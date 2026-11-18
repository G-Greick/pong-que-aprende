"""Testa o bot com um Telegram falso: nada sai para a internet."""

import urllib.error

import pytest

from pong import telegram_bot
from pong.chat import Assistente


class TelegramFalso:
    def __init__(self, atualizacoes):
        self.atualizacoes = list(atualizacoes)
        self.textos, self.fotos, self.offsets = [], [], []

    def chamar(self, metodo, params=None, espera=None):
        assert metodo == "getUpdates"
        self.offsets.append(params["offset"])
        if self.atualizacoes:
            item = self.atualizacoes.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        return []

    def enviar_texto(self, chat_id, texto):
        self.textos.append((chat_id, texto))

    def enviar_foto(self, chat_id, caminho, legenda=""):
        self.fotos.append((chat_id, caminho))


def msg(update_id, chat_id, texto):
    return {"update_id": update_id, "message": {"chat": {"id": chat_id}, "text": texto}}


def test_responde_as_mensagens_e_confirma_as_lidas(tmp_path):
    falso = TelegramFalso([[msg(10, 1, "oi"), msg(11, 1, "placar")]])
    telegram_bot.rodar(falso, Assistente(tmp_path), set(), mostrar=lambda _: None, ciclos=2)
    assert [t[0] for t in falso.textos] == [1, 1]
    assert falso.textos[0][1].startswith("Sou o assistente")
    assert "Nenhuma partida" in falso.textos[1][1]
    assert falso.offsets == [0, 12]  # na segunda chamada pede só o que vem depois da 11


def test_manda_o_grafico_como_foto(tmp_path):
    (tmp_path / "aprendizado.png").write_bytes(b"png")
    falso = TelegramFalso([[msg(1, 5, "/grafico")]])
    telegram_bot.rodar(falso, Assistente(tmp_path), set(), mostrar=lambda _: None, ciclos=1)
    assert falso.fotos == [(5, tmp_path / "aprendizado.png")]


def test_chat_fora_da_lista_nao_recebe_dados(tmp_path):
    falso = TelegramFalso([[msg(1, 999, "como foi o treino?")]])
    telegram_bot.rodar(falso, Assistente(tmp_path), {123}, mostrar=lambda _: None, ciclos=1)
    assert falso.textos == [(999, "Este bot é privado.")]


def test_ignora_mensagens_sem_texto(tmp_path):
    falso = TelegramFalso([[{"update_id": 1, "message": {"chat": {"id": 1}, "sticker": {}}}]])
    telegram_bot.rodar(falso, Assistente(tmp_path), set(), mostrar=lambda _: None, ciclos=1)
    assert falso.textos == []


def test_queda_de_conexao_nao_derruba_o_bot(tmp_path, monkeypatch):
    monkeypatch.setattr(telegram_bot.time, "sleep", lambda _: None)
    falso = TelegramFalso([urllib.error.URLError("sem rede"), [msg(1, 1, "oi")]])
    telegram_bot.rodar(falso, Assistente(tmp_path), set(), mostrar=lambda _: None, ciclos=2)
    assert len(falso.textos) == 1


def test_token_invalido_encerra_com_mensagem(tmp_path):
    erro = urllib.error.HTTPError("url", 401, "Unauthorized", {}, None)
    falso = TelegramFalso([erro])
    with pytest.raises(SystemExit, match="token"):
        telegram_bot.rodar(falso, Assistente(tmp_path), set(), mostrar=lambda _: None, ciclos=1)


def test_sem_token_explica_como_configurar(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(SystemExit, match="BotFather"):
        telegram_bot.main()

"""Controle pela mão sem webcam: um rastreador falso faz o papel da câmera."""

import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from pong import jogar, menu  # noqa: E402
from pong.jogo import DESCE, ESQ, PARADO, SOBE, Pong  # noqa: E402
from pong.mao import HumanoMao, altura_na_quadra, baixar_modelo  # noqa: E402
from pong.menu import Escolha, Menu  # noqa: E402
from pong.partidas import partida_atual  # noqa: E402


class RastreadorFalso:
    def __init__(self, y=None):
        self.y = y
        self.erro = None
        self.situacao = "mostre a mão para a câmera"
        self.parado = False

    def iniciar(self):
        return self

    def parar(self):
        self.parado = True

    def miniatura(self):
        return None


def test_faixa_util_da_imagem_cobre_a_quadra_toda():
    assert altura_na_quadra(0.2, 600) == 0
    assert altura_na_quadra(0.5, 600) == pytest.approx(300)
    assert altura_na_quadra(0.8, 600) == 600
    assert altura_na_quadra(0.05, 600) == 0  # fora da faixa: fica na borda
    assert altura_na_quadra(0.95, 600) == 600


def test_raquete_vai_atras_da_mao_com_as_tres_acoes():
    jogo = Pong(seed=0)  # raquete começa no meio (300)
    assert HumanoMao(RastreadorFalso(y=0.25)).agir(jogo, ESQ) == SOBE
    assert HumanoMao(RastreadorFalso(y=0.75)).agir(jogo, ESQ) == DESCE
    assert HumanoMao(RastreadorFalso(y=0.5)).agir(jogo, ESQ) == PARADO


def test_sem_mao_a_raquete_para():
    assert HumanoMao(RastreadorFalso(y=None)).agir(Pong(seed=0), ESQ) == PARADO


def test_suavizacao_amortece_um_salto_da_deteccao():
    rastreador = RastreadorFalso(y=0.5)
    jogador = HumanoMao(rastreador, suavizacao=0.5)
    jogo = Pong(seed=0)
    jogador.agir(jogo, ESQ)  # alvo 300
    rastreador.y = 0.8  # salto para 600
    jogador.agir(jogo, ESQ)
    assert jogador._alvo == pytest.approx(450)  # metade do caminho


def test_baixar_modelo_grava_o_arquivo(tmp_path):
    origem = tmp_path / "origem.task"
    origem.write_bytes(b"modelo")
    destino = tmp_path / "modelos" / "hand_landmarker.task"
    baixar_modelo(destino, url=origem.as_uri())
    assert destino.read_bytes() == b"modelo"


@pytest.fixture
def tela(monkeypatch, tmp_path):
    monkeypatch.setattr(jogar, "FPS", 0)
    monkeypatch.setattr(jogar, "PASTA_RESULTADOS", tmp_path)
    pygame.init()
    yield jogar.Tela(jogar.Config())
    pygame.quit()


def test_saque_espera_a_mao_aparecer_e_a_webcam_e_desligada(tela, monkeypatch):
    rastreador = RastreadorFalso(y=None)
    monkeypatch.setattr(jogar, "RastreadorMao", lambda: rastreador)
    escolha = Escolha(modo="jogar", oponente="segue", controle="mao")

    # sem mão, a bola não sai do centro: 200 quadros depois da espera, ninguém marcou
    jogar.jogar_partida(tela, escolha, com_menu=True, max_quadros=jogar.ESPERA_SAQUE + 200)
    assert rastreador.parado
    atual = partida_atual(jogar.PASTA_RESULTADOS)
    assert (atual["placar_esquerda"], atual["placar_direita"]) == (0, 0)


def test_menu_avisa_quando_falta_instalar(tela, tmp_path, monkeypatch):
    monkeypatch.setattr(menu, "falta_instalar", lambda: "instale antes: pip install -r requirements-mao.txt")
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    m = Menu(tela, Escolha(oponente="segue", controle="mao"), tmp_path, tmp_path)
    assert m.rodar(max_quadros=10) is None
    assert "requirements-mao.txt" in m.aviso

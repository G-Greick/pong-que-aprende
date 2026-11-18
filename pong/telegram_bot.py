"""Bot do Telegram: recebe as mensagens do produtor e responde com o Assistente.

    $env:TELEGRAM_BOT_TOKEN = "<token do @BotFather>"
    python -m pong.telegram_bot

O token é secreto: fica só na variável de ambiente, nunca no código nem no git.
Opcional: TELEGRAM_CHATS_PERMITIDOS="123,456" restringe quem pode conversar
(o bot mostra no terminal o id de cada chat que manda mensagem).

Usa a API HTTP do Telegram direto (getUpdates com long polling), sem biblioteca
extra: o bot pergunta "tem mensagem nova?" e o Telegram segura a resposta até
chegar alguma ou passar 30 s.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from pong.chat import Assistente

ESPERA_POLLING = 30  # segundos que o Telegram segura o getUpdates


class Telegram:
    def __init__(self, token: str):
        self._base = f"https://api.telegram.org/bot{token}/"

    def chamar(self, metodo: str, params: dict | None = None, espera: float = ESPERA_POLLING + 10):
        dados = urllib.parse.urlencode(params or {}).encode()
        return self._enviar(urllib.request.Request(self._base + metodo, data=dados), espera)

    def enviar_texto(self, chat_id: int, texto: str) -> None:
        self.chamar("sendMessage", {"chat_id": chat_id, "text": texto})

    def enviar_foto(self, chat_id: int, caminho: Path, legenda: str = "") -> None:
        # upload de arquivo exige multipart/form-data, montado à mão
        limite = uuid.uuid4().hex
        partes = [
            f'--{limite}\r\nContent-Disposition: form-data; name="{nome}"\r\n\r\n{valor}\r\n'.encode()
            for nome, valor in (("chat_id", chat_id), ("caption", legenda))
        ]
        partes.append(
            f'--{limite}\r\nContent-Disposition: form-data; name="photo"; filename="{caminho.name}"\r\n'
            "Content-Type: image/png\r\n\r\n".encode() + caminho.read_bytes() + b"\r\n"
        )
        partes.append(f"--{limite}--\r\n".encode())
        pedido = urllib.request.Request(
            self._base + "sendPhoto",
            data=b"".join(partes),
            headers={"Content-Type": f"multipart/form-data; boundary={limite}"},
        )
        self._enviar(pedido, 60)

    @staticmethod
    def _enviar(pedido: urllib.request.Request, espera: float):
        with urllib.request.urlopen(pedido, timeout=espera) as r:
            resposta = json.load(r)
        if not resposta.get("ok"):
            raise RuntimeError(resposta.get("description", "erro desconhecido do Telegram"))
        return resposta["result"]


def atender(telegram, assistente: Assistente, mensagem: dict, permitidos: set[int], mostrar=print) -> None:
    chat_id = mensagem["chat"]["id"]
    texto = mensagem.get("text", "")
    mostrar(f"[chat {chat_id}] {texto}")
    if permitidos and chat_id not in permitidos:
        telegram.enviar_texto(chat_id, "Este bot é privado.")
        return
    resposta = assistente.responder(texto)
    telegram.enviar_texto(chat_id, resposta.texto)
    if resposta.imagem:
        telegram.enviar_foto(chat_id, resposta.imagem)


def rodar(telegram, assistente: Assistente, permitidos: set[int], mostrar=print, ciclos: int | None = None) -> None:
    proximo = 0  # id da próxima atualização: confirma ao Telegram as que já foram lidas
    while ciclos is None or ciclos > 0:
        if ciclos is not None:
            ciclos -= 1
        try:
            atualizacoes = telegram.chamar("getUpdates", {"offset": proximo, "timeout": ESPERA_POLLING})
        except urllib.error.HTTPError as erro:
            if erro.code == 401:
                raise SystemExit("O Telegram recusou o token (401). Confira TELEGRAM_BOT_TOKEN.") from None
            if erro.code == 409:
                raise SystemExit("Já existe outra cópia deste bot rodando; feche-a primeiro.") from None
            mostrar(f"Telegram respondeu erro {erro.code}; tentando de novo em 5 s")
            time.sleep(5)
            continue
        except (urllib.error.URLError, TimeoutError, ConnectionError) as erro:
            mostrar(f"Sem conexão com o Telegram ({erro.__class__.__name__}); tentando de novo em 5 s")
            time.sleep(5)
            continue

        for atualizacao in atualizacoes:
            proximo = atualizacao["update_id"] + 1
            mensagem = atualizacao.get("message")
            if not mensagem or "text" not in mensagem:
                continue
            try:
                atender(telegram, assistente, mensagem, permitidos, mostrar)
            except Exception as erro:  # uma mensagem com problema não derruba o bot
                mostrar(f"Erro ao responder: {erro}")


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "Defina o token do bot (criado no @BotFather) numa variável de ambiente:\n"
            '  PowerShell:  $env:TELEGRAM_BOT_TOKEN = "123456:ABC..."\n'
            "Sem Telegram, dá para conversar pelo terminal: python -m pong.chat"
        )
    permitidos = {int(c) for c in os.environ.get("TELEGRAM_CHATS_PERMITIDOS", "").split(",") if c.strip()}

    telegram = Telegram(token)
    try:
        bot = telegram.chamar("getMe", espera=15)
    except urllib.error.HTTPError as erro:
        raise SystemExit(f"O Telegram recusou o token ({erro.code}). Confira TELEGRAM_BOT_TOKEN.") from None
    except urllib.error.URLError:
        raise SystemExit("Sem conexão com o Telegram. Sem internet, use: python -m pong.chat") from None

    print(f"Bot @{bot['username']} no ar. Mande uma mensagem para ele no Telegram. Ctrl+C encerra.")
    if permitidos:
        print(f"Respondendo só aos chats: {', '.join(map(str, sorted(permitidos)))}")
    try:
        rodar(telegram, Assistente(), permitidos, mostrar=lambda m: print(m, flush=True))
    except KeyboardInterrupt:
        print("\nBot encerrado.")


if __name__ == "__main__":
    sys.exit(main())

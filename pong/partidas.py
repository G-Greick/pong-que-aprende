"""Placar das partidas do modo visual, gravado para o chat consultar.

  resultados/partida.json   a partida atual (ou a última), atualizada a cada ponto
  resultados/partidas.csv   uma linha por partida terminada
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from pong.arquivos import escrever_json, ler_csv, ler_json
from pong.jogo import DIR, ESQ, Pong

PASTA = Path("resultados")
ATUAL = "partida.json"
HISTORICO = "partidas.csv"
COLUNAS = ["fim", "esquerda", "direita", "placar_esquerda", "placar_direita", "vencedor"]


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


class RegistroPartida:
    def __init__(self, nomes: dict[str, str], pasta: Path = PASTA):
        self.nomes = nomes
        self.pasta = pasta

    def inicio(self, jogo: Pong) -> None:
        self._gravar(jogo, "em andamento")

    def ponto(self, jogo: Pong) -> None:
        if not jogo.terminou:
            self._gravar(jogo, "em andamento")
            return
        self._gravar(jogo, "terminada")
        caminho = self.pasta / HISTORICO
        novo = not caminho.exists()
        with open(caminho, "a", newline="", encoding="utf-8") as f:
            escritor = csv.DictWriter(f, fieldnames=COLUNAS)
            if novo:
                escritor.writeheader()
            escritor.writerow({
                "fim": _agora(),
                "esquerda": self.nomes[ESQ],
                "direita": self.nomes[DIR],
                "placar_esquerda": jogo.placar[ESQ],
                "placar_direita": jogo.placar[DIR],
                "vencedor": self.nomes[jogo.vencedor],
            })

    def interrompida(self, jogo: Pong) -> None:
        if not jogo.terminou:
            self._gravar(jogo, "interrompida")

    def _gravar(self, jogo: Pong, situacao: str) -> None:
        escrever_json(self.pasta / ATUAL, {
            "situacao": situacao,
            "esquerda": self.nomes[ESQ],
            "direita": self.nomes[DIR],
            "placar_esquerda": jogo.placar[ESQ],
            "placar_direita": jogo.placar[DIR],
            "pontos_para_vencer": jogo.cfg.pontos_para_vencer,
            "vencedor": self.nomes[jogo.vencedor] if jogo.vencedor else None,
            "atualizado": _agora(),
        })


def partida_atual(pasta: Path = PASTA) -> dict | None:
    return ler_json(pasta / ATUAL)


def historico(pasta: Path = PASTA) -> list[dict]:
    return ler_csv(pasta / HISTORICO)

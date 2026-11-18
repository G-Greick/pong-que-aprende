"""Arquivos que um processo grava e outro lê ao mesmo tempo (o treino e o
jogo gravam, o chat lê)."""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path


def escrever_json(caminho: Path, dados: dict) -> None:
    """Grava num arquivo temporário e troca, para quem lê nunca pegar um JSON
    pela metade. No Windows a troca falha se o leitor estiver com o arquivo
    aberto naquele instante, então tenta de novo algumas vezes."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    for tentativa in range(10):
        try:
            tmp.replace(caminho)
            return
        except PermissionError:
            if tentativa == 9:
                raise
            time.sleep(0.02)


def ler_json(caminho: Path) -> dict | None:
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def ler_csv(caminho: Path) -> list[dict]:
    try:
        with open(caminho, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        return []

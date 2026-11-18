import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # roda sem abrir janela
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pong import jogar  # noqa: E402


def test_modo_visual_roda_sem_erros(monkeypatch):
    # bot contra bot por 10 segundos de jogo (600 quadros)
    args = jogar.argparse.Namespace(
        nivel="dificil", oponente="preditor", controle="teclado", assistir=True, pontos=11
    )
    monkeypatch.setattr(jogar, "FPS", 0)  # sem esperar o relógio
    jogar.rodar(args, max_quadros=600)


def test_nivel_sem_modelo_treinado_avisa(tmp_path, monkeypatch):
    monkeypatch.setattr(jogar, "PASTA_MODELOS", tmp_path)
    with pytest.raises(SystemExit, match="treine antes"):
        jogar.criar_oponente("dificil")

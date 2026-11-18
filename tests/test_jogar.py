import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # roda sem abrir janela
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pong import jogar  # noqa: E402
from pong.partidas import historico, partida_atual  # noqa: E402


def test_modo_visual_roda_e_grava_o_placar(monkeypatch, tmp_path):
    # bot contra bot (o preditor sempre vence o segue), partida até 1 ponto
    args = jogar.argparse.Namespace(
        nivel="dificil", oponente="preditor", controle="teclado", assistir=True, pontos=1
    )
    monkeypatch.setattr(jogar, "FPS", 0)  # sem esperar o relógio
    monkeypatch.setattr(jogar, "PASTA_RESULTADOS", tmp_path)
    jogar.rodar(args, max_quadros=3000)

    atual = partida_atual(tmp_path)
    assert atual["situacao"] == "terminada"
    assert atual["vencedor"] == "bot preditor"
    assert [p["vencedor"] for p in historico(tmp_path)] == ["bot preditor"]


def test_nivel_sem_modelo_treinado_avisa(tmp_path, monkeypatch):
    monkeypatch.setattr(jogar, "PASTA_MODELOS", tmp_path)
    with pytest.raises(SystemExit, match="treine antes"):
        jogar.criar_oponente("dificil")

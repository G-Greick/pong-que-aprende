import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # roda sem abrir janela
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from pong import jogar  # noqa: E402
from pong.menu import Escolha, Menu, descrever, linhas_do_menu  # noqa: E402
from pong.partidas import historico, partida_atual  # noqa: E402


@pytest.fixture
def tela(monkeypatch, tmp_path):
    monkeypatch.setattr(jogar, "FPS", 0)  # sem esperar o relógio
    monkeypatch.setattr(jogar, "PASTA_RESULTADOS", tmp_path)
    pygame.init()
    yield jogar.Tela(jogar.Config())
    pygame.quit()


def teclas(*nomes):
    for nome in nomes:
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=nome))


# --- partida -------------------------------------------------------------------


def test_partida_roda_e_grava_o_placar(tela, tmp_path):
    # bot contra bot (o preditor sempre vence o segue), partida até 1 ponto
    escolha = Escolha(modo="assistir", oponente="preditor", pontos=1)
    assert jogar.jogar_partida(tela, escolha, com_menu=False, max_quadros=3000) == "sair"

    atual = partida_atual(tmp_path)
    assert atual["situacao"] == "terminada"
    assert atual["vencedor"] == "bot preditor"
    assert [p["vencedor"] for p in historico(tmp_path)] == ["bot preditor"]


def test_esc_na_partida_volta_ao_menu(tela, tmp_path):
    teclas(pygame.K_ESCAPE)
    escolha = Escolha(modo="jogar", oponente="segue")
    assert jogar.jogar_partida(tela, escolha, com_menu=True, max_quadros=100) == "menu"
    assert partida_atual(tmp_path)["situacao"] == "interrompida"


def test_nivel_sem_modelo_treinado_avisa(tmp_path, monkeypatch):
    monkeypatch.setattr(jogar, "PASTA_MODELOS", tmp_path)
    with pytest.raises(SystemExit, match="treine antes"):
        jogar.criar_oponente("dificil")


# --- menu ------------------------------------------------------------------------


def test_menu_enter_joga_com_a_escolha_padrao(tela, tmp_path):
    teclas(pygame.K_RETURN)
    escolha = Menu(tela, Escolha(), jogar.PASTA_MODELOS, tmp_path).rodar(max_quadros=10)
    assert escolha == Escolha()


def test_menu_muda_modo_adversario_e_pontos_pelo_teclado(tela, tmp_path):
    # começa no JOGAR; desce até "Modo", troca para assistir; desce para
    # "Adversário" e volta um (difícil -> médio); desce até "Pontos" e avança (11 -> 21)
    teclas(
        pygame.K_DOWN, pygame.K_RIGHT,
        pygame.K_DOWN, pygame.K_LEFT,
        pygame.K_DOWN, pygame.K_RIGHT,
        pygame.K_RETURN,
    )
    escolha = Menu(tela, Escolha(), jogar.PASTA_MODELOS, tmp_path).rodar(max_quadros=20)
    assert escolha == Escolha(modo="assistir", oponente="medio", controle="teclado", pontos=21)


def test_menu_esc_fecha(tela, tmp_path):
    teclas(pygame.K_ESCAPE)
    assert Menu(tela, Escolha(), jogar.PASTA_MODELOS, tmp_path).rodar(max_quadros=10) is None


def test_menu_nao_deixa_jogar_nivel_sem_modelo(tela, tmp_path):
    teclas(pygame.K_RETURN)
    menu = Menu(tela, Escolha(oponente="facil"), tmp_path, tmp_path)  # pasta de modelos vazia
    assert menu.rodar(max_quadros=10) is None
    assert menu.aviso == "esse nível ainda não foi treinado"


def test_controle_so_aparece_quando_humano_joga():
    assert "controle" in [l.chave for l in linhas_do_menu(Escolha(modo="jogar"))]
    assert "controle" not in [l.chave for l in linhas_do_menu(Escolha(modo="assistir"))]


def test_descricao_do_nivel_usa_a_avaliacao(tmp_path):
    (tmp_path / "ia_2000.npz").write_bytes(b"")
    aval = {"facil": {"pct_pontos": "13.0"}}
    texto = descrever(Escolha(oponente="facil"), "oponente", aval, tmp_path)
    assert texto == "IA com 2.000 pontos de treino · ganha 13% dos pontos contra o bot segue"

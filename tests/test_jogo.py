import math
import random

import pytest

from pong.jogo import ACOES, DESCE, DIR, ESQ, PARADO, SOBE, Config, Pong

INFINITO = 10**9  # pontos_para_vencer quando o teste não quer que a partida acabe


def posicionar_bola(jogo, x, y, vx, vy):
    jogo.bola_x, jogo.bola_y, jogo.bola_vx, jogo.bola_vy = x, y, vx, vy


def rodar_ate_ponto(jogo, limite=50):
    for _ in range(limite):
        evento = jogo.step(PARADO, PARADO)
        if evento.ponto:
            return evento
    pytest.fail("nenhum ponto aconteceu")


# --- bola e paredes ---------------------------------------------------------


def test_bola_quica_no_teto():
    jogo = Pong(seed=0)
    posicionar_bola(jogo, 400, 8, 3, -6)
    jogo.step(PARADO, PARADO)
    assert jogo.bola_vy > 0
    assert jogo.bola_y - jogo.cfg.bola_tam / 2 >= 0


def test_bola_quica_no_chao():
    jogo = Pong(seed=0)
    posicionar_bola(jogo, 400, 592, 3, 6)
    jogo.step(PARADO, PARADO)
    assert jogo.bola_vy < 0
    assert jogo.bola_y + jogo.cfg.bola_tam / 2 <= jogo.cfg.altura


# --- pontos e placar --------------------------------------------------------


def test_bola_passa_pela_esquerda_ponto_da_direita():
    jogo = Pong(seed=0)
    posicionar_bola(jogo, 100, 50, -6, 0)  # raquete esquerda está no meio, longe
    evento = rodar_ate_ponto(jogo)
    assert evento.ponto == DIR
    assert jogo.placar == {ESQ: 0, DIR: 1}


def test_bola_passa_pela_direita_ponto_da_esquerda():
    jogo = Pong(seed=0)
    posicionar_bola(jogo, 700, 50, 6, 0)
    evento = rodar_ate_ponto(jogo)
    assert evento.ponto == ESQ
    assert jogo.placar == {ESQ: 1, DIR: 0}


def test_depois_do_ponto_bola_volta_ao_centro_indo_para_quem_sofreu():
    jogo = Pong(seed=0)
    posicionar_bola(jogo, 100, 50, -6, 0)
    rodar_ate_ponto(jogo)
    assert (jogo.bola_x, jogo.bola_y) == (400, 300)
    assert jogo.bola_vx < 0  # quem sofreu foi a esquerda


def test_partida_termina_com_o_vencedor_certo():
    jogo = Pong(Config(pontos_para_vencer=3), seed=0)
    jogo.placar = {ESQ: 2, DIR: 1}
    posicionar_bola(jogo, 700, 50, 6, 0)
    evento = rodar_ate_ponto(jogo)
    assert evento.fim
    assert jogo.vencedor == ESQ
    assert jogo.placar == {ESQ: 3, DIR: 1}
    with pytest.raises(RuntimeError):
        jogo.step(PARADO, PARADO)


def test_placar_bate_com_os_pontos_de_uma_partida_inteira():
    jogo = Pong(seed=1)
    acoes = random.Random(1)
    contagem = {ESQ: 0, DIR: 0}
    while not jogo.terminou:
        evento = jogo.step(acoes.choice(ACOES), acoes.choice(ACOES))
        if evento.ponto:
            contagem[evento.ponto] += 1
    assert contagem == jogo.placar
    assert jogo.placar[jogo.vencedor] == jogo.cfg.pontos_para_vencer


def test_reiniciar_zera_a_partida():
    jogo = Pong(Config(pontos_para_vencer=1), seed=0)
    posicionar_bola(jogo, 700, 50, 6, 0)
    rodar_ate_ponto(jogo)
    jogo.reiniciar()
    assert jogo.placar == {ESQ: 0, DIR: 0}
    assert not jogo.terminou


# --- raquetes ---------------------------------------------------------------


def test_acoes_movem_a_raquete():
    jogo = Pong(seed=0)
    meio, vel = jogo.cfg.altura / 2, jogo.cfg.raquete_vel
    jogo.step(SOBE, DESCE)
    assert jogo.raquete == {ESQ: meio - vel, DIR: meio + vel}
    jogo.step(PARADO, PARADO)
    assert jogo.raquete == {ESQ: meio - vel, DIR: meio + vel}


def test_acao_invalida_e_recusada():
    jogo = Pong(seed=0)
    with pytest.raises(ValueError):
        jogo.step(7, PARADO)


def test_raquete_nao_sai_da_quadra():
    jogo = Pong(Config(pontos_para_vencer=INFINITO), seed=0)
    meia = jogo.cfg.raquete_altura / 2
    for _ in range(200):
        jogo.step(SOBE, DESCE)
    assert jogo.raquete == {ESQ: meia, DIR: jogo.cfg.altura - meia}


# --- rebatidas --------------------------------------------------------------


def test_raquete_rebate_a_bola():
    jogo = Pong(seed=0)
    posicionar_bola(jogo, 40, 300, -6, 0)
    evento = jogo.step(PARADO, PARADO)
    assert evento.rebateu == ESQ
    assert evento.ponto is None
    assert jogo.bola_vx > 0


def test_raquete_direita_rebate_a_bola():
    jogo = Pong(seed=0)
    posicionar_bola(jogo, 760, 300, 6, 0)
    evento = jogo.step(PARADO, PARADO)
    assert evento.rebateu == DIR
    assert jogo.bola_vx < 0


def test_rebatida_no_centro_volta_reta_e_mais_rapida():
    jogo = Pong(seed=0)
    posicionar_bola(jogo, 40, 300, -6, 0)
    jogo.step(PARADO, PARADO)
    assert jogo.bola_vy == pytest.approx(0)
    assert jogo.bola_vx == pytest.approx(6 * jogo.cfg.aceleracao)


@pytest.mark.parametrize("y_bola, sobe", [(335, False), (265, True)])
def test_rebatida_na_ponta_sai_inclinada(y_bola, sobe):
    jogo = Pong(seed=0)
    posicionar_bola(jogo, 40, y_bola, -6, 0)
    jogo.step(PARADO, PARADO)
    angulo = math.degrees(math.atan2(abs(jogo.bola_vy), jogo.bola_vx))
    assert angulo > 30
    assert (jogo.bola_vy < 0) == sobe


def test_bola_rapida_nao_atravessa_a_raquete():
    # raquete fina e bola muito rápida: sem a checagem pela trajetória, a bola
    # sairia do outro lado da raquete em um único passo
    jogo = Pong(Config(raquete_largura=2, bola_vel_max=40), seed=0)
    posicionar_bola(jogo, 30, 300, -30, 0)
    evento = jogo.step(PARADO, PARADO)
    assert evento.rebateu == ESQ


def test_velocidade_nunca_passa_do_maximo():
    jogo = Pong(seed=0)
    posicionar_bola(jogo, 40, 300, -jogo.cfg.bola_vel_max, 0)
    jogo.step(PARADO, PARADO)
    vel = math.hypot(jogo.bola_vx, jogo.bola_vy)
    assert vel == pytest.approx(jogo.cfg.bola_vel_max)


def test_bola_que_passa_da_raquete_nao_e_rebatida_por_tras():
    jogo = Pong(seed=0)
    posicionar_bola(jogo, 26, 300, -6, 0)  # já passou da face (x=30)
    evento = jogo.step(PARADO, PARADO)
    assert evento.rebateu is None


# --- reprodutibilidade ------------------------------------------------------


def test_mesma_semente_mesma_partida():
    def jogar(seed):
        jogo = Pong(Config(pontos_para_vencer=INFINITO), seed=seed)
        acoes = random.Random(42)
        for _ in range(5000):
            jogo.step(acoes.choice(ACOES), acoes.choice(ACOES))
        return jogo.placar, jogo.bola_x, jogo.bola_y, jogo.raquete

    assert jogar(7) == jogar(7)

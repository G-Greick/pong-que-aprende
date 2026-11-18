import random

import pytest

from pong import agente as modulo_agente
from pong.agente import AgenteQ, Discretizador, recompensa
from pong.jogo import ACOES, DESCE, DIR, ESQ, PARADO, SOBE, Evento, Pong


def test_estado_sempre_cabe_na_tabela():
    jogo, disc, rng = Pong(seed=0), Discretizador(), random.Random(0)
    for _ in range(2000):
        jogo.bola_x, jogo.bola_y = rng.uniform(0, 800), rng.uniform(0, 600)
        jogo.bola_vx, jogo.bola_vy = rng.uniform(-14, 14) or 1, rng.uniform(-14, 14)
        jogo.raquete[DIR] = rng.uniform(40, 560)
        assert 0 <= disc(jogo, DIR) < disc.n_estados


def test_mesma_situacao_espelhada_da_o_mesmo_estado():
    # a IA enxerga o jogo a partir da própria raquete, então ela joga dos dois lados
    disc = Discretizador()
    jogo = Pong(seed=0)
    jogo.bola_x, jogo.bola_y, jogo.bola_vx, jogo.bola_vy = 600, 250, 6, 3
    jogo.raquete[DIR] = 320
    estado_dir = disc(jogo, DIR)

    jogo.bola_x, jogo.bola_vx = 800 - 600, -6
    jogo.raquete[ESQ] = 320
    assert disc(jogo, ESQ) == estado_dir


def test_recompensas():
    assert recompensa(Evento(rebateu=DIR), DIR) == 1
    assert recompensa(Evento(rebateu=ESQ), DIR) == 0
    assert recompensa(Evento(ponto=ESQ), DIR) == -1
    assert recompensa(Evento(ponto=DIR), DIR) == modulo_agente.RECOMPENSA_MARCAR


def test_aprender_em_estado_final_nao_olha_o_futuro():
    agente = AgenteQ(alpha=0.1)
    agente.q[7] = [0, 5, 0]
    agente.aprender(3, SOBE, r=1.0, proximo=7, terminal=True)
    assert agente.q[3, SOBE] == pytest.approx(0.1)


def test_aprender_soma_o_valor_do_proximo_estado():
    agente = AgenteQ(alpha=0.1, gamma=0.99)
    agente.q[7] = [0, 2, 0]
    agente.aprender(3, DESCE, r=0.0, proximo=7, terminal=False)
    assert agente.q[3, DESCE] == pytest.approx(0.1 * 0.99 * 2)


def test_escolhe_a_acao_de_maior_valor():
    agente = AgenteQ(seed=0)
    agente.q[5] = [0.1, -0.3, 0.8]
    assert all(agente.escolher(5) == DESCE for _ in range(50))


def test_ia_sem_treino_joga_ao_acaso():
    agente = AgenteQ(seed=0)
    assert {agente.escolher(5) for _ in range(300)} == set(ACOES)


def test_repete_a_acao_entre_decisoes():
    agente = AgenteQ(repetir=4, seed=0)
    agente.q[:] = [0, 1, 0]  # sempre SOBE
    jogo = Pong(seed=0)
    assert [agente.agir(jogo, DIR) for _ in range(4)] == [SOBE] * 4
    agente.q[:] = [1, 0, 0]  # agora sempre PARADO, mas só vale na próxima decisão
    assert agente.agir(jogo, DIR) == PARADO


def test_salvar_e_carregar(tmp_path):
    agente = AgenteQ(alpha=0.2, repetir=3, seed=0)
    agente.q[10] = [1, 2, 3]
    agente.meta = {"pontos_treinados": 123}
    agente.salvar(tmp_path / "ia.npz")

    copia = AgenteQ.carregar(tmp_path / "ia.npz")
    assert (copia.q == agente.q).all()
    assert (copia.alpha, copia.repetir) == (0.2, 3)
    assert copia.meta == {"pontos_treinados": 123}


def test_tamanho_do_cerebro():
    agente = AgenteQ()
    assert agente.tamanho_bytes == agente.disc.n_estados * 3 * 4  # float32

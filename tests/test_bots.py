import pytest

from pong.avaliacao import avaliar
from pong.bots import BotAleatorio, BotPreditor, BotSegue, criar_bot, prever_y
from pong.jogo import DESCE, DIR, ESQ, PARADO, SOBE, Pong


def test_segue_vai_atras_da_bola_que_vem():
    jogo = Pong(seed=0)
    jogo.bola_x, jogo.bola_y, jogo.bola_vx, jogo.bola_vy = 400, 100, 6, 0
    assert BotSegue().agir(jogo, DIR) == SOBE
    jogo.bola_y = 500
    assert BotSegue().agir(jogo, DIR) == DESCE


def test_segue_volta_para_o_meio_quando_a_bola_vai_embora():
    jogo = Pong(seed=0)
    jogo.bola_x, jogo.bola_y, jogo.bola_vx, jogo.bola_vy = 400, 100, -6, 0
    jogo.raquete[DIR] = 100
    assert BotSegue().agir(jogo, DIR) == DESCE
    jogo.raquete[DIR] = 300
    assert BotSegue().agir(jogo, DIR) == PARADO


def test_previsao_conta_o_quique_na_parede():
    jogo = Pong(seed=0)
    # sobe 95 px até encostar no teto (y=5) e desce os 270 px que faltam
    jogo.bola_x, jogo.bola_y, jogo.bola_vx, jogo.bola_vy = 400, 100, 10, -10
    assert prever_y(jogo, DIR) == pytest.approx(275)


def test_previsao_bate_com_a_simulacao():
    jogo = Pong(seed=3)
    for _ in range(50):
        jogo.sacar(DIR)
        jogo.bola_vy *= 1.8  # saque bem inclinado, para quicar
        previsto = prever_y(jogo, DIR)
        jogo.raquete[DIR] = 40 if previsto > 300 else 560  # sai da frente
        while jogo.bola_x + 5 < jogo.x_face(DIR):
            y_antes = jogo.bola_y
            jogo.step(PARADO, PARADO)
        assert abs(previsto - y_antes) < abs(jogo.bola_vy) + 1


def test_criar_bot_desconhecido():
    with pytest.raises(ValueError):
        criar_bot("imbativel")


# a escada de dificuldade dos bots, medida em 200 pontos com sementes fixas


def test_segue_vence_aleatorio():
    assert avaliar(BotSegue(), BotAleatorio(seed=2), pontos=200)["pct_pontos"] == 100


def test_preditor_vence_segue():
    assert avaliar(BotPreditor(seed=1), BotSegue(), pontos=200)["pct_pontos"] == 100


def test_avaliacao_conta_pontos_travados():
    r = avaliar(BotSegue(), BotSegue(), pontos=20, limite_passos=200, lado=ESQ)
    assert r["travados"] > 0
    assert r["pontos"] + r["travados"] == 20

from pong.jogo import DIR, ESQ, Config, Pong
from pong.partidas import RegistroPartida, historico, partida_atual

NOMES = {ESQ: "você", DIR: "IA · fácil"}


def test_placar_acompanha_a_partida(tmp_path):
    jogo = Pong(Config(pontos_para_vencer=3), seed=0)
    registro = RegistroPartida(NOMES, tmp_path)
    registro.inicio(jogo)
    assert partida_atual(tmp_path)["situacao"] == "em andamento"

    jogo.placar = {ESQ: 2, DIR: 1}
    registro.ponto(jogo)
    atual = partida_atual(tmp_path)
    assert (atual["placar_esquerda"], atual["placar_direita"]) == (2, 1)
    assert historico(tmp_path) == []  # ainda não terminou


def test_partida_terminada_entra_no_historico_uma_vez(tmp_path):
    jogo = Pong(Config(pontos_para_vencer=3), seed=0)
    registro = RegistroPartida(NOMES, tmp_path)
    jogo.placar, jogo.vencedor = {ESQ: 3, DIR: 1}, ESQ
    registro.ponto(jogo)
    registro.interrompida(jogo)  # sair depois do fim não muda nada

    assert partida_atual(tmp_path)["situacao"] == "terminada"
    partidas = historico(tmp_path)
    assert len(partidas) == 1
    assert partidas[0]["vencedor"] == "você"
    assert (partidas[0]["placar_esquerda"], partidas[0]["placar_direita"]) == ("3", "1")


def test_sair_no_meio_marca_como_interrompida(tmp_path):
    jogo = Pong(seed=0)
    registro = RegistroPartida(NOMES, tmp_path)
    registro.inicio(jogo)
    registro.interrompida(jogo)
    assert partida_atual(tmp_path)["situacao"] == "interrompida"
    assert historico(tmp_path) == []

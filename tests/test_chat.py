import csv
import json

import pytest

from pong.chat import Assistente, entender
from pong.jogo import DIR, ESQ, Config, Pong
from pong.partidas import RegistroPartida


def escrever_csv(caminho, linhas):
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(linhas[0]))
        escritor.writeheader()
        escritor.writerows(linhas)


@pytest.fixture
def resultados(tmp_path):
    """Uma pasta resultados/ com um treino terminado e a avaliação final."""
    (tmp_path / "status.json").write_text(json.dumps({
        "situacao": "concluido", "pontos_total": 30000, "pontos_treinados": 30000,
        "adversario": "segue", "segundos": 324.0,
    }), encoding="utf-8")
    escrever_csv(tmp_path / "treino.csv", [
        {"pontos_treinados": 0, "pct_pontos_avaliacao": 0.0, "rebatidas_avaliacao": 0.17},
        {"pontos_treinados": 29000, "pct_pontos_avaliacao": 52.1, "rebatidas_avaliacao": 29.65},
        {"pontos_treinados": 30000, "pct_pontos_avaliacao": 50.4, "rebatidas_avaliacao": 24.83},
    ])
    linhas = []
    for nivel, pct_segue, reb in (("sem-treino", 0.0, 0.17), ("dificil", 50.9, 23.9)):
        for bot, pct in (("aleatorio", 48.8 if nivel == "sem-treino" else 100.0), ("segue", pct_segue),
                         ("preditor", 0.1)):
            linhas.append({"nivel": nivel, "bot": bot, "pct_pontos": pct, "rebatidas_por_ponto": reb})
    escrever_csv(tmp_path / "avaliacao.csv", linhas)
    return tmp_path


@pytest.mark.parametrize("pergunta, intencao", [
    ("Como foi o treino?", "treino"),
    ("/treino", "treino"),
    ("o treinamento terminou?", "treino"),
    ("A IA aprendeu mesmo?", "aprendeu"),
    ("qual o placar?", "placar"),
    ("quem tá ganhando?", "placar"),
    ("Quanto CÉREBRO ela tem?", "cerebro"),
    ("quais os níveis de dificuldade", "niveis"),
    ("joga bem contra outro adversário?", "adversario"),
    ("manda o gráfico do treino", "grafico"),
    ("/start", "ajuda"),
    ("oi", "ajuda"),
    ("qual a capital da França", None),
])
def test_entende_a_pergunta(pergunta, intencao):
    assert entender(pergunta) == intencao


def test_como_foi_o_treino(resultados):
    texto = Assistente(resultados).responder("como foi o treino?").texto
    assert "terminou: 30.000 pontos contra o bot segue, em 5,4 minutos" in texto
    assert "ganhava 0,0% dos pontos" in texto
    assert "No fim, 50,4%" in texto
    assert "Melhor medição: 52,1% com 29.000" in texto


def test_treino_em_andamento(tmp_path):
    (tmp_path / "status.json").write_text(json.dumps({
        "situacao": "treinando", "pontos_total": 30000, "pontos_treinados": 12000, "adversario": "segue",
        "segundos": 52.0, "pct_pontos_avaliacao": 34.6, "rebatidas_avaliacao": 14.01, "epsilon": 0.2,
    }), encoding="utf-8")
    texto = Assistente(tmp_path).responder("e o treino?").texto
    assert "rodando: 12.000 de 30.000 pontos (40%)" in texto
    assert "34,6%" in texto


def test_aprendeu_compara_os_niveis(resultados):
    texto = Assistente(resultados).responder("a IA aprendeu?").texto
    assert "sem treino: 0,0% dos pontos, 0,2 rebatidas" in texto
    assert "difícil: 50,9% dos pontos, 23,9 rebatidas" in texto
    assert "foi de 48,8% para 100,0%" in texto


def test_tamanho_do_cerebro(resultados):
    texto = Assistente(resultados).responder("quanto cérebro?").texto
    assert "440 situações × 3 ações" in texto
    assert "1.320 números" in texto and "5.280 bytes" in texto


def test_adversario_diferente_responde_com_honestidade(resultados):
    texto = Assistente(resultados).responder("e contra outro adversário?").texto
    assert "0,1%" in texto and "23,9 rebatidas" in texto
    assert "não a vencer" in texto


def test_grafico_manda_imagem(resultados):
    (resultados / "aprendizado.png").write_bytes(b"png")
    resposta = Assistente(resultados).responder("/grafico")
    assert resposta.imagem == resultados / "aprendizado.png"


def test_placar_da_partida_e_historico(tmp_path):
    nomes = {ESQ: "você", DIR: "IA · difícil"}
    jogo = Pong(Config(pontos_para_vencer=2), seed=0)
    registro = RegistroPartida(nomes, tmp_path)
    registro.inicio(jogo)
    jogo.placar = {ESQ: 1, DIR: 0}
    registro.ponto(jogo)
    assistente = Assistente(tmp_path)
    assert "em andamento: você 1 x 0 IA · difícil" in assistente.responder("placar").texto

    jogo.placar, jogo.vencedor = {ESQ: 1, DIR: 2}, DIR
    registro.ponto(jogo)
    texto = assistente.responder("qual o placar?").texto
    assert "IA · difícil venceu, você 1 x 2 IA · difícil" in texto
    assert "1 partida terminada, humanos 0 x 1 IA" in texto


def test_sem_dados_ainda_explica_o_que_fazer(tmp_path):
    assistente = Assistente(tmp_path)
    assert "python -m pong.treino" in assistente.responder("como foi o treino").texto
    assert "python -m pong.jogar" in assistente.responder("placar").texto
    assert "python -m pong.relatorio" in assistente.responder("gráfico").texto


def test_pergunta_desconhecida_mostra_a_ajuda(resultados):
    texto = Assistente(resultados).responder("qual a capital da França?").texto
    assert texto.startswith("Não entendi") and "/treino" in texto

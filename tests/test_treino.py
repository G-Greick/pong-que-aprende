import csv
import json

from pong.agente import AgenteQ
from pong.avaliacao import avaliar
from pong.bots import BotSegue
from pong.treino import epsilon_no, treinar


def test_exploracao_cai_e_depois_fica_no_minimo():
    assert epsilon_no(0, 1000) == 1.0
    assert epsilon_no(250, 1000) == 0.5
    assert epsilon_no(500, 1000) == 0.05
    assert epsilon_no(900, 1000) == 0.05


def test_treino_gera_modelos_grafico_e_status(tmp_path):
    treinar(
        pontos=300, bloco=100, checkpoints=(0,), pontos_avaliacao=20,
        pasta_modelos=tmp_path / "modelos", pasta_resultados=tmp_path / "resultados",
        mostrar=lambda _: None,
    )
    assert (tmp_path / "modelos" / "ia_0.npz").exists()
    assert AgenteQ.carregar(tmp_path / "modelos" / "ia_300.npz").meta["pontos_treinados"] == 300

    with open(tmp_path / "resultados" / "treino.csv", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    assert [int(l["pontos_treinados"]) for l in linhas] == [0, 100, 200, 300]

    status = json.loads((tmp_path / "resultados" / "status.json").read_text(encoding="utf-8"))
    assert status["situacao"] == "concluido"
    assert status["pontos_treinados"] == 300


def test_medir_durante_o_treino_nao_muda_o_que_a_ia_aprende(tmp_path):
    def treinar_medindo_a_cada(bloco):
        pasta = tmp_path / str(bloco)
        return treinar(
            pontos=300, bloco=bloco, pontos_avaliacao=20,
            pasta_modelos=pasta, pasta_resultados=pasta, mostrar=lambda _: None,
        )

    assert (treinar_medindo_a_cada(50).q == treinar_medindo_a_cada(300).q).all()


def test_ia_treinada_defende_melhor_que_sem_treino(tmp_path):
    treinar(
        pontos=2000, bloco=2000, checkpoints=(0,), pontos_avaliacao=20,
        pasta_modelos=tmp_path, pasta_resultados=tmp_path, mostrar=lambda _: None,
    )
    sem_treino = avaliar(AgenteQ.carregar(tmp_path / "ia_0.npz", seed=1), BotSegue(), pontos=300)
    treinada = avaliar(AgenteQ.carregar(tmp_path / "ia_2000.npz", seed=1), BotSegue(), pontos=300)
    assert treinada["rebatidas_por_ponto"] > 3 * sem_treino["rebatidas_por_ponto"]

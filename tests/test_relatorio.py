import csv

from pong import relatorio
from pong.treino import treinar


def test_relatorio_gera_tabela_graficos_e_texto(tmp_path):
    treinar(
        pontos=300, bloco=100, checkpoints=(0,), pontos_avaliacao=20,
        pasta_modelos=tmp_path, pasta_resultados=tmp_path, mostrar=lambda _: None,
    )
    relatorio.main(["--pontos", "30", "--modelos", str(tmp_path), "--resultados", str(tmp_path)])

    with open(tmp_path / "avaliacao.csv", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    assert {l["bot"] for l in linhas} == set(relatorio.BOTS_AVALIACAO)
    assert all(l["nivel"] == "sem-treino" for l in linhas)  # só o ia_0 existe aqui

    for nome in ("aprendizado.png", "niveis.png"):
        assert (tmp_path / nome).stat().st_size > 10_000
    texto = (tmp_path / "relatorio.md").read_text(encoding="utf-8")
    assert "sem treino" in texto and "1320 números" not in texto  # número formatado: 1.320

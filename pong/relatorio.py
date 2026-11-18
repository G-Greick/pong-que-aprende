"""Evidências de que a IA aprendeu: avalia cada nível contra os três bots e
desenha os gráficos.

    python -m pong.relatorio

Lê    modelos/ia_*.npz, resultados/treino.csv e resultados/status.json
Gera  resultados/avaliacao.csv   cada nível contra cada bot, em muitos pontos
      resultados/aprendizado.png a evolução ao longo do treino
      resultados/niveis.png      os níveis lado a lado
      resultados/relatorio.md    tudo isso em texto
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # só gera arquivos, não abre janela
import matplotlib.pyplot as plt  # noqa: E402

from pong.agente import NIVEIS, NOME_NIVEL, PASTA_MODELOS, AgenteQ, caminho_nivel  # noqa: E402
from pong.avaliacao import avaliar  # noqa: E402
from pong.bots import criar_bot  # noqa: E402

BOTS_AVALIACAO = ("aleatorio", "segue", "preditor")
NOME_BOT = {"aleatorio": "aleatório", "segue": "segue (treino)", "preditor": "preditor (nunca visto)"}

# cores: superfície clara, texto neutro, uma cor fixa por bot
SUPERFICIE = "#fcfcfb"
TEXTO = "#0b0b0b"
TEXTO_2 = "#52514e"
GRADE = "#e4e3df"
DESTAQUE = "#2a78d6"
COR_BOT = {"aleatorio": "#2a78d6", "segue": "#eb6834", "preditor": "#1baf7a"}

plt.rcParams.update({
    "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE, "savefig.facecolor": SUPERFICIE,
    "axes.edgecolor": GRADE, "axes.labelcolor": TEXTO_2, "text.color": TEXTO,
    "xtick.color": TEXTO_2, "ytick.color": TEXTO_2, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "axes.grid.axis": "y",
    "grid.color": GRADE, "grid.linewidth": 0.8, "font.size": 10,
})


def avaliar_niveis(pasta_modelos: Path, pontos: int, mostrar=print) -> list[dict]:
    linhas = []
    for nivel in NIVEIS:
        caminho = caminho_nivel(nivel, pasta_modelos)
        if not caminho.exists():
            mostrar(f"pulando {nivel}: {caminho} não existe")
            continue
        for bot in BOTS_AVALIACAO:
            ia = AgenteQ.carregar(caminho, seed=1)
            r = avaliar(ia, criar_bot(bot, seed=7), pontos=pontos)
            linhas.append({
                "nivel": nivel,
                "pontos_treinados": ia.meta.get("pontos_treinados", NIVEIS[nivel]),
                "bot": bot,
                "pct_pontos": round(r["pct_pontos"], 1),
                "rebatidas_por_ponto": round(r["rebatidas_por_ponto"], 2),
                "pontos": r["pontos"],
                "travados": r["travados"],
            })
            mostrar(f"{nivel:>10} vs {bot:<9} {r['pct_pontos']:5.1f}% dos pontos, "
                    f"{r['rebatidas_por_ponto']:5.2f} rebatidas/ponto, {r['travados']} travados")
    return linhas


def grafico_aprendizado(treino: list[dict], total: int, saida: Path) -> None:
    x = [int(l["pontos_treinados"]) for l in treino]
    rebatidas = [float(l["rebatidas_avaliacao"]) for l in treino]
    pct = [float(l["pct_pontos_avaliacao"]) for l in treino]

    fig, (cima, baixo) = plt.subplots(2, 1, sharex=True, figsize=(9, 6.5), dpi=150)
    fig.suptitle("A IA aprendendo a jogar", x=0.07, y=0.985, ha="left", fontsize=14, fontweight="bold")
    fig.text(0.07, 0.935, "Medida sem exploração contra o bot de treino (segue), a cada 1.000 pontos de treino",
             color=TEXTO_2)

    for ax in (cima, baixo):
        ax.axvspan(0, total / 2, color="#f0efeb", zorder=0)
        for nivel, p in NIVEIS.items():
            if p:
                ax.axvline(p, color=TEXTO_2, linewidth=0.8, linestyle=(0, (2, 3)), zorder=1)

    cima.plot(x, rebatidas, color=DESTAQUE, linewidth=2, marker="o", markersize=3.5, zorder=3)
    cima.set_ylabel("rebatidas por ponto")
    cima.set_ylim(bottom=0)
    cima.text(NIVEIS["facil"] + total * 0.012, cima.get_ylim()[1] * 0.96,
              "fase de exploração\n(ε cai de 1 para 0,05)", color=TEXTO_2, fontsize=9, va="top")
    for nivel, p in NIVEIS.items():
        if p:
            cima.text(p, cima.get_ylim()[1], f" {NOME_NIVEL[nivel]}", color=TEXTO, fontsize=9,
                      va="bottom", ha="left" if p < total else "right")

    baixo.plot(x, pct, color=DESTAQUE, linewidth=2, marker="o", markersize=3.5, zorder=3)
    baixo.axhline(50, color=TEXTO_2, linewidth=1, zorder=2)
    baixo.text(NIVEIS["medio"] + total * 0.012, 51.5, "empate (50%)", color=TEXTO_2, fontsize=9, va="bottom")
    baixo.set_ylabel("% dos pontos ganhos")
    baixo.set_ylim(0, 100)
    baixo.set_xlabel("pontos de treino jogados")
    baixo.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", ".")))

    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(saida)
    plt.close(fig)


def grafico_niveis(avaliacao: list[dict], saida: Path) -> None:
    niveis = [n for n in NIVEIS if any(l["nivel"] == n for l in avaliacao)]
    valor = {(l["nivel"], l["bot"]): l for l in avaliacao}
    largura = 0.26

    fig, eixos = plt.subplots(1, 2, figsize=(11, 4.6), dpi=150)
    fig.suptitle("Cada nível contra cada bot", x=0.05, y=0.98, ha="left", fontsize=14, fontweight="bold")
    fig.text(0.05, 0.895, "1.000 pontos por confronto, sempre com os mesmos saques", color=TEXTO_2)

    for ax, campo, titulo in (
        (eixos[0], "pct_pontos", "% dos pontos ganhos"),
        (eixos[1], "rebatidas_por_ponto", "rebatidas por ponto (defesa)"),
    ):
        for j, bot in enumerate(BOTS_AVALIACAO):
            xs = [i + (j - 1) * largura for i in range(len(niveis))]
            ys = [valor[(n, bot)][campo] for n in niveis]
            barras = ax.bar(xs, ys, width=largura - 0.03, color=COR_BOT[bot], label=NOME_BOT[bot], zorder=3)
            rotulos = [f"{y:.0f}" if campo == "pct_pontos" else f"{y:.1f}".replace(".", ",") for y in ys]
            ax.bar_label(barras, labels=rotulos, fontsize=8, color=TEXTO_2, padding=2)
        ax.set_title(titulo, loc="left", color=TEXTO, fontsize=11)
        ax.set_xticks(range(len(niveis)), [NOME_NIVEL[n] for n in niveis])
        ax.margins(y=0.12)
    eixos[0].set_ylim(0, 110)
    fig.legend(*eixos[0].get_legend_handles_labels(), loc="upper right", bbox_to_anchor=(0.98, 0.93),
               ncol=3, frameon=False, fontsize=9)

    fig.tight_layout(rect=(0, 0, 1, 0.86))
    fig.savefig(saida)
    plt.close(fig)


def escrever_relatorio(avaliacao: list[dict], status: dict, saida: Path) -> None:
    estados = status.get("estados")
    tamanho = status.get("tamanho_cerebro_bytes")
    minutos = status.get("segundos", 0) / 60
    valor = {(l["nivel"], l["bot"]): l for l in avaliacao}
    niveis = [n for n in NIVEIS if (n, "segue") in valor]

    linhas = [
        "# Relatório de evidências",
        "",
        "Gerado por `python -m pong.relatorio`.",
        "",
        "## Treino",
        "",
        f"- Adversário de treino: bot `{status.get('adversario')}`",
        f"- Pontos de treino jogados: {status.get('pontos_treinados', 0):,}".replace(",", "."),
        f"- Tempo de treino: {minutos:.1f} minutos".replace(".", ","),
        f"- Tamanho do \"cérebro\": {estados} estados × 3 ações = {estados * 3:,} números".replace(",", ".")
        + f" (float32) = {tamanho:,} bytes".replace(",", "."),
        "",
        "![aprendizado](aprendizado.png)",
        "",
        "## Níveis contra os bots",
        "",
        "Cada célula: % dos pontos ganhos pela IA · rebatidas por ponto. "
        "Pontos que passam de 3.000 passos sem ninguém errar são contados à parte (travados).",
        "",
        "| Nível | " + " | ".join(NOME_BOT[b] for b in BOTS_AVALIACAO) + " |",
        "|---|" + "---|" * len(BOTS_AVALIACAO),
    ]
    for n in niveis:
        celulas = []
        for b in BOTS_AVALIACAO:
            v = valor[(n, b)]
            trav = f" ({v['travados']} travado{'s' if v['travados'] > 1 else ''})" if v["travados"] else ""
            celulas.append(f"{v['pct_pontos']:.1f}% · {v['rebatidas_por_ponto']:.1f}{trav}".replace(".", ","))
        linhas.append(f"| {NOME_NIVEL[n]} ({NIVEIS[n]:,} pontos) | ".replace(",", ".") + " | ".join(celulas) + " |")
    linhas += [
        "",
        "Contra o aleatório quase não há rebatidas porque ele erra logo a primeira devolução. "
        "No preditor ninguém marca ponto (nem o bot segue); ali o que mede a IA é a defesa.",
        "",
        "![níveis](niveis.png)",
        "",
    ]
    saida.write_text("\n".join(linhas), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Avalia os níveis da IA e gera gráficos e relatório.")
    p.add_argument("--pontos", type=int, default=1000, help="pontos por confronto")
    p.add_argument("--modelos", type=Path, default=PASTA_MODELOS)
    p.add_argument("--resultados", type=Path, default=Path("resultados"))
    a = p.parse_args(argv)

    with open(a.resultados / "treino.csv", encoding="utf-8") as f:
        treino = list(csv.DictReader(f))
    status = json.loads((a.resultados / "status.json").read_text(encoding="utf-8"))

    avaliacao = avaliar_niveis(a.modelos, a.pontos, mostrar=lambda m: print(m, flush=True))
    with open(a.resultados / "avaliacao.csv", "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(avaliacao[0]))
        escritor.writeheader()
        escritor.writerows(avaliacao)

    grafico_aprendizado(treino, status["pontos_total"], a.resultados / "aprendizado.png")
    grafico_niveis(avaliacao, a.resultados / "niveis.png")
    escrever_relatorio(avaliacao, status, a.resultados / "relatorio.md")
    print(f"pronto: {a.resultados / 'relatorio.md'}")


if __name__ == "__main__":
    main()

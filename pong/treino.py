"""Treino da IA no modo rápido (sem tela).

    python -m pong.treino --pontos 30000

Gera:
  modelos/ia_<pontos>.npz   a tabela Q em alguns momentos do treino (viram os níveis)
  resultados/treino.csv     a evolução, bloco a bloco (vira o gráfico)
  resultados/status.json    o andamento, atualizado durante o treino (lido pelo chat)
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path

from pong.agente import AgenteQ, recompensa
from pong.avaliacao import avaliar
from pong.bots import criar_bot
from pong.jogo import DIR, ESQ, Config, Pong, adversario

INFINITO = 10**9


def epsilon_no(ponto: int, total: int, eps_min: float = 0.05, fracao: float = 0.5) -> float:
    """Exploração cai em linha reta de 1.0 (só ações ao acaso) até eps_min,
    ao longo da primeira metade do treino, e fica em eps_min depois."""
    return max(eps_min, 1.0 - ponto / (fracao * total))


def jogar_ponto(jogo: Pong, agente: AgenteQ, bot, epsilon: float, lado: str = DIR, limite_passos: int = 3000):
    """Joga um ponto inteiro, aprendendo a cada decisão.
    Devolve (quem marcou ou None se travou, rebatidas da IA, passos)."""
    outro = adversario(lado)
    estado = agente.disc(jogo, lado)
    rebatidas = passos = 0
    while True:
        acao = agente.escolher(estado, epsilon)
        r = 0.0
        for _ in range(agente.repetir):
            acoes = {lado: acao, outro: bot.agir(jogo, outro)}
            evento = jogo.step(acoes[ESQ], acoes[DIR])
            passos += 1
            r += recompensa(evento, lado)
            rebatidas += evento.rebateu == lado
            if evento.ponto:
                break
        proximo = agente.disc(jogo, lado)
        agente.aprender(estado, acao, r, proximo, terminal=evento.ponto is not None)
        if evento.ponto:
            return evento.ponto, rebatidas, passos
        if passos >= limite_passos:
            jogo.sacar(jogo.rng.choice((ESQ, DIR)))
            return None, rebatidas, passos
        estado = proximo


def _escrever_json(caminho: Path, dados: dict) -> None:
    # grava num arquivo temporário e troca, para o chat nunca ler um JSON pela metade
    tmp = caminho.with_suffix(".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(caminho)


def treinar(
    pontos: int = 30_000,
    adversario_treino: str = "segue",
    seed: int = 0,
    checkpoints: tuple[int, ...] = (0,),
    bloco: int = 500,
    pontos_avaliacao: int = 200,
    pasta_modelos: Path = Path("modelos"),
    pasta_resultados: Path = Path("resultados"),
    mostrar=print,
) -> AgenteQ:
    pasta_modelos.mkdir(parents=True, exist_ok=True)
    pasta_resultados.mkdir(parents=True, exist_ok=True)

    jogo = Pong(Config(pontos_para_vencer=INFINITO), seed=seed)
    agente = AgenteQ(seed=seed)
    bot = criar_bot(adversario_treino, seed)
    checkpoints = set(checkpoints) | {pontos}

    def salvar_checkpoint(p: int) -> None:
        agente.meta = {"pontos_treinados": p, "adversario": adversario_treino, "seed": seed}
        agente.salvar(pasta_modelos / f"ia_{p}.npz")

    status = {
        "situacao": "treinando",
        "inicio": datetime.now().isoformat(timespec="seconds"),
        "pontos_total": pontos,
        "adversario": adversario_treino,
        "estados": agente.disc.n_estados,
        "tamanho_cerebro_bytes": agente.tamanho_bytes,
    }
    colunas = [
        "pontos_treinados", "epsilon", "pct_pontos_treino", "pct_pontos_avaliacao",
        "rebatidas_por_ponto", "passos_por_ponto", "segundos",
    ]
    arquivo_csv = open(pasta_resultados / "treino.csv", "w", newline="", encoding="utf-8")
    escritor = csv.DictWriter(arquivo_csv, fieldnames=colunas)
    escritor.writeheader()

    if 0 in checkpoints:
        salvar_checkpoint(0)

    inicio = time.perf_counter()
    ganhos = jogados = rebatidas = passos = 0
    with arquivo_csv:
        for p in range(1, pontos + 1):
            epsilon = epsilon_no(p, pontos)
            marcou, reb, n = jogar_ponto(jogo, agente, bot, epsilon)
            jogados += marcou is not None
            ganhos += marcou == DIR
            rebatidas += reb
            passos += n

            if p in checkpoints:
                salvar_checkpoint(p)
            if p % bloco and p != pontos:
                continue

            # fim de bloco: mede a IA sem exploração, sempre nos mesmos saques
            aval = avaliar(agente, criar_bot(adversario_treino, seed), pontos=pontos_avaliacao)
            linha = {
                "pontos_treinados": p,
                "epsilon": round(epsilon, 3),
                "pct_pontos_treino": round(100 * ganhos / max(jogados, 1), 1),
                "pct_pontos_avaliacao": round(aval["pct_pontos"], 1),
                "rebatidas_por_ponto": round(rebatidas / max(jogados, 1), 2),
                "passos_por_ponto": round(passos / max(jogados, 1)),
                "segundos": round(time.perf_counter() - inicio, 1),
            }
            escritor.writerow(linha)
            arquivo_csv.flush()
            status.update(linha, atualizado=datetime.now().isoformat(timespec="seconds"))
            _escrever_json(pasta_resultados / "status.json", status)
            mostrar(
                f"{p:>7} pontos | eps {linha['epsilon']:.2f} | avaliação {linha['pct_pontos_avaliacao']:5.1f}% "
                f"| {linha['rebatidas_por_ponto']:.2f} rebatidas/ponto | {linha['segundos']:.0f}s"
            )
            ganhos = jogados = rebatidas = passos = 0

    status["situacao"] = "concluido"
    _escrever_json(pasta_resultados / "status.json", status)
    return agente


def main() -> None:
    p = argparse.ArgumentParser(description="Treina a IA do Pong por Q-learning.")
    p.add_argument("--pontos", type=int, default=30_000, help="quantos pontos jogar no treino")
    p.add_argument("--adversario", default="segue", help="bot de treino: segue, preditor, aleatorio")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--checkpoints", type=int, nargs="*", default=[0], help="momentos (em pontos) para salvar a IA")
    p.add_argument("--bloco", type=int, default=500, help="de quantos em quantos pontos medir e registrar")
    a = p.parse_args()
    treinar(a.pontos, a.adversario, a.seed, tuple(a.checkpoints), a.bloco)


if __name__ == "__main__":
    main()

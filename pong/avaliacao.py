"""Mede o quanto um jogador é bom: joga muitos pontos contra um adversário
e conta quantos ganhou. Nada aprende aqui (a IA joga só com o que já sabe)."""

from __future__ import annotations

from pong.jogo import DIR, ESQ, Config, Pong, adversario

INFINITO = 10**9


def avaliar(
    jogador,
    oponente,
    pontos: int = 1000,
    seed: int = 12345,
    lado: str = DIR,
    limite_passos: int = 3000,
) -> dict:
    """Joga `pontos` pontos e devolve as estatísticas do ponto de vista de `jogador`.

    Se um ponto passar de `limite_passos` sem ninguém marcar (dois jogadores
    que não erram), ele é contado como "travado" e a bola é sacada de novo.
    A semente fixa faz todo mundo enfrentar a mesma sequência de saques.
    """
    jogo = Pong(Config(pontos_para_vencer=INFINITO), seed=seed)
    outro = adversario(lado)
    ganhos = rebatidas = jogados = travados = passos_no_ponto = 0

    while jogados + travados < pontos:
        acao = {lado: jogador.agir(jogo, lado), outro: oponente.agir(jogo, outro)}
        evento = jogo.step(acao[ESQ], acao[DIR])
        passos_no_ponto += 1
        rebatidas += evento.rebateu == lado
        if evento.ponto:
            jogados += 1
            ganhos += evento.ponto == lado
            passos_no_ponto = 0
        elif passos_no_ponto >= limite_passos:
            travados += 1
            passos_no_ponto = 0
            jogo.sacar(jogo.rng.choice((ESQ, DIR)))

    return {
        "pct_pontos": 100 * ganhos / jogados if jogados else 0.0,
        "rebatidas_por_ponto": rebatidas / jogados if jogados else 0.0,
        "pontos": jogados,
        "travados": travados,
    }

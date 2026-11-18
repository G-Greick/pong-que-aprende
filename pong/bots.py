"""Jogadores escritos à mão (scripts), usados como adversários da IA.

Todo jogador tem o mesmo formato: `agir(jogo, lado) -> acao`. A IA treinada
também segue esse formato, então qualquer um enfrenta qualquer um.
"""

from __future__ import annotations

import random

from pong.jogo import ACOES, DESCE, ESQ, PARADO, SOBE, Pong


def bola_vindo(jogo: Pong, lado: str) -> bool:
    return (jogo.bola_vx < 0) == (lado == ESQ)


def mover_para(y_raquete: float, alvo: float, zona_morta: float) -> int:
    if alvo < y_raquete - zona_morta:
        return SOBE
    if alvo > y_raquete + zona_morta:
        return DESCE
    return PARADO


def prever_y(jogo: Pong, lado: str) -> float:
    """Altura em que a bola vai chegar à raquete de `lado`, contando os quiques."""
    meia = jogo.cfg.bola_tam / 2
    distancia = abs(jogo.x_face(lado) - jogo.bola_x) - meia
    passos = distancia / abs(jogo.bola_vx)
    y = jogo.bola_y + jogo.bola_vy * passos

    # "desdobra" os quiques: a trajetória refletida nas paredes vira uma reta
    curso = jogo.cfg.altura - 2 * meia
    y = (y - meia) % (2 * curso)
    if y > curso:
        y = 2 * curso - y
    return y + meia


class BotAleatorio:
    """Aperta botões ao acaso. Serve de piso: qualquer IA tem que vencer este."""

    nome = "aleatorio"

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def agir(self, jogo: Pong, lado: str) -> int:
        return self.rng.choice(ACOES)


class BotSegue:
    """O script clássico: persegue a altura da bola quando ela vem e volta
    para o meio quando ela vai embora. É o adversário de treino da IA."""

    nome = "segue"

    def __init__(self, zona_morta: float = 10):
        self.zona_morta = zona_morta

    def agir(self, jogo: Pong, lado: str) -> int:
        alvo = jogo.bola_y if bola_vindo(jogo, lado) else jogo.cfg.altura / 2
        return mover_para(jogo.raquete[lado], alvo, self.zona_morta)


class BotPreditor:
    """Estilo diferente do de treino: calcula onde a bola vai chegar e vai
    direto para lá. A cada jogada sorteia com que parte da raquete vai bater,
    para devolver com ângulo (o alcance da raquete é 45 px a partir do centro).

    Serve para testar se a IA continua boa contra quem ela nunca viu."""

    nome = "preditor"

    def __init__(self, erro: float = 35, seed: int | None = None):
        self.erro = erro
        self.rng = random.Random(seed)
        self._desvio = 0.0
        self._vinha = False

    def agir(self, jogo: Pong, lado: str) -> int:
        vindo = bola_vindo(jogo, lado)
        if vindo and not self._vinha:  # nova jogada: sorteia onde vai mirar
            self._desvio = self.rng.uniform(-self.erro, self.erro)
        self._vinha = vindo
        if not vindo:
            return mover_para(jogo.raquete[lado], jogo.cfg.altura / 2, 5)
        return mover_para(jogo.raquete[lado], prever_y(jogo, lado) + self._desvio, 5)


BOTS = {
    "aleatorio": lambda seed: BotAleatorio(seed=seed),
    "segue": lambda seed: BotSegue(),
    "preditor": lambda seed: BotPreditor(seed=seed),
}


def criar_bot(nome: str, seed: int | None = None):
    if nome not in BOTS:
        raise ValueError(f"bot desconhecido: {nome!r} (opções: {', '.join(BOTS)})")
    return BOTS[nome](seed)

"""Simulação do Pong, sem desenho.

Toda a regra do jogo mora aqui. O modo visual (pygame) e o treino da IA usam
esta mesma classe, então o jogo em que a IA treina é exatamente o jogo que o
humano joga.

Coordenadas em pixels, origem no canto superior esquerdo, y cresce para baixo
(mesma convenção do pygame). Posições são sempre do CENTRO dos objetos.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

# Cada raquete, a cada passo, só pode fazer uma destas três coisas.
PARADO, SOBE, DESCE = 0, 1, 2
ACOES = (PARADO, SOBE, DESCE)
_SENTIDO_ACAO = {PARADO: 0, SOBE: -1, DESCE: 1}

ESQ, DIR = "esq", "dir"


def adversario(lado: str) -> str:
    return DIR if lado == ESQ else ESQ


@dataclass(frozen=True)
class Config:
    largura: int = 800
    altura: int = 600
    raquete_altura: int = 80
    raquete_largura: int = 10
    raquete_margem: int = 20  # distância da raquete até a borda lateral
    raquete_vel: float = 7.0  # pixels por passo
    bola_tam: int = 10
    bola_vel_inicial: float = 6.0
    bola_vel_max: float = 14.0
    aceleracao: float = 1.05  # a bola fica 5% mais rápida a cada rebatida
    angulo_max: float = 60.0  # graus; rebatida na ponta da raquete sai com este ângulo
    angulo_saque: float = 30.0  # graus; o saque sai com ângulo aleatório até este
    pontos_para_vencer: int = 11


@dataclass
class Evento:
    """O que aconteceu em um passo. A recompensa da IA é calculada a partir disto."""

    rebateu: str | None = None  # ESQ ou DIR
    ponto: str | None = None  # quem fez o ponto
    fim: bool = False


class Pong:
    def __init__(self, config: Config | None = None, seed: int | None = None):
        self.cfg = config or Config()
        self.rng = random.Random(seed)
        self.reiniciar()

    def reiniciar(self) -> None:
        """Começa uma partida nova, com placar zerado."""
        meio = self.cfg.altura / 2
        self.placar = {ESQ: 0, DIR: 0}
        self.raquete = {ESQ: meio, DIR: meio}
        self.vencedor: str | None = None
        self.passos = 0
        self.sacar(self.rng.choice((ESQ, DIR)))

    @property
    def terminou(self) -> bool:
        return self.vencedor is not None

    def x_face(self, lado: str) -> float:
        """x da face da raquete que encosta na bola."""
        c = self.cfg
        if lado == ESQ:
            return c.raquete_margem + c.raquete_largura
        return c.largura - c.raquete_margem - c.raquete_largura

    def step(self, acao_esq: int, acao_dir: int) -> Evento:
        """Avança um passo do jogo (1/60 s no modo visual)."""
        if self.terminou:
            raise RuntimeError("a partida terminou; chame reiniciar()")

        self._mover_raquete(ESQ, acao_esq)
        self._mover_raquete(DIR, acao_dir)

        evento = Evento()
        x0, y0 = self.bola_x, self.bola_y
        self.bola_x += self.bola_vx
        self.bola_y += self.bola_vy

        lado = ESQ if self.bola_vx < 0 else DIR
        y_contato = self._contato_com_raquete(lado, x0, y0)
        if y_contato is not None:
            self._rebater(lado, y_contato)
            evento.rebateu = lado

        self._quicar_nas_paredes()

        marcou = self._quem_marcou()
        if marcou:
            self.placar[marcou] += 1
            evento.ponto = marcou
            if self.placar[marcou] >= self.cfg.pontos_para_vencer:
                self.vencedor = marcou
                evento.fim = True
            else:
                self.sacar(adversario(marcou))

        self.passos += 1
        return evento

    def _mover_raquete(self, lado: str, acao: int) -> None:
        if acao not in _SENTIDO_ACAO:
            raise ValueError(f"ação inválida: {acao!r} (use PARADO, SOBE ou DESCE)")
        meia = self.cfg.raquete_altura / 2
        y = self.raquete[lado] + _SENTIDO_ACAO[acao] * self.cfg.raquete_vel
        self.raquete[lado] = min(max(y, meia), self.cfg.altura - meia)

    def sacar(self, para: str) -> None:
        """Bola volta ao centro e sai em direção a `para`."""
        c = self.cfg
        self.bola_x = c.largura / 2
        self.bola_y = c.altura / 2
        angulo = math.radians(self.rng.uniform(-c.angulo_saque, c.angulo_saque))
        sentido = -1 if para == ESQ else 1
        self.bola_vx = sentido * c.bola_vel_inicial * math.cos(angulo)
        self.bola_vy = c.bola_vel_inicial * math.sin(angulo)

    def _contato_com_raquete(self, lado: str, x0: float, y0: float) -> float | None:
        """Devolve o y em que a bola tocou a raquete neste passo, ou None.

        Em vez de olhar só a posição final (a bola rápida poderia "pular" a
        raquete), verifica se a borda da bola cruzou a face da raquete durante
        o passo e calcula onde ela estava nesse momento.
        """
        meia = self.cfg.bola_tam / 2
        face = self.x_face(lado)
        if lado == ESQ:
            antes, depois = x0 - meia, self.bola_x - meia
            cruzou = antes >= face > depois
        else:
            antes, depois = x0 + meia, self.bola_x + meia
            cruzou = antes <= face < depois
        if not cruzou:
            return None

        t = (face - antes) / (depois - antes)
        y = y0 + t * (self.bola_y - y0)
        alcance = self.cfg.raquete_altura / 2 + meia
        return y if abs(y - self.raquete[lado]) <= alcance else None

    def _rebater(self, lado: str, y_contato: float) -> None:
        """Quanto mais longe do centro da raquete, mais inclinada a bola volta."""
        c = self.cfg
        meia = c.bola_tam / 2
        deslocamento = (y_contato - self.raquete[lado]) / (c.raquete_altura / 2 + meia)
        deslocamento = min(max(deslocamento, -1.0), 1.0)
        angulo = math.radians(deslocamento * c.angulo_max)
        vel = min(math.hypot(self.bola_vx, self.bola_vy) * c.aceleracao, c.bola_vel_max)
        sentido = 1 if lado == ESQ else -1

        self.bola_vx = sentido * vel * math.cos(angulo)
        self.bola_vy = vel * math.sin(angulo)
        self.bola_x = self.x_face(lado) + sentido * meia
        self.bola_y = y_contato

    def _quicar_nas_paredes(self) -> None:
        meia = self.cfg.bola_tam / 2
        if self.bola_y - meia < 0:
            self.bola_y = 2 * meia - self.bola_y
            self.bola_vy = abs(self.bola_vy)
        elif self.bola_y + meia > self.cfg.altura:
            self.bola_y = 2 * (self.cfg.altura - meia) - self.bola_y
            self.bola_vy = -abs(self.bola_vy)

    def _quem_marcou(self) -> str | None:
        """Ponto quando a bola sai inteira da quadra por um dos lados."""
        meia = self.cfg.bola_tam / 2
        if self.bola_x + meia < 0:
            return DIR
        if self.bola_x - meia > self.cfg.largura:
            return ESQ
        return None

"""IA que aprende a jogar por Q-learning em tabela.

A IA não sabe a regra "siga a bola". Ela só recebe:
  - o que "enxerga": o estado do jogo resumido em poucas faixas (Discretizador);
  - o que pode fazer: SOBE, DESCE ou PARADO;
  - uma recompensa: +1 quando rebate, +1 quando marca ponto, -1 quando deixa passar.

A tabela Q guarda, para cada estado e cada ação, quanta recompensa futura a IA
espera receber. Jogando, ela ajusta esses números e passa a escolher a ação de
maior valor. Essa tabela é todo o "cérebro" dela.
"""

from __future__ import annotations

import json
import random
from bisect import bisect
from pathlib import Path

import numpy as np

from pong.jogo import ACOES, ESQ, PARADO, Evento, Pong, adversario

# Os níveis de dificuldade são a mesma IA salva em momentos diferentes do treino.
NIVEIS = {"sem-treino": 0, "facil": 2000, "medio": 10000, "dificil": 30000}
NOME_NIVEL = {"sem-treino": "sem treino", "facil": "fácil", "medio": "médio", "dificil": "difícil"}
PASTA_MODELOS = Path("modelos")


def caminho_nivel(nivel: str, pasta: Path = PASTA_MODELOS) -> Path:
    return pasta / f"ia_{NIVEIS[nivel]}.npz"


def caminho_jogando(nivel: str, pasta: Path = PASTA_MODELOS) -> Path:
    """Onde fica a IA que continua aprendendo nas partidas (os níveis originais não mudam)."""
    return pasta / "jogando" / f"ia_{nivel}.npz"


RECOMPENSA_REBATER = 1.0
RECOMPENSA_SOFRER = -1.0
RECOMPENSA_MARCAR = 1.0


def recompensa(evento: Evento, lado: str) -> float:
    r = 0.0
    if evento.rebateu == lado:
        r += RECOMPENSA_REBATER
    if evento.ponto == adversario(lado):
        r += RECOMPENSA_SOFRER
    if evento.ponto == lado:
        r += RECOMPENSA_MARCAR
    return r


class Discretizador:
    """Resume o jogo, do ponto de vista de um lado, em um número inteiro.

    Faixas (limites em pixels):
      dy    = altura da bola menos altura da minha raquete (11 faixas)
      dist  = distância horizontal da bola até a minha raquete (4 faixas)
      vy    = velocidade vertical da bola (5 faixas: sobe rápido ... desce rápido)
      vindo = a bola vem para mim ou vai embora (2)

    Tudo é relativo a "minha raquete", então a mesma tabela joga dos dois lados.
    """

    DY = (-200, -100, -50, -25, -10, 10, 25, 50, 100, 200)
    DIST = (100, 250, 450)
    VY = (-4, -1, 1, 4)

    def __init__(self):
        self.n_dy = len(self.DY) + 1
        self.n_dist = len(self.DIST) + 1
        self.n_vy = len(self.VY) + 1
        self.n_estados = self.n_dy * self.n_dist * self.n_vy * 2

    def __call__(self, jogo: Pong, lado: str) -> int:
        vindo = int((jogo.bola_vx < 0) == (lado == ESQ))
        dy = bisect(self.DY, jogo.bola_y - jogo.raquete[lado])
        dist = bisect(self.DIST, abs(jogo.bola_x - jogo.x_face(lado)))
        vy = bisect(self.VY, jogo.bola_vy)
        return ((dy * self.n_dist + dist) * self.n_vy + vy) * 2 + vindo


class AgenteQ:
    def __init__(
        self,
        alpha: float = 0.1,
        gamma: float = 0.99,
        repetir: int = 4,
        seed: int | None = None,
    ):
        self.alpha = alpha  # taxa de aprendizado: quanto cada experiência muda a tabela
        self.gamma = gamma  # desconto: quanto vale uma recompensa que vem mais tarde
        self.repetir = repetir  # decide a cada `repetir` passos (~15 decisões/s no visual)
        self.disc = Discretizador()
        self.q = np.zeros((self.disc.n_estados, len(ACOES)), dtype=np.float32)
        self.rng = random.Random(seed)
        self.meta: dict = {}
        self._acao = PARADO
        self._restantes = 0

    def escolher(self, estado: int, epsilon: float = 0.0) -> int:
        """Com probabilidade epsilon explora (ação ao acaso); senão, a melhor da tabela.
        Empates são sorteados, então a IA sem treino (tabela zerada) joga ao acaso."""
        if self.rng.random() < epsilon:
            return self.rng.choice(ACOES)
        linha = self.q[estado]
        melhor = linha.max()
        return self.rng.choice([a for a in ACOES if linha[a] == melhor])

    def aprender(self, estado: int, acao: int, r: float, proximo: int, terminal: bool) -> None:
        """Atualização do Q-learning:
        Q(s,a) <- Q(s,a) + alpha * (r + gamma * max Q(s',·) - Q(s,a))"""
        alvo = r if terminal else r + self.gamma * self.q[proximo].max()
        self.q[estado, acao] += self.alpha * (alvo - self.q[estado, acao])

    def agir(self, jogo: Pong, lado: str) -> int:
        """Para jogar (sem aprender): mesmo formato dos bots, chamado a cada passo."""
        if self._restantes == 0:
            self._acao = self.escolher(self.disc(jogo, lado))
            self._restantes = self.repetir
        self._restantes -= 1
        return self._acao

    @property
    def tamanho_bytes(self) -> int:
        return self.q.nbytes

    def salvar(self, caminho: str | Path) -> None:
        caminho = Path(caminho)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        config = {"alpha": self.alpha, "gamma": self.gamma, "repetir": self.repetir}
        np.savez_compressed(caminho, q=self.q, config=json.dumps(config), meta=json.dumps(self.meta))

    @classmethod
    def carregar(cls, caminho: str | Path, seed: int | None = None) -> AgenteQ:
        dados = np.load(caminho)
        agente = cls(**json.loads(str(dados["config"])), seed=seed)
        if dados["q"].shape != agente.q.shape:
            raise ValueError(f"{caminho}: tabela {dados['q'].shape}, esperado {agente.q.shape}")
        agente.q = dados["q"].copy()  # cópia gravável: a IA pode continuar aprendendo
        agente.meta = json.loads(str(dados["meta"]))
        return agente


class AgenteAprendendo:
    """A IA joga e aprende ao mesmo tempo, durante a partida no modo visual.

    É o mesmo Q-learning do treino rápido (pong/treino.py), só que no ritmo da
    tela: a cada decisão ela atualiza a tabela com a recompensa que recebeu desde
    a decisão anterior. Depois de cada ponto, a tabela é salva em `caminho`.
    """

    def __init__(self, agente: AgenteQ, caminho: str | Path, epsilon: float = 0.05):
        self.agente = agente
        self.caminho = Path(caminho)
        self.epsilon = epsilon  # mesma exploração do fim do treino
        self.meta = agente.meta
        self.meta.setdefault("pontos_jogando", 0)
        self.lado: str | None = None
        self._estado: int | None = None
        self._acao = PARADO
        self._r = 0.0
        self._restantes = 0

    @property
    def pontos_jogando(self) -> int:
        return self.meta["pontos_jogando"]

    @property
    def tamanho_bytes(self) -> int:
        return self.agente.tamanho_bytes

    def agir(self, jogo: Pong, lado: str) -> int:
        self.lado = lado
        if self._restantes == 0:
            estado = self.agente.disc(jogo, lado)
            if self._estado is not None:  # aprende com a decisão anterior
                self.agente.aprender(self._estado, self._acao, self._r, estado, terminal=False)
            self._acao = self.agente.escolher(estado, self.epsilon)
            self._estado, self._r = estado, 0.0
            self._restantes = self.agente.repetir
        self._restantes -= 1
        return self._acao

    def observar(self, evento: Evento) -> None:
        """Chamado depois de cada passo do jogo, com o que aconteceu nele."""
        if self._estado is None or self.lado is None:
            return
        self._r += recompensa(evento, self.lado)
        if evento.ponto:  # fim do ponto: o próximo saque começa uma decisão nova
            self.agente.aprender(self._estado, self._acao, self._r, 0, terminal=True)
            self._estado, self._r, self._restantes = None, 0.0, 0
            self.meta["pontos_jogando"] += 1
            self.salvar()

    def salvar(self) -> None:
        self.agente.meta = self.meta
        self.agente.salvar(self.caminho)

"""Modo visual: jogue contra a IA.

    python -m pong.jogar                      você (W/S ou setas) contra a IA difícil
    python -m pong.jogar --nivel facil        níveis: sem-treino, facil, medio, dificil
    python -m pong.jogar --oponente segue     contra um bot escrito à mão
    python -m pong.jogar --controle mouse     raquete segue o mouse (com a mesma velocidade da IA)
    python -m pong.jogar --assistir           IA contra o bot "segue", sem humano

Teclas: P pausa, R recomeça, F11 tela cheia, ESC sai.

A tela só desenha: quem manda é a mesma classe Pong usada no treino.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from collections import deque

import numpy as np

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

from pong.agente import NIVEIS, NOME_NIVEL, PASTA_MODELOS, AgenteQ, caminho_nivel
from pong.bots import BOTS, BotSegue, criar_bot, mover_para
from pong.jogo import DESCE, DIR, ESQ, PARADO, SOBE, Config, Pong
from pong.partidas import PASTA as PASTA_RESULTADOS
from pong.partidas import RegistroPartida

FPS = 60
ESPERA_SAQUE = 40  # quadros parados antes de cada saque

FUNDO = (14, 16, 32)
LINHA = (60, 64, 100)
TEXTO = (235, 235, 245)
TEXTO_FRACO = (130, 134, 170)
COR = {ESQ: (79, 209, 255), DIR: (255, 79, 139)}


# --- jogadores ----------------------------------------------------------------


class HumanoTeclado:
    def agir(self, jogo: Pong, lado: str) -> int:
        k = pygame.key.get_pressed()
        sobe = k[pygame.K_w] or k[pygame.K_UP]
        desce = k[pygame.K_s] or k[pygame.K_DOWN]
        if sobe and not desce:
            return SOBE
        if desce and not sobe:
            return DESCE
        return PARADO


class HumanoMouse:
    """A raquete vai atrás do mouse, mas com as mesmas três ações e a mesma
    velocidade da IA: não há teletransporte."""

    def agir(self, jogo: Pong, lado: str) -> int:
        return mover_para(jogo.raquete[lado], pygame.mouse.get_pos()[1], jogo.cfg.raquete_vel / 2)


def criar_oponente(nome: str):
    if nome in BOTS:
        bot = criar_bot(nome)
        return bot, f"bot {nome}", "escrito à mão"
    if nome not in NIVEIS:
        raise SystemExit(f"oponente desconhecido: {nome} (níveis: {', '.join(NIVEIS)}; bots: {', '.join(BOTS)})")
    caminho = caminho_nivel(nome, PASTA_MODELOS)
    if not caminho.exists():
        raise SystemExit(f"modelo {caminho} não existe; treine antes com: python -m pong.treino")
    ia = AgenteQ.carregar(caminho)
    treino = ia.meta.get("pontos_treinados", NIVEIS[nome])
    pontos = f"{treino:,}".replace(",", ".")
    kb = f"{ia.tamanho_bytes / 1024:.1f}".replace(".", ",")
    return ia, f"IA · {NOME_NIVEL[nome]}", f"{pontos} pontos de treino · {kb} KB"


# --- efeitos ------------------------------------------------------------------


def _bip(freq: float, ms: int, volume: float = 0.25):
    """Gera um bipe de onda quadrada, no estilo dos fliperamas antigos."""
    taxa, _, canais = pygame.mixer.get_init()
    t = np.arange(int(taxa * ms / 1000)) / taxa
    onda = np.sign(np.sin(2 * np.pi * freq * t)) * np.linspace(1, 0, t.size) * volume
    dados = (onda * 32767).astype(np.int16)
    if canais == 2:
        dados = np.ascontiguousarray(np.column_stack([dados, dados]))
    return pygame.sndarray.make_sound(dados)


class Efeitos:
    def __init__(self):
        self.rastro: deque[tuple[float, float]] = deque(maxlen=10)
        self.brilho = {ESQ: 0, DIR: 0}
        self.tremor = 0
        self.particulas: list[list[float]] = []
        self.sons = {}
        try:
            pygame.mixer.init()
            self.sons = {"raquete": _bip(440, 60), "parede": _bip(330, 40), "ponto": _bip(160, 300)}
        except pygame.error:
            pass  # sem placa de som: joga mudo

    def tocar(self, nome: str) -> None:
        if nome in self.sons:
            self.sons[nome].play()

    def registrar(self, jogo: Pong, evento, vy_antes: float) -> None:
        self.rastro.append((jogo.bola_x, jogo.bola_y))
        if evento.rebateu:
            self.brilho[evento.rebateu] = 12
            self.tocar("raquete")
            for _ in range(12):
                vx = random.uniform(1, 4) * (1 if evento.rebateu == ESQ else -1)
                self.particulas.append([jogo.bola_x, jogo.bola_y, vx, random.uniform(-3, 3), 20, evento.rebateu])
        elif (jogo.bola_vy > 0) != (vy_antes > 0) and not evento.ponto:
            self.tocar("parede")
        if evento.ponto:
            self.tremor = 14
            self.rastro.clear()
            self.tocar("ponto")

    def avancar(self) -> None:
        self.brilho = {lado: max(0, v - 1) for lado, v in self.brilho.items()}
        self.tremor = max(0, self.tremor - 1)
        for p in self.particulas:
            p[0] += p[2]
            p[1] += p[3]
            p[4] -= 1
        self.particulas = [p for p in self.particulas if p[4] > 0]

    def deslocamento(self) -> tuple[int, int]:
        if not self.tremor:
            return 0, 0
        return random.randint(-self.tremor, self.tremor) // 2, random.randint(-self.tremor, self.tremor) // 2


# --- desenho ------------------------------------------------------------------


class Tela:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.superficie = pygame.display.set_mode((cfg.largura, cfg.altura), pygame.SCALED)
        pygame.display.set_caption("Pong que aprende — Arcade Pixel")
        self.quadro = pygame.Surface((cfg.largura, cfg.altura))
        self.fonte_placar = pygame.font.Font(None, 96)
        self.fonte = pygame.font.Font(None, 30)
        self.fonte_pequena = pygame.font.Font(None, 22)

    def texto(self, fonte, conteudo: str, cor, centro: tuple[float, float]) -> None:
        img = fonte.render(conteudo, True, cor)
        self.quadro.blit(img, img.get_rect(center=(int(centro[0]), int(centro[1]))))

    def desenhar(self, jogo: Pong, efeitos: Efeitos, nomes: dict, detalhe: str, aviso: str | None) -> None:
        c, q = self.cfg, self.quadro
        q.fill(FUNDO)
        for y in range(0, c.altura - 40, 30):
            pygame.draw.rect(q, LINHA, (c.largura // 2 - 2, y + 8, 4, 14))

        for i, lado in enumerate((ESQ, DIR)):
            x = c.largura * (0.25 + 0.5 * i)
            self.texto(self.fonte_placar, str(jogo.placar[lado]), TEXTO, (x, 60))
            self.texto(self.fonte, nomes[lado], COR[lado], (x, 115))
        self.texto(self.fonte_pequena, detalhe, TEXTO_FRACO, (c.largura * 0.75, 138))

        for x, y, _, _, vida, lado in efeitos.particulas:
            pygame.draw.rect(q, COR[lado], (x - 2, y - 2, 4, 4))
        for i, (x, y) in enumerate(efeitos.rastro):
            tam = c.bola_tam * (i + 1) / (len(efeitos.rastro) + 1)
            cor = tuple(int(f + (t - f) * (i + 1) / 14) for f, t in zip(FUNDO, TEXTO))
            pygame.draw.rect(q, cor, (x - tam / 2, y - tam / 2, tam, tam))

        for lado in (ESQ, DIR):
            x = jogo.x_face(lado) - (c.raquete_largura if lado == ESQ else 0)
            ret = pygame.Rect(x, jogo.raquete[lado] - c.raquete_altura / 2, c.raquete_largura, c.raquete_altura)
            if efeitos.brilho[lado]:
                pygame.draw.rect(q, COR[lado], ret.inflate(efeitos.brilho[lado], efeitos.brilho[lado]), border_radius=4)
            pygame.draw.rect(q, TEXTO if efeitos.brilho[lado] else COR[lado], ret, border_radius=3)

        b = c.bola_tam
        pygame.draw.rect(q, TEXTO, (jogo.bola_x - b / 2, jogo.bola_y - b / 2, b, b))

        self.texto(
            self.fonte_pequena, "W/S ou setas · P pausa · R recomeça · F11 tela cheia · ESC sai",
            TEXTO_FRACO, (c.largura / 2, c.altura - 16),
        )
        if aviso:
            veu = pygame.Surface((c.largura, c.altura), pygame.SRCALPHA)
            veu.fill((0, 0, 0, 150))
            q.blit(veu, (0, 0))
            for i, linha in enumerate(aviso.split("\n")):
                fonte = self.fonte_placar if i == 0 else self.fonte
                self.texto(fonte, linha, TEXTO, (c.largura / 2, c.altura / 2 - 30 + i * 60))

        self.superficie.fill(FUNDO)
        self.superficie.blit(q, efeitos.deslocamento())
        pygame.display.flip()


# --- laço principal -------------------------------------------------------------


def rodar(args: argparse.Namespace, max_quadros: int | None = None) -> None:
    pygame.init()
    cfg = Config(pontos_para_vencer=args.pontos)
    tela = Tela(cfg)
    relogio = pygame.time.Clock()

    direita, nome_dir, detalhe = criar_oponente(args.oponente or args.nivel)
    if args.assistir:
        esquerda, nome_esq = BotSegue(), "bot segue"
    elif args.controle == "mouse":
        esquerda, nome_esq = HumanoMouse(), "você"
    else:
        esquerda, nome_esq = HumanoTeclado(), "você"
    nomes = {ESQ: nome_esq, DIR: nome_dir}

    jogo = Pong(cfg)
    efeitos = Efeitos()
    espera, pausado, quadros = ESPERA_SAQUE, False, 0

    registro = RegistroPartida(nomes, PASTA_RESULTADOS)  # placar para o chat consultar
    registro.inicio(jogo)

    while max_quadros is None or quadros < max_quadros:
        quadros += 1
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                registro.interrompida(jogo)
                pygame.quit()
                return
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_p and not jogo.terminou:
                    pausado = not pausado
                elif e.key == pygame.K_r or (e.key == pygame.K_SPACE and jogo.terminou):
                    registro.interrompida(jogo)
                    jogo.reiniciar()
                    registro.inicio(jogo)
                    espera, pausado = ESPERA_SAQUE, False
                elif e.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()

        if not pausado and not jogo.terminou:
            if espera:
                espera -= 1
            else:
                vy_antes = jogo.bola_vy
                evento = jogo.step(esquerda.agir(jogo, ESQ), direita.agir(jogo, DIR))
                efeitos.registrar(jogo, evento, vy_antes)
                if evento.ponto:
                    registro.ponto(jogo)
                    if not evento.fim:
                        espera = ESPERA_SAQUE
        efeitos.avancar()

        aviso = None
        if jogo.terminou:
            vencedor = "VOCÊ VENCEU!" if jogo.vencedor == ESQ and nome_esq == "você" else f"{nomes[jogo.vencedor].upper()} VENCEU"
            aviso = f"{vencedor}\nespaço para jogar de novo"
        elif pausado:
            aviso = "PAUSA\nP para continuar"
        tela.desenhar(jogo, efeitos, nomes, detalhe, aviso)
        relogio.tick(FPS)
    pygame.quit()


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Jogue Pong contra a IA.")
    p.add_argument("--nivel", choices=list(NIVEIS), default="dificil")
    p.add_argument("--oponente", choices=list(BOTS), help="joga contra um bot em vez da IA")
    p.add_argument("--controle", choices=["teclado", "mouse"], default="teclado")
    p.add_argument("--assistir", action="store_true", help="bot segue (esquerda) contra o oponente")
    p.add_argument("--pontos", type=int, default=11, help="pontos para vencer a partida")
    rodar(p.parse_args(argv))


if __name__ == "__main__":
    main(sys.argv[1:])

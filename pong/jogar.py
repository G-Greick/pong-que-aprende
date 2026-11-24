"""Modo visual: jogue contra a IA.

    python -m pong.jogar                      abre o menu (modo, adversário, controle, pontos)

Ou direto, sem menu:
    python -m pong.jogar --nivel facil        níveis: sem-treino, facil, medio, dificil
    python -m pong.jogar --oponente segue     contra um bot escrito à mão
    python -m pong.jogar --controle mouse     raquete segue o mouse (com a mesma velocidade da IA)
    python -m pong.jogar --assistir           o bot "segue" contra a IA, sem humano
    python -m pong.jogar --aprender           a IA continua aprendendo enquanto joga

Teclas: P pausa, R recomeça, F11 tela cheia, ESC volta ao menu (ou sai).

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

from pong.agente import (
    NIVEIS, NOME_NIVEL, PASTA_MODELOS, AgenteAprendendo, AgenteQ, caminho_jogando, caminho_nivel,
)
from pong.bots import BOTS, BotSegue, criar_bot, mover_para
from pong.estilo import COR, FUNDO, LINHA, TEXTO, TEXTO_FRACO
from pong.jogo import DESCE, DIR, ESQ, PARADO, SOBE, Config, Pong
from pong.mao import MINIATURA, HumanoMao, RastreadorMao, falta_instalar
from pong.menu import NOME_BOT, Escolha, Menu
from pong.partidas import PASTA as PASTA_RESULTADOS
from pong.partidas import RegistroPartida

FPS = 60
ESPERA_SAQUE = 40  # quadros parados antes de cada saque


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


def _n(numero: int) -> str:
    return f"{numero:,}".replace(",", ".")


def detalhe_ia(ia) -> str:
    """Linha embaixo do nome da IA: quanto ela treinou e o tamanho do cérebro."""
    texto = f"{_n(ia.meta.get('pontos_treinados', 0))} pontos de treino"
    if isinstance(ia, AgenteAprendendo):
        texto += f" + {_n(ia.pontos_jogando)} jogando"
    kb = f"{ia.tamanho_bytes / 1024:.1f}".replace(".", ",")
    return f"{texto} · {kb} KB"


def criar_oponente(nome: str, aprender: bool = False):
    if nome in BOTS:
        return criar_bot(nome), f"bot {NOME_BOT[nome]}", "escrito à mão"
    if nome not in NIVEIS:
        raise SystemExit(f"oponente desconhecido: {nome} (níveis: {', '.join(NIVEIS)}; bots: {', '.join(BOTS)})")
    caminho = caminho_nivel(nome, PASTA_MODELOS)
    if not caminho.exists():
        raise SystemExit(f"modelo {caminho} não existe; treine antes com: python -m pong.treino")
    nome_ia = f"IA · {NOME_NIVEL[nome]}"
    if aprender:
        # continua de onde a IA parou nas partidas anteriores; na primeira vez, parte do nível
        jogando = caminho_jogando(nome, PASTA_MODELOS)
        ia = AgenteAprendendo(AgenteQ.carregar(jogando if jogando.exists() else caminho), jogando)
        return ia, f"{nome_ia} · aprendendo", detalhe_ia(ia)
    ia = AgenteQ.carregar(caminho)
    ia.meta.setdefault("pontos_treinados", NIVEIS[nome])
    return ia, nome_ia, detalhe_ia(ia)


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
        self.fonte_titulo = pygame.font.Font(None, 72)
        self.fonte = pygame.font.Font(None, 30)
        self.fonte_pequena = pygame.font.Font(None, 22)

    @property
    def fps(self) -> int:
        return FPS

    def texto(self, fonte, conteudo: str, cor, centro: tuple[float, float]) -> None:
        img = fonte.render(conteudo, True, cor)
        self.quadro.blit(img, img.get_rect(center=(int(centro[0]), int(centro[1]))))

    def mostrar(self, deslocamento: tuple[int, int] = (0, 0)) -> None:
        self.superficie.fill(FUNDO)
        self.superficie.blit(self.quadro, deslocamento)
        pygame.display.flip()

    def desenhar(
        self, jogo: Pong, efeitos: Efeitos, nomes: dict, detalhe: str, aviso: str | None, rodape: str,
        camera: tuple | None = None,
    ) -> None:
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

        self.texto(self.fonte_pequena, rodape, TEXTO_FRACO, (c.largura / 2, c.altura - 16))
        if camera:
            self._camera(*camera)
        if aviso:
            veu = pygame.Surface((c.largura, c.altura), pygame.SRCALPHA)
            veu.fill((0, 0, 0, 150))
            q.blit(veu, (0, 0))
            for i, linha in enumerate(aviso.split("\n")):
                fonte = self.fonte_placar if i == 0 else self.fonte
                self.texto(fonte, linha, TEXTO, (c.largura / 2, c.altura / 2 - 30 + i * 60))
        self.mostrar(efeitos.deslocamento())

    def _camera(self, miniatura, situacao: str | None) -> None:
        """Prévia da webcam no rodapé, no meio (onde as raquetes não passam)."""
        c = self.cfg
        caixa = pygame.Rect(0, 0, *MINIATURA)
        caixa.midbottom = (c.largura // 2, c.altura - 32)
        if miniatura is not None:
            imagem = pygame.image.frombuffer(miniatura.tobytes(), MINIATURA, "RGB")
            imagem.set_alpha(190)
            self.quadro.blit(imagem, caixa)
        pygame.draw.rect(self.quadro, LINHA, caixa, width=1)
        if situacao:
            self.texto(self.fonte_pequena, situacao, TEXTO, (caixa.centerx, caixa.top - 12))


# --- partida e laço principal ------------------------------------------------------


def montar_jogadores(escolha: Escolha):
    direita, nome_dir, detalhe = criar_oponente(escolha.oponente, escolha.aprender)
    if escolha.modo == "assistir":
        esquerda, nome_esq = BotSegue(), "bot segue"
    elif escolha.controle == "mao":
        esquerda, nome_esq = HumanoMao(RastreadorMao().iniciar()), "você"
    elif escolha.controle == "mouse":
        esquerda, nome_esq = HumanoMouse(), "você"
    else:
        esquerda, nome_esq = HumanoTeclado(), "você"
    return esquerda, direita, {ESQ: nome_esq, DIR: nome_dir}, detalhe


def jogar_partida(tela: Tela, escolha: Escolha, com_menu: bool, max_quadros: int | None = None) -> str:
    """Joga até o jogador sair. Devolve "menu" (ESC) ou "sair" (fechou a janela)."""
    esquerda, direita, nomes, detalhe = montar_jogadores(escolha)
    rastreador = getattr(esquerda, "rastreador", None)  # só existe no controle pela mão
    try:
        return _partida(tela, escolha, com_menu, max_quadros, esquerda, direita, nomes, detalhe, rastreador)
    finally:
        if rastreador:
            rastreador.parar()  # desliga a webcam


def _partida(tela, escolha, com_menu, max_quadros, esquerda, direita, nomes, detalhe, rastreador) -> str:
    jogo = Pong(Config(pontos_para_vencer=escolha.pontos))
    efeitos = Efeitos()
    relogio = pygame.time.Clock()
    espera, pausado, quadros = ESPERA_SAQUE, False, 0
    aprendendo = isinstance(direita, AgenteAprendendo)
    esc ="ESC menu" if com_menu else "ESC sai"
    controle = "W/S ou setas"
    if escolha.modo == "jogar" and escolha.controle != "teclado":
        controle = {"mouse": "mouse", "mao": "mão na webcam"}[escolha.controle]
    rodape = f"{controle} · P pausa · R recomeça · F11 tela cheia · {esc}"

    registro = RegistroPartida(nomes, PASTA_RESULTADOS)  # placar para o chat consultar
    registro.inicio(jogo)

    while max_quadros is None or quadros < max_quadros:
        quadros += 1
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                registro.interrompida(jogo)
                return "sair" if e.type == pygame.QUIT else "menu"
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

        sem_mao = rastreador is not None and rastreador.y is None
        if not pausado and not jogo.terminou and not (rastreador and rastreador.erro):
            if espera:
                if not (sem_mao and espera == 1):  # o saque espera a mão aparecer
                    espera -= 1
            else:
                vy_antes = jogo.bola_vy
                evento = jogo.step(esquerda.agir(jogo, ESQ), direita.agir(jogo, DIR))
                efeitos.registrar(jogo, evento, vy_antes)
                if aprendendo:
                    direita.observar(evento)  # a IA aprende com o que acabou de acontecer
                if evento.ponto:
                    registro.ponto(jogo)
                    if aprendendo:
                        detalhe = detalhe_ia(direita)
                    if not evento.fim:
                        espera = ESPERA_SAQUE
        efeitos.avancar()

        aviso = None
        if jogo.terminou:
            humano_venceu = jogo.vencedor == ESQ and nomes[ESQ] == "você"
            vencedor = "VOCÊ VENCEU!" if humano_venceu else f"{nomes[jogo.vencedor].upper()} VENCEU"
            aviso = f"{vencedor}\nespaço joga de novo · {esc}"
        elif rastreador and rastreador.erro:
            aviso = f"ERRO NA CÂMERA\n{rastreador.erro}\n{esc}"
        elif pausado:
            aviso = "PAUSA\nP para continuar"
        camera = None
        if rastreador:
            camera = (rastreador.miniatura(), rastreador.situacao if sem_mao else None)
        tela.desenhar(jogo, efeitos, nomes, detalhe, aviso, rodape, camera)
        relogio.tick(FPS)
    return "sair"


def rodar(escolha: Escolha, com_menu: bool, max_quadros: int | None = None) -> None:
    pygame.init()
    tela = Tela(Config())
    try:
        if not com_menu:
            jogar_partida(tela, escolha, com_menu=False, max_quadros=max_quadros)
            return
        while True:
            escolha = Menu(tela, escolha, PASTA_MODELOS, PASTA_RESULTADOS).rodar(max_quadros)
            if escolha is None or jogar_partida(tela, escolha, True, max_quadros) == "sair":
                return
    finally:
        pygame.quit()


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Jogue Pong contra a IA. Sem opções, abre o menu.")
    p.add_argument("--nivel", choices=list(NIVEIS), help="nível da IA (padrão: dificil)")
    p.add_argument("--oponente", choices=list(BOTS), help="joga contra um bot em vez da IA")
    p.add_argument("--controle", choices=["teclado", "mouse", "mao"], default="teclado",
                   help="mao = webcam (precisa de requirements-mao.txt)")
    p.add_argument("--assistir", action="store_true", help="bot segue (esquerda) contra o oponente")
    p.add_argument("--pontos", type=int, default=11, help="pontos para vencer a partida")
    p.add_argument("--aprender", action="store_true",
                   help="a IA continua aprendendo durante a partida (salva em modelos/jogando/)")
    argv = sys.argv[1:] if argv is None else argv
    a = p.parse_args(argv)
    if a.controle == "mao" and falta_instalar():
        raise SystemExit(f"Controle pela mão: {falta_instalar()}")
    escolha = Escolha(
        modo="assistir" if a.assistir else "jogar",
        oponente=a.oponente or a.nivel or "dificil",
        controle=a.controle,
        pontos=a.pontos,
        aprender=a.aprender,
    )
    if a.aprender and escolha.oponente not in NIVEIS:
        raise SystemExit("--aprender só vale contra a IA (bots escritos à mão não aprendem)")
    rodar(escolha, com_menu=not argv)


if __name__ == "__main__":
    main()


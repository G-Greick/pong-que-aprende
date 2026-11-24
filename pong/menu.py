"""Menu inicial do modo visual: modo, adversário (dificuldade), controle e pontos.

Teclado: setas para cima/baixo escolhem a linha, esquerda/direita mudam o valor,
Enter joga. Mouse: clique na metade esquerda/direita do valor para mudar, ou em JOGAR.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pygame

from pong.agente import NIVEIS, NOME_NIVEL, caminho_jogando, caminho_nivel
from pong.arquivos import ler_csv
from pong.bots import BotPreditor, BotSegue
from pong.estilo import COR, DESTAQUE, FUNDO, LINHA, TEXTO, TEXTO_FRACO
from pong.jogo import DIR, ESQ, Config, Pong
from pong.mao import falta_instalar

NOME_BOT = {"segue": "segue", "preditor": "preditor", "aleatorio": "aleatório"}
OPONENTES = {**{n: f"IA · {NOME_NIVEL[n]}" for n in NIVEIS}, **{b: f"bot {NOME_BOT[b]}" for b in NOME_BOT}}
MODOS = {"jogar": "jogar", "assistir": "assistir"}
CONTROLES = {"teclado": "teclado", "mouse": "mouse", "mao": "mão (webcam)"}
PONTOS = (3, 5, 11, 21)
SIM_NAO = {False: "não", True: "sim"}

DESCRICAO = {
    "jogar": "você na raquete azul, contra o adversário escolhido",
    "assistir": "o bot segue (azul) contra o adversário escolhido, sem humano",
    "teclado": "W/S ou setas para subir e descer",
    "mouse": "a raquete vai atrás do mouse, na mesma velocidade da IA",
    "mao": "a raquete segue a altura da sua mão na webcam, na mesma velocidade da IA",
    "segue": "bot escrito à mão: vai atrás da bola (é com ele que a IA treinou)",
    "preditor": "bot escrito à mão: calcula onde a bola vai chegar e devolve com ângulo",
    "aleatorio": "bot escrito à mão: aperta botões ao acaso",
}


@dataclass
class Escolha:
    modo: str = "jogar"
    oponente: str = "dificil"  # um nível da IA ou o nome de um bot
    controle: str = "teclado"
    pontos: int = 11
    aprender: bool = False  # a IA continua aprendendo durante a partida


@dataclass
class Linha:
    chave: str  # atributo da Escolha que esta linha muda
    rotulo: str
    nomes: dict = field(default_factory=dict)

    @property
    def opcoes(self) -> list:
        return list(self.nomes)


def linhas_do_menu(escolha: Escolha) -> list[Linha]:
    linhas = [Linha("modo", "Modo", MODOS), Linha("oponente", "Adversário", OPONENTES)]
    if escolha.modo == "jogar":
        linhas.append(Linha("controle", "Controle", CONTROLES))
    linhas.append(Linha("pontos", "Pontos para vencer", {p: str(p) for p in PONTOS}))
    if escolha.oponente in NIVEIS:  # bots escritos à mão não aprendem
        linhas.append(Linha("aprender", "Treinar jogando", SIM_NAO))
    return linhas


def mudar(escolha: Escolha, linha: Linha, passo: int) -> None:
    atual = getattr(escolha, linha.chave)
    i = linha.opcoes.index(atual) if atual in linha.opcoes else 0
    setattr(escolha, linha.chave, linha.opcoes[(i + passo) % len(linha.opcoes)])


def falta_modelo(escolha: Escolha, pasta_modelos: Path) -> bool:
    return escolha.oponente in NIVEIS and not caminho_nivel(escolha.oponente, pasta_modelos).exists()


def descrever(escolha: Escolha, chave: str | None, avaliacao: dict, pasta_modelos: Path) -> str:
    if chave is None:  # linha JOGAR
        chave = "oponente"
    if chave == "oponente" and escolha.oponente in NIVEIS:
        if falta_modelo(escolha, pasta_modelos):
            return "modelo não encontrado: treine antes com  python -m pong.treino"
        treino = f"{NIVEIS[escolha.oponente]:,}".replace(",", ".")
        texto = f"IA com {treino} pontos de treino"
        aval = avaliacao.get(escolha.oponente)
        if aval:
            pct = f"{float(aval['pct_pontos']):.0f}"
            texto += f" · ganha {pct}% dos pontos contra o bot segue"
        return texto
    if chave == "oponente":
        return DESCRICAO[escolha.oponente]
    if chave == "pontos":
        return f"a partida acaba quando alguém fizer {escolha.pontos} pontos"
    if chave == "aprender":
        if not escolha.aprender:
            return "a IA joga só com o que já sabe"
        jogando = caminho_jogando(escolha.oponente, pasta_modelos)
        if jogando.exists():
            return "a IA continua de onde parou e aprende a cada ponto (salvo em modelos/jogando)"
        return "a IA parte deste nível e aprende a cada ponto (o nível original não muda)"
    if chave == "controle" and escolha.controle == "mao" and falta_instalar():
        return falta_instalar()
    return DESCRICAO[getattr(escolha, chave)]


class Menu:
    def __init__(self, tela, escolha: Escolha, pasta_modelos: Path, pasta_resultados: Path):
        self.tela = tela
        self.escolha = escolha
        self.pasta_modelos = pasta_modelos
        self.selecionada = len(linhas_do_menu(escolha))  # começa no JOGAR
        self.avaliacao = {
            l["nivel"]: l for l in ler_csv(pasta_resultados / "avaliacao.csv") if l["bot"] == "segue"
        }
        self.aviso = ""
        # dois bots jogando no fundo, só de enfeite
        self.demo = Pong(Config(pontos_para_vencer=10**9), seed=1)
        self.demo_esq, self.demo_dir = BotSegue(), BotPreditor(seed=2)
        self.alvos: list[pygame.Rect] = []
        self.botao = pygame.Rect(0, 0, 0, 0)

    def rodar(self, max_quadros: int | None = None) -> Escolha | None:
        """Devolve a escolha quando o jogador manda jogar, ou None se fechar."""
        relogio, quadros = pygame.time.Clock(), 0
        while max_quadros is None or quadros < max_quadros:
            quadros += 1
            for e in pygame.event.get():
                resultado = self._tratar(e)
                if resultado is not False:
                    return resultado
            self.demo.step(self.demo_esq.agir(self.demo, ESQ), self.demo_dir.agir(self.demo, DIR))
            self._desenhar()
            relogio.tick(self.tela.fps)
        return None

    def _tratar(self, e) -> Escolha | None | bool:
        """False = continua no menu; None = fechar; Escolha = jogar."""
        linhas = linhas_do_menu(self.escolha)
        if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
            return None
        if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self.aviso = ""
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_UP, pygame.K_w):
                self.selecionada = (self.selecionada - 1) % (len(linhas) + 1)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.selecionada = (self.selecionada + 1) % (len(linhas) + 1)
            elif e.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d) and self.selecionada < len(linhas):
                passo = -1 if e.key in (pygame.K_LEFT, pygame.K_a) else 1
                mudar(self.escolha, linhas[self.selecionada], passo)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self._jogar()
            elif e.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
        elif e.type == pygame.MOUSEMOTION:
            for i, alvo in enumerate(self.alvos + [self.botao]):
                if alvo.collidepoint(e.pos):
                    self.selecionada = i
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.botao.collidepoint(e.pos):
                return self._jogar()
            for i, alvo in enumerate(self.alvos):
                if alvo.collidepoint(e.pos) and i < len(linhas):
                    mudar(self.escolha, linhas[i], -1 if e.pos[0] < alvo.centerx + 130 else 1)
        self.selecionada = min(self.selecionada, len(linhas_do_menu(self.escolha)))
        return False

    def _jogar(self) -> Escolha | bool:
        if falta_modelo(self.escolha, self.pasta_modelos):
            self.aviso = "esse nível ainda não foi treinado"
            return False
        if self.escolha.modo == "jogar" and self.escolha.controle == "mao" and falta_instalar():
            self.aviso = f"controle pela mão: {falta_instalar()}"
            return False
        return self.escolha

    def _desenhar(self) -> None:
        t, q, c = self.tela, self.tela.quadro, self.tela.cfg
        q.fill(FUNDO)

        # o jogo de demonstração, apagado
        for y in range(0, c.altura, 30):
            pygame.draw.rect(q, LINHA, (c.largura // 2 - 2, y + 8, 4, 14))
        for lado in (ESQ, DIR):
            x = self.demo.x_face(lado) - (c.raquete_largura if lado == ESQ else 0)
            cor = tuple(int(f * 0.55 + v * 0.45) for f, v in zip(FUNDO, COR[lado]))
            pygame.draw.rect(q, cor, (x, self.demo.raquete[lado] - c.raquete_altura / 2,
                                      c.raquete_largura, c.raquete_altura), border_radius=3)
        b = c.bola_tam
        pygame.draw.rect(q, LINHA, (self.demo.bola_x - b / 2, self.demo.bola_y - b / 2, b, b))
        veu = pygame.Surface((c.largura, c.altura), pygame.SRCALPHA)
        veu.fill((*FUNDO, 200))
        q.blit(veu, (0, 0))

        t.texto(t.fonte_titulo, "PONG QUE APRENDE", TEXTO, (c.largura / 2, 92))
        t.texto(t.fonte_pequena, "Arcade Pixel Estúdio", TEXTO_FRACO, (c.largura / 2, 140))

        linhas = linhas_do_menu(self.escolha)
        self.alvos = []
        y = 205
        for i, linha in enumerate(linhas):
            alvo = pygame.Rect(130, y - 22, c.largura - 260, 44)
            self.alvos.append(alvo)
            ativa = i == self.selecionada
            if ativa:
                pygame.draw.rect(q, (28, 32, 60), alvo, border_radius=8)
            rotulo = t.fonte.render(linha.rotulo, True, TEXTO if ativa else TEXTO_FRACO)
            q.blit(rotulo, rotulo.get_rect(midright=(alvo.centerx - 20, y)))
            valor = linha.nomes[getattr(self.escolha, linha.chave)]
            cor = DESTAQUE if ativa else TEXTO
            t.texto(t.fonte, valor, cor, (alvo.centerx + 130, y))
            if ativa:
                t.texto(t.fonte, "<", cor, (alvo.centerx + 20, y))
                t.texto(t.fonte, ">", cor, (alvo.right - 20, y))
            y += 52

        self.botao = pygame.Rect(0, 0, 220, 52)
        self.botao.center = (c.largura // 2, y + 28)
        no_botao = self.selecionada == len(linhas)
        pygame.draw.rect(q, DESTAQUE, self.botao, width=0 if no_botao else 2, border_radius=10)
        t.texto(t.fonte, "JOGAR", FUNDO if no_botao else DESTAQUE, self.botao.center)

        chave = linhas[self.selecionada].chave if self.selecionada < len(linhas) else None
        descricao = self.aviso or descrever(self.escolha, chave, self.avaliacao, self.pasta_modelos)
        t.texto(t.fonte_pequena, descricao, TEXTO_FRACO, (c.largura / 2, self.botao.bottom + 36))
        t.texto(t.fonte_pequena, "setas escolhem e mudam · Enter joga · F11 tela cheia · ESC sai",
                TEXTO_FRACO, (c.largura / 2, c.altura - 16))
        t.mostrar()

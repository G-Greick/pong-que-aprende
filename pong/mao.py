"""Controle da raquete pela mão, com a webcam (extra opcional).

    pip install -r requirements-mao.txt      (opencv-python e mediapipe)
    python -m pong.jogar --controle mao

Na primeira vez baixa o modelo de detecção de mão do MediaPipe (7,8 MB) para modelos/.

A câmera roda numa thread separada, então o jogo não espera a detecção (~20 ms por
quadro). A altura da mão vira um ALVO: a raquete vai até ele com as mesmas três
ações e a mesma velocidade da IA, como no controle por mouse. Sem teletransporte.
"""

from __future__ import annotations

import importlib.util
import os
import threading
import time
import urllib.request
from pathlib import Path

import numpy as np

from pong.bots import mover_para
from pong.jogo import PARADO, Pong

URL_MODELO = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)
CAMINHO_MODELO = Path("modelos/hand_landmarker.task")
CENTRO_DA_MAO = 9  # ponto 9 do MediaPipe: base do dedo médio, mais estável que as pontas
FAIXA_UTIL = (0.2, 0.8)  # a mão entre 20% e 80% da altura da imagem cobre a quadra toda
MINIATURA = (160, 120)


def falta_instalar() -> str | None:
    """Mensagem dizendo o que falta, ou None se dá para usar a mão."""
    faltando = [m for m in ("cv2", "mediapipe") if importlib.util.find_spec(m) is None]
    if faltando:
        return "instale antes: pip install -r requirements-mao.txt"
    return None


def baixar_modelo(caminho: Path = CAMINHO_MODELO, url: str = URL_MODELO) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(".baixando")
    with urllib.request.urlopen(url, timeout=60) as r:
        tmp.write_bytes(r.read())
    tmp.replace(caminho)


def altura_na_quadra(y_imagem: float, altura_quadra: float) -> float:
    """Converte a altura da mão na imagem (0 = topo, 1 = base) em altura na quadra."""
    baixo, alto = FAIXA_UTIL
    fracao = min(max((y_imagem - baixo) / (alto - baixo), 0.0), 1.0)
    return fracao * altura_quadra


class RastreadorMao:
    """Lê a webcam numa thread e guarda a última altura da mão encontrada."""

    def __init__(self, camera: int = 0, caminho_modelo: Path = CAMINHO_MODELO):
        self.camera = camera
        self.caminho_modelo = caminho_modelo
        self.y: float | None = None  # 0 = topo da imagem, 1 = base; None = sem mão
        self.situacao = "abrindo a câmera..."
        self.erro: str | None = None
        self.pronto = False
        self._miniatura: np.ndarray | None = None
        self._trava = threading.Lock()
        self._parar = threading.Event()
        self._thread = threading.Thread(target=self._rodar, daemon=True)

    def iniciar(self) -> RastreadorMao:
        self._thread.start()
        return self

    def parar(self) -> None:
        self._parar.set()
        self._thread.join(timeout=2)

    def miniatura(self) -> np.ndarray | None:
        with self._trava:
            return self._miniatura

    def _rodar(self) -> None:
        try:
            import cv2
            import mediapipe as mp

            if not self.caminho_modelo.exists():
                self.situacao = "baixando o modelo da mão (7,8 MB)..."
                baixar_modelo(self.caminho_modelo)

            visao = mp.tasks.vision
            opcoes = visao.HandLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(self.caminho_modelo)),
                running_mode=visao.RunningMode.VIDEO,
                num_hands=1,
            )
            api = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY  # no Windows abre bem mais rápido
            camera = cv2.VideoCapture(self.camera, api)
            if not camera.isOpened():
                self.erro = "webcam não encontrada"
                return
            try:
                with visao.HandLandmarker.create_from_options(opcoes) as detector:
                    self._detectar(camera, detector, cv2, mp)
            finally:
                camera.release()
        except Exception as erro:  # qualquer falha vira mensagem na tela, sem derrubar o jogo
            self.erro = f"{erro.__class__.__name__}: {erro}"[:70]

    def _detectar(self, camera, detector, cv2, mp) -> None:
        self.situacao = "mostre a mão para a câmera"
        self.pronto = True
        inicio, ultimo_ms = time.monotonic(), -1
        while not self._parar.is_set():
            ok, quadro = camera.read()
            if not ok:
                self.erro = "a webcam parou de enviar imagens"
                return
            quadro = cv2.flip(quadro, 1)  # espelho: a imagem se mexe para o mesmo lado da mão
            rgb = cv2.cvtColor(quadro, cv2.COLOR_BGR2RGB)
            # o detector exige instantes sempre crescentes, em milissegundos
            ms = max(int((time.monotonic() - inicio) * 1000), ultimo_ms + 1)
            ultimo_ms = ms
            resultado = detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ms)

            mini = cv2.resize(rgb, MINIATURA)
            if resultado.hand_landmarks:
                ponto = resultado.hand_landmarks[0][CENTRO_DA_MAO]
                self.y = ponto.y
                centro = (int(ponto.x * MINIATURA[0]), int(ponto.y * MINIATURA[1]))
                cv2.circle(mini, centro, 6, (79, 209, 255), -1)
            else:
                self.y = None
            for fracao in FAIXA_UTIL:  # mostra a faixa útil na miniatura
                y = int(fracao * MINIATURA[1])
                cv2.line(mini, (0, y), (MINIATURA[0], y), (130, 134, 170), 1)
            with self._trava:
                self._miniatura = mini


class HumanoMao:
    """Jogador controlado pela altura da mão na webcam."""

    def __init__(self, rastreador: RastreadorMao, suavizacao: float = 0.5):
        self.rastreador = rastreador
        self.suavizacao = suavizacao  # amortece a tremedeira natural da detecção
        self._alvo: float | None = None

    def agir(self, jogo: Pong, lado: str) -> int:
        y = self.rastreador.y
        if y is None:  # mão sumiu: a raquete para
            self._alvo = None
            return PARADO
        alvo = altura_na_quadra(y, jogo.cfg.altura)
        if self._alvo is not None:
            alvo = self.suavizacao * self._alvo + (1 - self.suavizacao) * alvo
        self._alvo = alvo
        return mover_para(jogo.raquete[lado], alvo, jogo.cfg.raquete_vel / 2)

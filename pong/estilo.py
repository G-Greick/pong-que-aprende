"""Cores do modo visual (usadas pelo jogo e pelo menu)."""

from pong.jogo import DIR, ESQ

FUNDO = (14, 16, 32)
LINHA = (60, 64, 100)
TEXTO = (235, 235, 245)
TEXTO_FRACO = (130, 134, 170)
COR = {ESQ: (79, 209, 255), DIR: (255, 79, 139)}
DESTAQUE = COR[ESQ]

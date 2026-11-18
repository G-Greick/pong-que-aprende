# Pong que aprende

Projeto 02 — Arcade Pixel Estúdio (fictício). Um Pong jogável em que o adversário
aprende a jogar sozinho, por aprendizado por reforço.

## Instalar e rodar

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pytest
```

## Organização

```
pong/
  jogo.py        regras e física do jogo, sem desenho (usado pelo treino e pelo modo visual)
tests/
  test_jogo.py   testes das regras: quique, ponto, placar, rebatida, fim de partida
```

## Situação

- [x] Simulação do jogo, sem tela, com testes (~600 mil passos por segundo)
- [ ] Adversário simples (bot) para a IA treinar
- [ ] IA com Q-learning + treino rápido
- [ ] Gráfico de evolução e avaliação em muitas partidas
- [ ] Níveis de dificuldade a partir de checkpoints do treino
- [ ] Modo visual com pygame (teclado)
- [ ] Chat para o produtor consultar o treino
- [ ] Extra: controle da raquete pela mão (webcam)

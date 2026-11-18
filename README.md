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
  bots.py        adversários escritos à mão: aleatorio, segue (treino) e preditor
  agente.py      a IA: o que ela enxerga, a recompensa e a tabela Q
  treino.py      treino rápido sem tela; salva modelos/, resultados/treino.csv e status.json
  avaliacao.py   mede uma IA ou bot jogando muitos pontos contra outro
tests/           testes das regras, dos bots, do agente e do treino
```

Treinar a IA:

```powershell
python -m pong.treino --pontos 30000
```

## Situação

- [x] Simulação do jogo, sem tela, com testes (~600 mil passos por segundo)
- [x] Adversário simples (bot) para a IA treinar
- [x] IA com Q-learning + treino rápido
- [ ] Gráfico de evolução e avaliação em muitas partidas
- [ ] Níveis de dificuldade a partir de checkpoints do treino
- [ ] Modo visual com pygame (teclado)
- [ ] Chat para o produtor consultar o treino
- [ ] Extra: controle da raquete pela mão (webcam)

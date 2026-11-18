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
  jogar.py       modo visual (pygame): humano contra IA ou bot
  relatorio.py   avalia os níveis contra os bots e desenha os gráficos
modelos/         a IA treinada em 4 momentos do treino = os níveis de dificuldade
resultados/      evolução do treino, avaliação, gráficos e relatorio.md
tests/           testes das regras, dos bots, do agente e do treino
```

Jogar contra a IA (W/S ou setas; P pausa, R recomeça, F11 tela cheia, ESC sai):

```powershell
python -m pong.jogar                    # IA difícil
python -m pong.jogar --nivel facil      # sem-treino, facil, medio, dificil
python -m pong.jogar --controle mouse   # raquete segue o mouse
python -m pong.jogar --assistir         # bot "segue" contra a IA, sem humano
```

Treinar a IA de novo (uns 5 minutos; gera os níveis em `modelos/`):

```powershell
python -m pong.treino --pontos 30000 --bloco 1000 --checkpoints 0 2000 10000 30000
python -m pong.relatorio    # avalia os níveis (~2 min) e gera resultados/relatorio.md
```

Resultados: [resultados/relatorio.md](resultados/relatorio.md)

## Situação

- [x] Simulação do jogo, sem tela, com testes (~600 mil passos por segundo)
- [x] Adversário simples (bot) para a IA treinar
- [x] IA com Q-learning + treino rápido
- [x] Gráfico de evolução e avaliação em muitas partidas
- [x] Níveis de dificuldade a partir de checkpoints do treino
- [x] Modo visual com pygame (teclado e mouse)
- [ ] Chat para o produtor consultar o treino
- [ ] Extra: controle da raquete pela mão (webcam)

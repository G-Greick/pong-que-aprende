# Pong que aprende

Projeto 02 — Arcade Pixel Estúdio (fictício). Um Pong jogável em que o adversário
aprende a jogar sozinho, por aprendizado por reforço (Q-learning), e de cujo
treino saem os níveis de dificuldade.

## Instalar e jogar (Windows, PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m pong.jogar
```

A IA já vem treinada em `modelos/`. Você é a raquete azul (esquerda): **W/S** ou **setas**.
P pausa, R recomeça, F11 tela cheia, ESC sai.

```powershell
python -m pong.jogar --nivel facil      # sem-treino, facil, medio, dificil (padrão)
python -m pong.jogar --controle mouse   # raquete vai atrás do mouse, na mesma velocidade da IA
python -m pong.jogar --assistir         # bot "segue" contra a IA, sem humano
```

## Treino e evidências

```powershell
python -m pong.treino --pontos 30000 --bloco 1000 --checkpoints 0 2000 10000 30000   # ~5 min
python -m pong.relatorio    # avalia os níveis contra os bots (~2 min) e gera os gráficos
pytest                      # testes automatizados
```

Resultados: [resultados/relatorio.md](resultados/relatorio.md)

## Chat do produtor (Telegram)

1. No Telegram, fale com o **@BotFather**, mande `/newbot` e copie o token.
2. Guarde o token só na variável de ambiente (nunca no código) e suba o bot:

```powershell
$env:TELEGRAM_BOT_TOKEN = "cole-o-token-aqui"
python -m pong.telegram_bot
```

Pergunte ao bot: *como foi o treino?*, *a IA aprendeu?*, *qual o placar?*, *quais são os níveis?*,
*quanto cérebro ela tem?*, *joga bem contra outro adversário?* ou mande `/grafico`.
O placar é o da partida que estiver sendo jogada no `pong.jogar`, atualizado a cada ponto.

Para restringir quem conversa com o bot: `$env:TELEGRAM_CHATS_PERMITIDOS = "123456789"`
(o id de cada chat aparece no terminal do bot). Sem Telegram, o mesmo assistente roda no
terminal: `python -m pong.chat`.

## Organização

```
pong/
  jogo.py          regras e física do jogo, sem desenho (usado pelo treino e pelo modo visual)
  bots.py          adversários escritos à mão: aleatorio, segue (treino) e preditor
  agente.py        a IA: o que ela enxerga, a recompensa, a tabela Q e os níveis
  treino.py        treino rápido sem tela; salva modelos/, resultados/treino.csv e status.json
  avaliacao.py     mede uma IA ou bot jogando muitos pontos contra outro
  relatorio.py     avalia os níveis contra os bots e desenha os gráficos
  jogar.py         modo visual (pygame): humano contra IA ou bot
  partidas.py      grava o placar das partidas para o chat
  chat.py          assistente que responde ao produtor (também roda no terminal)
  telegram_bot.py  liga o assistente ao Telegram
modelos/           a IA salva em 4 momentos do treino = os níveis de dificuldade
resultados/        evolução do treino, avaliação, gráficos e relatorio.md
tests/             testes de cada parte
```

## Situação

- [x] Simulação do jogo, sem tela, com testes (~600 mil passos por segundo)
- [x] Adversários escritos à mão (bots) para treinar e avaliar a IA
- [x] IA com Q-learning + treino rápido (~5 min)
- [x] Gráfico de evolução e avaliação em milhares de pontos
- [x] Níveis de dificuldade a partir de checkpoints do treino
- [x] Modo visual com pygame (teclado e mouse)
- [x] Chat do produtor pelo Telegram (e pelo terminal)
- [ ] `decisoes.md` e `relato-ia.md`
- [ ] Extra: controle da raquete pela mão (webcam)

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

Testado do zero (clone + venv novo) no Windows 11 com Python 3.10 e 3.13. A IA já vem treinada em `modelos/`. O jogo abre num menu para escolher o **modo** (jogar ou
assistir), o **adversário** (IA sem treino, fácil, médio, difícil ou um dos bots), o **controle**
(teclado ou mouse), os **pontos** da partida e, contra a IA, se ela deve **treinar jogando**. Você é a raquete azul (esquerda): **W/S** ou **setas**.
P pausa, R recomeça, F11 tela cheia, ESC volta ao menu.

**Controle pela mão (extra opcional):** a raquete segue a altura da sua mão na webcam.

```powershell
pip install -r requirements-mao.txt     # OpenCV + MediaPipe
python -m pong.jogar --controle mao     # ou escolha "mão (webcam)" no menu
```

Na primeira vez o jogo baixa o modelo de detecção de mão (7,8 MB) para `modelos/`, então
precisa de internet. Mão aberta de frente para a câmera; a faixa do meio da imagem (marcada
na prévia) cobre a quadra toda. A bola só sai quando a mão aparece.

**Treinar jogando:** com essa opção ligada, a IA continua aprendendo durante a partida, com o
mesmo Q-learning do treino rápido: a cada decisão ela atualiza a tabela com a recompensa que
recebeu (+1 ao rebater, +1 ao marcar, −1 ao sofrer). O que ela aprende é salvo a cada ponto em
`modelos/jogando/` e a próxima partida continua de onde parou; os níveis originais não mudam.
Embaixo do nome dela aparece quantos pontos ela já jogou aprendendo. Para recomeçar do zero,
apague `modelos/jogando/`. A mudança é lenta: o nível fácil precisou de 2.000 pontos de treino,
e uma partida tem de 11 a 21.

Para pular o menu:

```powershell
python -m pong.jogar --nivel facil      # sem-treino, facil, medio, dificil (padrão)
python -m pong.jogar --oponente segue   # contra um bot: segue, preditor, aleatorio
python -m pong.jogar --controle mouse   # raquete vai atrás do mouse, na mesma velocidade da IA
python -m pong.jogar --controle mao     # raquete segue a mão na webcam
python -m pong.jogar --assistir         # bot "segue" contra a IA, sem humano
python -m pong.jogar --aprender         # a IA continua aprendendo enquanto joga
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
  menu.py          menu inicial: modo, adversário, controle e pontos
  mao.py           controle pela mão: webcam + MediaPipe numa thread separada
  estilo.py        cores do modo visual
  partidas.py      grava o placar das partidas para o chat
  chat.py          assistente que responde ao produtor (também roda no terminal)
  telegram_bot.py  liga o assistente ao Telegram
modelos/           a IA salva em 4 momentos do treino = os níveis de dificuldade
  jogando/         a IA que continua aprendendo nas partidas (criada pelo jogo, fora do git)
resultados/        evolução do treino, avaliação, gráficos e relatorio.md
tests/             testes de cada parte
```

## Situação

- [x] Simulação do jogo, sem tela, com testes (~600 mil passos por segundo)
- [x] Adversários escritos à mão (bots) para treinar e avaliar a IA
- [x] IA com Q-learning + treino rápido (~5 min)
- [x] Gráfico de evolução e avaliação em milhares de pontos
- [x] Níveis de dificuldade a partir de checkpoints do treino
- [x] Modo visual com pygame (teclado e mouse) e menu inicial
- [x] IA que continua aprendendo durante a partida (opção "Treinar jogando")
- [x] Chat do produtor pelo Telegram (e pelo terminal)
- [x] [`decisoes.md`](decisoes.md) e [`relato-ia.md`](relato-ia.md)
- [x] Extra: controle da raquete pela mão (webcam)

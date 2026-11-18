# Decisões do projeto — Pong que aprende

## 1. Como entendi o problema

O Arcade Pixel quer um adversário que **ninguém programou**: em vez de um script do tipo
"siga a bola", um jogador que descobre sozinho o que funciona, jogando. O pedido tem
quatro partes que precisam se encaixar:

1. **Jogo correto e jogável:** a bola quica, o ponto vai para o jogador certo e o placar bate.
2. **IA que aprende:** joga mal no começo e bem depois do treino, que precisa durar minutos.
3. **Prova com números:** níveis de dificuldade que vêm do próprio treino e medições em muitas partidas.
4. **Acompanhamento:** o produtor consulta o treino e o placar por chat.

Por isso a peça central do projeto é **uma única simulação** (`pong/jogo.py`), sem desenho,
usada ao mesmo tempo pelo treino rápido, pelo modo visual e pelos testes. O jogo em que a IA
treina é exatamente o jogo em que o humano joga.

**O que decidi não resolver:**
- **Atacar de propósito:** a IA não enxerga onde o adversário está, então não aprende a mirar longe dele.
- **Treinar contra si mesma (self-play):** treinei só contra um bot escrito à mão.
- **Rede neural:** não usei.
- **Partida online e dificuldade que se ajusta durante o jogo:** ficaram de fora.
- **Controle pela mão (webcam):** era um extra opcional e não entrou nesta entrega.

## 2. Caminhos que considerei e o que escolhi

| Decisão | Opções | Escolha e motivo |
|---|---|---|
| Plataforma | Unity (ML-Agents) ou Python | **Python + pygame.** Treinar sem tela é trivial, os testes, o chat e o gráfico saem com bibliotecas comuns, e a instalação cabe em 4 comandos. No Unity, o ML-Agents exigiria versões casadas de editor, Python e PyTorch, e o algoritmo (PPO) seria uma caixa-preta difícil de explicar. |
| Algoritmo | Q-learning em tabela, rede neural (DQN) ou evolução de parâmetros | **Q-learning em tabela.** Treina em minutos num computador comum, o "cérebro" tem tamanho exato e cada número dele tem significado. Custo: preciso decidir à mão como resumir o jogo em estados. |
| O que a IA enxerga | Posições absolutas ou relativas à própria raquete | **Relativas**, em 4 informações: altura da bola menos a da raquete (11 faixas), distância da bola (4), velocidade vertical (5) e se a bola vem ou vai (2). São **440 estados**. Como tudo é relativo, a mesma tabela joga dos dois lados. |
| Como decide | A cada passo do jogo (60 por segundo) ou a cada 4 passos | **A cada 4 passos** (cerca de 15 decisões por segundo, ritmo humano). Cada decisão pesa mais e o aprendizado fica mais rápido. As ações são as mesmas do humano: subir, descer ou ficar parado. |
| Recompensa | Só −1 ao sofrer ponto, ou recompensas intermediárias | **+1 ao rebater, +1 ao marcar, −1 ao sofrer.** Recompensar a rebatida acelera o aprendizado sem dizer *como* rebater. Comparei com e sem o +1 por marcar: deu 44% contra 39% dos pontos contra o bot de treino. A diferença é pequena, mas marcar é o objetivo real. |
| Adversário de treino | Bot aleatório, bot que segue a bola ou a própria IA | **Bot "segue"**, o script clássico. O aleatório é fraco demais para ensinar, e a própria IA ficou para depois. Para medir a generalização criei o **"preditor"**, de estilo diferente: calcula onde a bola vai chegar e devolve com ângulo. |
| Exploração | ε fixo ou decrescente | **ε cai em linha reta de 1 para 0,05** na primeira metade do treino. No começo a IA joga ao acaso e depois passa a usar o que aprendeu. |
| Níveis | Limitar a velocidade da IA ou salvar o treino em momentos diferentes | **Checkpoints** com 0, 2.000, 10.000 e 30.000 pontos de treino: sem treino, fácil, médio e difícil. A dificuldade vem só do quanto ela treinou. |
| Física | Física pronta ou própria | **Própria e determinística** (mesma semente, mesma partida). A colisão olha a trajetória da bola no passo, e não só a posição final, para a bola rápida não atravessar a raquete. |
| Controle humano | Mouse "teletransporta" a raquete ou segue as mesmas regras | **Mesmas regras da IA:** com o mouse, a raquete vai atrás do cursor com as mesmas três ações e a mesma velocidade, então ninguém tem vantagem. |
| Chat | Modelo de linguagem ou palavras-chave | **Palavras-chave** sobre os arquivos de resultado: roda offline, não tem custo e nunca inventa número. O bot do Telegram usa a API HTTP direto, com o token só em variável de ambiente. O mesmo assistente roda no terminal (`python -m pong.chat`) se o Telegram não estiver disponível. |

## 3. Como medi se funciona

**Avaliação final** (`python -m pong.relatorio`): cada nível joga 1.000 pontos sem exploração
contra cada bot, sempre com os mesmos saques. Meço o **% de pontos ganhos** e as **rebatidas por
ponto**, que mostram a defesa. Se um ponto passa de 3.000 passos sem ninguém errar, ele conta
à parte como "travado".

| Nível | vs aleatório | vs segue (treino) | vs preditor (nunca visto) |
|---|---|---|---|
| sem treino | 48,8% · 0,1 rebatidas | 0,0% · 0,2 | 0,0% · 0,2 |
| fácil (2.000) | 94,6% · 0,2 | 13,0% · 6,6 | 0,0% · 3,3 |
| médio (10.000) | 99,8% · 0,2 | 23,4% · 9,7 | 0,0% · 8,4 |
| difícil (30.000) | 100,0% · 0,2 | **50,9%** · 23,9 | 0,1% · 11,5 |

- **Ela aprendeu:** sem treino, joga como o aleatório. O nível difícil empata com o script
  de treino e nunca perde para o aleatório.
- **Os níveis são diferentes de verdade:** os números sobem a cada nível nos três adversários.
- **Contra um adversário diferente:** o preditor quase nunca erra, e nem o próprio bot "segue"
  marca ponto nele. A IA também não marca, mas a defesa dela contra esse estilo novo sobe de
  0,2 para 11,5 rebatidas por ponto. Ela aprendeu a defender de forma geral, não a vencer quem não erra.
- **Curva de aprendizado:** a cada 1.000 pontos de treino a IA é medida em 200 pontos. A curva
  está em `resultados/aprendizado.png`.
- **Tamanho do cérebro:** 440 estados × 3 ações = 1.320 números float32, ou seja, **5.280 bytes**.
- **Custo:** o treino completo leva **5,4 minutos**, e a simulação roda cerca de 600 mil passos por segundo.

**Testes automatizados** (`pytest`, 84 testes):
- **Regras do jogo:** quique, ponto pro lado certo, placar igual à soma dos pontos, fim da
  partida, bola rápida que não atravessa a raquete e reprodutibilidade.
- **Partes do sistema:** bots, atualização do Q-learning, salvar e carregar modelos, menu,
  placar das partidas, respostas do chat e o bot do Telegram (com um Telegram falso, sem internet).
- **Aprendizado:** um teste treina 2.000 pontos e exige que a IA treinada defenda mais de 3 vezes
  melhor que a sem treino.

## 4. Limites e o que eu faria com mais tempo

- **Uma semente só:** os números vêm de um único treino. Eu repetiria com várias sementes e mostraria média e variação.
- **Curva com ruído:** cada medição usa só 200 pontos. Com mais tempo, mediria com mais pontos ou suavizaria a curva.
- **Não ataca:** sem ver o adversário, a IA não mira. Eu acrescentaria a posição do adversário ao estado
  e testaria treinar contra ela mesma.
- **Estados feitos à mão:** as faixas foram escolhidas por mim. Uma rede neural (DQN) aprenderia
  direto dos números contínuos, com treino mais longo e um cérebro menos fácil de explicar.
- **Pontos travados:** cerca de 30% dos pontos entre a IA difícil e o bot "segue" não terminam.
  As porcentagens consideram só os pontos que terminaram.
- **Sem medição com pessoas:** não medi o desempenho contra humanos de forma sistemática. O jogo
  registra o placar de cada partida e daria para juntar esses dados.
- **Chat limitado:** ele entende só os assuntos previstos. Fora deles, mostra o que pode responder.
- **Controle pela mão (webcam com MediaPipe):** ficou de fora. Seria mais um tipo de jogador com
  as mesmas três ações, como o mouse.

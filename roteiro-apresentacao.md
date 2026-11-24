# Roteiro da apresentação — Pong que aprende

Duração-alvo da demonstração: **~7 minutos**, mais as perguntas. Se o tempo for menor,
corte os blocos marcados como *(opcional)*.

## Antes de começar (checklist, 10 min antes)

- [ ] Notebook na tomada, som ligado (os bipes ajudam a demo).
- [ ] **Janela 1:** `python -m pong.telegram_bot` rodando (aparece "Bot @pong_que_aprende_pixel_bot no ar").
- [ ] **Janela 2:** `python -m pong.jogar` aberto no **menu**.
- [ ] `resultados/aprendizado.png` e `resultados/niveis.png` abertos num visualizador de imagens.
- [ ] Telegram aberto no celular na conversa com **@pong_que_aprende_pixel_bot** (mande um `/start` de teste).
- [ ] *(Se for mostrar a mão)* webcam testada com a luz da sala: menu → Controle → "mão (webcam)".
- [ ] Uma partida curta: deixe **Pontos para vencer = 5** no menu (11 demora demais ao vivo).

## Roteiro

### 1. O problema (30 s)
> "O estúdio queria um adversário que ninguém programou. Em vez de escrever 'siga a bola',
> a IA joga milhares de pontos e descobre sozinha o que funciona. E os níveis de dificuldade
> saem do próprio treino."

### 2. Como a IA funciona (1 min)
Fale sem slide, com 4 números:
- **O que ela vê:** 4 informações relativas à raquete dela (onde está a bola, distância,
  velocidade vertical, se vem ou vai) → **440 situações**.
- **O que ela faz:** sobe, desce ou fica parada (as mesmas 3 ações do humano).
- **Recompensa:** **+1** quando rebate, **+1** quando marca, **−1** quando sofre ponto.
- **Cérebro:** uma tabela de 440 × 3 = **1.320 números = 5,2 KB**. Q-learning ajusta esses números jogando.

### 3. Demo: IA sem treino (45 s)
Menu → Adversário **"IA · sem treino"** → JOGAR. Jogue uns pontos.
> "Essa é a mesma IA antes de treinar: a tabela está zerada, então ela joga ao acaso."

ESC volta ao menu.

### 4. A prova em números (1 min)
Mostre `aprendizado.png`:
> "Durante o treino de 30 mil pontos (5 minutos e meio), medi a IA a cada mil pontos contra
> o bot com que ela treinou. Começa em zero e chega a empatar: 50% dos pontos."

Mostre `niveis.png`:
> "Cada nível é a IA salva num momento do treino. Contra o bot de treino: 0%, 13%, 23% e 51%.
> E nunca perde para o bot aleatório depois de treinada."

### 5. Demo principal: o professor joga + o chat (2 min)
Menu → **"IA · difícil"**, 5 pontos → JOGAR. Passe o teclado para o professor (W/S ou setas).

Enquanto ele joga, no celular pergunte ao bot **"qual o placar?"** e mostre a resposta:
> "O produtor acompanha pelo Telegram, com o placar da partida que está acontecendo agora."

Depois pergunte **"como foi o treino?"** e mande **/grafico**.

### 6. Honestidade: adversário diferente (30 s)
> "Testei contra um bot que ela nunca viu, que calcula onde a bola vai chegar. Ninguém marca
> ponto nele, nem o bot de treino. Mas a defesa dela sobe de 0,2 para 11,5 rebatidas por ponto.
> Ela aprendeu a defender de forma geral, não a vencer quem não erra."

### 7. *(opcional)* Extra: controle pela mão (1 min)
Menu → Controle **"mão (webcam)"** → JOGAR.
> "A mão vira um alvo e a raquete vai até ele com as mesmas 3 ações e a mesma velocidade da IA,
> então ninguém tem vantagem. A detecção é o MediaPipe, rodando numa thread separada."

### 8. Limites e fechamento (30 s)
> "Os limites: a IA não vê o adversário, então não aprende a mirar; treinei com uma semente só;
> e a curva tem ruído porque cada medição usa 200 pontos. Com mais tempo, colocaria a posição do
> adversário no estado e treinaria contra ela mesma. Tudo isso está no decisoes.md, e há 91 testes
> automatizados cobrindo as regras, o aprendizado e o chat."

## Se algo der errado (plano B)

| Problema | Saída |
|---|---|
| Internet caiu / Telegram não conecta | `python -m pong.chat` no terminal: o mesmo assistente, as mesmas respostas |
| Webcam não detecta a mão | ESC → menu → Controle "teclado" (não insista mais de 30 s) |
| Professor quer ver o treino rodando | `python -m pong.treino --pontos 3000 --bloco 500` (uns 20 s) e pergunte ao bot "como foi o treino?" durante |
| Pedem para rodar os testes | `pytest` (uns 40 s) |
| O jogo travou | ESC; se não responder, feche a janela e rode `python -m pong.jogar` de novo |

## Perguntas prováveis (com resposta curta)

**Por que Q-learning em tabela e não rede neural?**
Treina em minutos num computador comum, o cérebro tem tamanho exato (5,2 KB) e cada número
tem significado. Uma rede neural precisaria de mais treino e seria difícil de explicar.

**O que é o ε (epsilon)?**
A chance de a IA fazer uma ação ao acaso em vez da melhor que ela conhece. Começa em 1
(só explora) e cai até 0,05 na metade do treino. Sem explorar, ela nunca descobre jogadas melhores.

**O que a fórmula do Q-learning faz?**
`Q(s,a) ← Q(s,a) + α · (r + γ · max Q(s',·) − Q(s,a))`. Depois de cada decisão, puxa o valor
daquela ação um pouco (α = 0,1) na direção do que ela de fato ganhou mais o melhor valor da
próxima situação, descontado (γ = 0,99).

**Por que 440 estados?**
11 faixas de altura relativa × 4 de distância × 5 de velocidade vertical × 2 (vem ou vai).
Mais faixas = mais detalhe, mas a tabela demora mais para aprender.

**Isso não é "siga a bola" disfarçado?**
Não. Ela recebe a posição da bola em relação à raquete, mas ninguém diz o que fazer com isso.
Sem treino, com a mesma informação, ela joga ao acaso (0% contra o bot de treino).

**Por que ela decide só a cada 4 passos?**
São ~15 decisões por segundo, ritmo humano. Cada decisão pesa mais, e o aprendizado fica mais rápido.

**Por que a recompensa por rebater?**
Só punir quando sofre ponto deixa o sinal raro demais. Rebater é um resultado (não uma
instrução de como jogar) e acelera o aprendizado.

**O que são os pontos "travados"?**
Pontos que passam de 3.000 passos sem ninguém errar. Contam à parte, senão a avaliação não
terminaria. A IA difícil trava ~30% dos pontos contra o bot de treino.

**Como o mouse/mão não dão vantagem?**
Eles não posicionam a raquete: viram um alvo, e a raquete vai até ele com as mesmas três
ações e a mesma velocidade da IA.

**Onde fica o token do Telegram?**
Numa variável de ambiente do Windows (`TELEGRAM_BOT_TOKEN`), nunca no código nem no git.

**Como sei que o placar está certo?**
Há testes: a soma dos pontos de uma partida inteira bate com o placar, o ponto vai para o
lado certo e a partida termina com o vencedor certo.

**O que você faria com mais tempo?**
Pôr a posição do adversário no estado, treinar contra ela mesma, repetir o treino com várias
sementes para mostrar a variação, e medir contra pessoas de verdade.

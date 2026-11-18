# Relato do uso de IA

Usei o Claude Code (assistente de programação) durante todo o projeto: para discutir o
caminho, escrever código e testes, rodar os treinos e revisar os resultados. As decisões
finais foram minhas, e cada parte foi revisada para eu conseguir explicar.

## Onde ajudou

- **Escolha do caminho:** comparou Unity e Python para este problema. Pesaram o treino sem
  tela, o README de 5 comandos e a necessidade de explicar o algoritmo, e fiquei com Python.
  Também apontou que o mouse e a mão não podiam "teletransportar" a raquete, porque isso
  quebraria a regra das três ações e daria vantagem ao humano.
- **Arquitetura:** separar a simulação (sem tela) do desenho, da IA e do chat. Foi isso que
  permitiu treinar rápido e testar tudo sem abrir janela.
- **Detalhes que eu não teria previsto:**
  - a colisão pela trajetória, para a bola rápida não atravessar a raquete;
  - a medição feita com uma cópia da IA, para medir não mudar o que ela aprende;
  - um Telegram falso nos testes do bot.
- **Experimentos:** rodou as duas versões da recompensa em paralelo e comparou os resultados.

## Onde errou (e como percebi)

- **O bot "preditor" perdia até para o aleatório.** A previsão estava certa, mas ele mirava
  até 50 px fora do centro, e a raquete só alcança 45. Percebi pela tabela de bots contra bots
  e corrigi para 35.
- **Corrompeu os acentos de um arquivo** ao editá-lo pelo PowerShell, que leu o UTF-8 como outra
  codificação ("Simulação" virou "SimulaÃ§Ã£o"). Apareceu no `git diff`, e o arquivo foi
  restaurado e editado de outro jeito.
- **Formatação de números com bug:** a primeira versão do texto "pontos de treino · KB" trocava
  a vírgula errada quando o nível era "sem treino". Foi pego na revisão, antes de virar problema.
- **Gráficos com textos sobrepostos** na primeira versão: rótulo cruzando linha e legenda
  cobrindo barra. Só apareceu olhando a imagem gerada, então passei a conferir cada gráfico.
- **Suspeita falsa:** aleatório contra aleatório deu 40% (e não 50%), e parecia que o jogo
  favorecia um lado. O teste com 5.000 pontos nos dois lados mostrou que era só variação.

**O que aprendi sobre usar IA:** ela acelera muito, mas os erros só apareceram porque cada
resultado foi conferido com números, testes e olhando a tela.

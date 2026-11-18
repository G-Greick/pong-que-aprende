"""Assistente do produtor: responde perguntas sobre o treino, os níveis e o placar.

Não depende do Telegram: recebe um texto e devolve uma resposta, lendo só os
arquivos em resultados/. O bot do Telegram (telegram_bot.py) apenas repassa as
mensagens para cá. Para conversar sem Telegram, direto no terminal:

    python -m pong.chat

Entende a pergunta por palavras-chave (sem IA de linguagem): é simples,
previsível, roda offline e sempre responde com os números reais.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from pong.agente import NIVEIS, NOME_NIVEL, AgenteQ
from pong.arquivos import ler_csv, ler_json
from pong.partidas import historico, partida_atual

AJUDA = (
    "Sou o assistente do Pong que aprende. Pode perguntar:\n"
    "• como foi o treino? (/treino)\n"
    "• a IA aprendeu? (/aprendeu)\n"
    "• qual o placar? (/placar)\n"
    "• quais são os níveis? (/niveis)\n"
    "• quanto cérebro ela tem? (/cerebro)\n"
    "• joga bem contra outro adversário? (/adversario)\n"
    "• /grafico mostra a curva de aprendizado"
)

# A primeira intenção com alguma palavra da mensagem vence, então a ordem importa
# ("gráfico do treino" é gráfico, não treino). Palavras com 4+ letras valem como
# começo de palavra: "trein" pega treino, treinou, treinamento.
INTENCOES = [
    ("grafico", ("grafic", "curva", "imagem")),
    ("placar", ("placar", "partida", "ganhando", "vencendo")),
    ("cerebro", ("cerebr", "tamanho", "memoria", "bytes", "tabela", "guarda")),
    ("adversario", ("advers", "predit", "generaliz", "diferente", "outro")),
    ("niveis", ("nivel", "niveis", "dificuldade", "facil", "medio", "dificil")),
    ("aprendeu", ("aprend", "evolu", "melhor", "result", "avalia", "prova", "funcion")),
    ("treino", ("trein", "andamento", "progresso", "status", "termin", "rodando")),
    ("ajuda", ("ajuda", "help", "start", "comando", "menu", "oi", "ola")),
]


@dataclass
class Resposta:
    texto: str
    imagem: Path | None = None


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()


def entender(mensagem: str) -> str | None:
    palavras = re.findall(r"[a-z0-9]+", normalizar(mensagem))
    for intencao, chaves in INTENCOES:
        for chave in chaves:
            if any(p == chave or (len(chave) >= 4 and p.startswith(chave)) for p in palavras):
                return intencao
    return None


def _n(valor, casas: int = 0) -> str:
    """Número no formato brasileiro: 30.000 e 50,9."""
    texto = f"{float(valor):,.{casas}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


class Assistente:
    def __init__(self, pasta: Path = Path("resultados")):
        self.pasta = pasta

    def responder(self, mensagem: str) -> Resposta:
        intencao = entender(mensagem)
        if intencao is None:
            return Resposta("Não entendi a pergunta.\n\n" + AJUDA)
        resposta = getattr(self, f"_{intencao}")()
        return resposta if isinstance(resposta, Resposta) else Resposta(resposta)

    # --- fontes de dados ---------------------------------------------------

    def _avaliacao(self) -> dict[tuple[str, str], dict]:
        return {(l["nivel"], l["bot"]): l for l in ler_csv(self.pasta / "avaliacao.csv")}

    # --- respostas ------------------------------------------------------------

    def _ajuda(self) -> str:
        return AJUDA

    def _treino(self) -> str:
        status = ler_json(self.pasta / "status.json")
        if not status:
            return "Nenhum treino rodou ainda. Para treinar: python -m pong.treino"
        linhas = ler_csv(self.pasta / "treino.csv")
        total, feitos = status["pontos_total"], status.get("pontos_treinados", 0)
        minutos = _n(status.get("segundos", 0) / 60, 1)
        bot = status.get("adversario", "?")

        if status["situacao"] == "treinando":
            return (
                f"O treino está rodando: {_n(feitos)} de {_n(total)} pontos "
                f"({_n(100 * feitos / total)}%), há {minutos} min, contra o bot {bot}.\n"
                f"Na última medição a IA ganhou {_n(status['pct_pontos_avaliacao'], 1)}% dos pontos "
                f"e fez {_n(status['rebatidas_avaliacao'], 1)} rebatidas por ponto. "
                f"Exploração (ε) em {_n(status['epsilon'], 2)}."
            )

        texto = f"O treino terminou: {_n(total)} pontos contra o bot {bot}, em {minutos} minutos."
        if linhas:
            inicio, fim = linhas[0], linhas[-1]
            melhor = max(linhas, key=lambda l: float(l["pct_pontos_avaliacao"]))
            texto += (
                f"\nNo começo a IA ganhava {_n(inicio['pct_pontos_avaliacao'], 1)}% dos pontos "
                f"({_n(inicio['rebatidas_avaliacao'], 1)} rebatidas por ponto). "
                f"No fim, {_n(fim['pct_pontos_avaliacao'], 1)}% "
                f"({_n(fim['rebatidas_avaliacao'], 1)} rebatidas por ponto).\n"
                f"Melhor medição: {_n(melhor['pct_pontos_avaliacao'], 1)}% com "
                f"{_n(melhor['pontos_treinados'])} pontos de treino. Mande /grafico para ver a curva."
            )
        return texto

    def _aprendeu(self) -> str:
        aval = self._avaliacao()
        niveis = [n for n in NIVEIS if (n, "segue") in aval]
        if not niveis:
            return "Ainda não há avaliação final (rode python -m pong.relatorio).\n\n" + self._treino()
        linhas = ["Sim, e dá para medir. Em 1.000 pontos contra o bot de treino (segue):"]
        for n in niveis:
            v = aval[(n, "segue")]
            linhas.append(
                f"• {NOME_NIVEL[n]}: {_n(v['pct_pontos'], 1)}% dos pontos, "
                f"{_n(v['rebatidas_por_ponto'], 1)} rebatidas por ponto"
            )
        primeiro, ultimo = niveis[0], niveis[-1]
        if (primeiro, "aleatorio") in aval and (ultimo, "aleatorio") in aval:
            linhas.append(
                f"Contra o bot aleatório, foi de {_n(aval[(primeiro, 'aleatorio')]['pct_pontos'], 1)}% "
                f"para {_n(aval[(ultimo, 'aleatorio')]['pct_pontos'], 1)}%."
            )
        linhas.append("Mande /grafico para ver a evolução.")
        return "\n".join(linhas)

    def _niveis(self) -> str:
        aval = self._avaliacao()
        linhas = ["São 4 níveis, todos a mesma IA salva em momentos diferentes do treino:"]
        for n, pontos in NIVEIS.items():
            desempenho = ""
            if (n, "segue") in aval:
                desempenho = f": ganha {_n(aval[(n, 'segue')]['pct_pontos'], 1)}% dos pontos contra o bot segue"
            linhas.append(f"• {NOME_NIVEL[n]} ({_n(pontos)} pontos de treino){desempenho}")
        linhas.append("Para jogar: python -m pong.jogar --nivel facil (ou sem-treino, medio, dificil)")
        return "\n".join(linhas)

    def _cerebro(self) -> str:
        ia = AgenteQ()
        estados = ia.disc.n_estados
        return (
            f"O cérebro da IA é uma tabela: {_n(estados)} situações × 3 ações (subir, descer, parar) "
            f"= {_n(estados * 3)} números. Em float32, {_n(ia.tamanho_bytes)} bytes "
            f"({_n(ia.tamanho_bytes / 1024, 1)} KB).\n"
            "Cada número diz quanto ela espera ganhar fazendo aquela ação naquela situação. "
            "Os 4 níveis têm o mesmo tamanho; o que muda são os valores dentro da tabela."
        )

    def _adversario(self) -> str:
        aval = self._avaliacao()
        if ("dificil", "preditor") not in aval:
            return "Ainda não há avaliação contra outros bots (rode python -m pong.relatorio)."
        dificil, crua = aval[("dificil", "preditor")], aval.get(("sem-treino", "preditor"))
        texto = (
            "Ela treinou só contra o bot segue. Contra o preditor, um bot que ela nunca viu "
            "e que calcula onde a bola vai chegar, a IA difícil quase não marca ponto "
            f"({_n(dificil['pct_pontos'], 1)}%): esse bot quase nunca erra. "
            f"Mas ela se defende: {_n(dificil['rebatidas_por_ponto'], 1)} rebatidas por ponto"
        )
        if crua:
            texto += f", contra {_n(crua['rebatidas_por_ponto'], 1)} da IA sem treino"
        return texto + ".\nResumo honesto: aprendeu a defender de forma geral, mas não a vencer um adversário que não erra."

    def _placar(self) -> str:
        atual, partidas = partida_atual(self.pasta), historico(self.pasta)
        if not atual and not partidas:
            return "Nenhuma partida jogada ainda. Para jogar: python -m pong.jogar"
        linhas = []
        if atual:
            jogo = f"{atual['esquerda']} {atual['placar_esquerda']} x {atual['placar_direita']} {atual['direita']}"
            if atual["situacao"] == "em andamento":
                linhas.append(f"Partida em andamento: {jogo} (vence quem fizer {atual['pontos_para_vencer']}).")
            elif atual["situacao"] == "terminada":
                linhas.append(f"Última partida: {atual['vencedor']} venceu, {jogo}.")
            else:
                linhas.append(f"A última partida foi interrompida em {jogo}.")
        contra_ia = [p for p in partidas if p["esquerda"] == "você" and p["direita"].startswith("IA")]
        if contra_ia:
            humanos = sum(p["vencedor"] == "você" for p in contra_ia)
            total = len(contra_ia)
            partidas_txt = "1 partida terminada" if total == 1 else f"{total} partidas terminadas"
            linhas.append(f"Humanos contra a IA: {partidas_txt}, humanos {humanos} x {total - humanos} IA.")
        return "\n".join(linhas)

    def _grafico(self) -> Resposta:
        imagem = self.pasta / "aprendizado.png"
        if not imagem.exists():
            return Resposta("O gráfico ainda não foi gerado. Rode: python -m pong.relatorio")
        return Resposta("Curva de aprendizado: rebatidas por ponto e % dos pontos ganhos ao longo do treino.", imagem)


def main() -> None:
    assistente = Assistente()
    print("Chat do produtor (sem Telegram). Escreva uma pergunta; 'sair' encerra.\n")
    print(AJUDA)
    while True:
        try:
            mensagem = input("\n> ")
        except (EOFError, KeyboardInterrupt):
            break
        if normalizar(mensagem).strip() in ("sair", "exit", "quit"):
            break
        resposta = assistente.responder(mensagem)
        print(resposta.texto)
        if resposta.imagem:
            print(f"[imagem: {resposta.imagem}]")


if __name__ == "__main__":
    main()

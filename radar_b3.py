
import os
import json
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
from pathlib import Path

# ==========================================================
# BASCKA RADAR B3 - VERSAO 1.0
# MOTOR ORIGINAL DE ROMPIMENTOS
# ==========================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

TICKERS_B3 = [
    "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA",
    "WEGE3.SA", "EMBR3.SA", "PRIO3.SA", "RENT3.SA", "EQTL3.SA",
    "SUZB3.SA", "GGBR4.SA", "RADL3.SA", "LREN3.SA", "MRFG3.SA",
    "BRFS3.SA", "JBSS3.SA", "DIRR3.SA", "CURY3.SA", "CYRE3.SA",
    "SBSP3.SA", "CPLE6.SA", "CMIG4.SA", "ELET3.SA", "B3SA3.SA"
]

ARQUIVO_RESULTADOS = Path("data.json")


def enviar_telegram(mensagem):

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram nao configurado.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "Markdown"
    }

    try:
        resposta = requests.post(url, json=payload, timeout=20)
        resposta.raise_for_status()

        if not resposta.json().get("ok"):
            print("Telegram retornou erro:", resposta.text)
            return False

        return True

    except Exception as erro:
        print("Erro Telegram:", erro)
        return False


def salvar_resultados(dados):

    ARQUIVO_RESULTADOS.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def verificar_pregao():

    fuso_br = pytz.timezone("America/Sao_Paulo")
    agora = datetime.now(fuso_br)

    resultado = {
        "atualizado_em": agora.strftime("%d/%m/%Y %H:%M:%S"),
        "status": "executado",
        "mensagem": "",
        "acoes_analisadas": 0,
        "acoes": [],
        "alertas": [],
        "erros": [],
        "quantidade_alertas": 0
    }

    # HORARIO ORIGINAL
    if agora.weekday() >= 5 or not (10 <= agora.hour < 17):

        resultado["status"] = "fora_do_pregao"
        resultado["mensagem"] = "Fora do horario do pregao."
        salvar_resultados(resultado)
        return resultado

    # IGNORA PRIMEIROS 20 MINUTOS
    minutos_passados = (agora.hour - 10) * 60 + agora.minute

    if minutos_passados < 20:

        resultado["status"] = "aguardando"
        resultado["mensagem"] = "Aguardando primeiros 20 minutos."
        salvar_resultados(resultado)
        return resultado

    fator_projecao = 420 / minutos_passados

    alertas = []
    linhas = []

    for ticker in TICKERS_B3:

        try:

            df = yf.download(
                ticker,
                period="30d",
                interval="1d",
                progress=False,
                auto_adjust=False,
                threads=False
            )

            if df is None or len(df) < 21:
                resultado["erros"].append(
                    f"{ticker}: historico insuficiente"
                )
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            hoje = df.iloc[-1]
            ontem = df.iloc[-2]
            historico = df.iloc[-21:-1]

            preco_atual = float(hoje["Close"])
            abertura = float(hoje["Open"])
            maxima_hoje = float(hoje["High"])
            fechamento_ontem = float(ontem["Close"])

            volume_hoje = float(hoje["Volume"])

            if fechamento_ontem <= 0 or maxima_hoje <= 0:
                continue

            # 1. VARIACAO DIARIA

            var_dia = (
                (preco_atual - fechamento_ontem)
                / fechamento_ontem
            ) * 100

            # 2. VOLUME PROJETADO

            vol_medio_20d = float(
                historico["Volume"].mean()
            )

            vol_projetado = volume_hoje * fator_projecao

            rvol = (
                vol_projetado / vol_medio_20d
                if vol_medio_20d > 0 else 0
            )

            # 3. MAXIMA DOS ULTIMOS 20 PREGOES

            maxima_20d = float(
                historico["High"].max()
            )

            rompendo_20d = (
                preco_atual >= maxima_20d * 0.995
            )

            # 4. DISTANCIA DA MAXIMA DIARIA

            dist_maxima_dia = (
                (maxima_hoje - preco_atual)
                / maxima_hoje
            ) * 100

            # REGISTRO DA ACAO

            linha = {
                "ticker": ticker.replace(".SA", ""),
                "preco": round(preco_atual, 2),
                "abertura": round(abertura, 2),
                "variacao_pct": round(var_dia, 2),
                "volume_dia": int(volume_hoje),
                "volume_medio_20d": int(vol_medio_20d),
                "rvol_projetado": round(rvol, 2),
                "maxima_20d": round(maxima_20d, 2),
                "maxima_dia": round(maxima_hoje, 2),
                "distancia_maxima_dia_pct": round(
                    dist_maxima_dia, 2
                ),
                "sinal": False
            }

            # GATILHO ORIGINAL

            if (
                1.5 <= var_dia <= 5.0
                and rvol >= 2.0
                and rompendo_20d
                and dist_maxima_dia <= 1.0
            ):

                linha["sinal"] = True

                alertas.append(
                    f"🚀 *{ticker.replace('.SA', '')}*\n"
                    f"• Preço: R$ {preco_atual:.2f} "
                    f"(*+{var_dia:.2f}%*)\n"
                    f"• Vol. Projetado: *{rvol:.1f}x* "
                    f"a média 20d\n"
                    f"• Status: Rompendo máxima de 20 dias "
                    f"perto do topo do dia"
                )

            linhas.append(linha)
            resultado["acoes_analisadas"] += 1

        except Exception as erro:

            resultado["erros"].append(
                f"{ticker}: {str(erro)[:200]}"
            )

            print(f"Erro em {ticker}: {erro}")
            continue

    resultado["acoes"] = linhas
    resultado["alertas"] = alertas
    resultado["quantidade_alertas"] = len(alertas)

    resultado["mensagem"] = (
        f"Analise concluida: "
        f"{resultado['acoes_analisadas']} acoes analisadas; "
        f"{len(alertas)} alertas; "
        f"{len(resultado['erros'])} erros."
    )

    # SALVA RESULTADOS

    salvar_resultados(resultado)

    # ENVIA TELEGRAM

    if alertas:

        cabecalho = (
            f"📊 *Radar B3 "
            f"({agora.strftime('%H:%M')}) "
            f"- Gatilho de Rompimento*\n\n"
        )

        sucesso = enviar_telegram(
            cabecalho + "\n\n".join(alertas)
        )

        resultado["telegram_enviado"] = sucesso

    else:

        resultado["telegram_enviado"] = False

    salvar_resultados(resultado)

    print(resultado["mensagem"])

    return resultado


if __name__ == "__main__":

    verificar_pregao()

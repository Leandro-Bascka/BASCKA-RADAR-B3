
import requests
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# ==========================================================
# BASCKA RADAR B3 - PAINEL STREAMLIT
# ==========================================================

GITHUB_USER = "Leandro-Bascka"
GITHUB_REPO = "BASCKA_RADAR_B3"
GITHUB_BRANCH = "main"

URL_DADOS = (
    f"https://raw.githubusercontent.com/"
    f"{GITHUB_USER}/{GITHUB_REPO}/"
    f"{GITHUB_BRANCH}/data.json"
)

st.set_page_config(
    page_title="BASCKA RADAR B3",
    page_icon="📈",
    layout="wide"
)

# ATUALIZACAO VISUAL A CADA 10 MINUTOS
st_autorefresh(
    interval=600000,
    key="atualizacao_radar"
)

@st.cache_data(ttl=60)
def carregar_dados():

    resposta = requests.get(
        URL_DADOS,
        timeout=20
    )

    resposta.raise_for_status()

    return resposta.json()


st.title("📈 BASCKA RADAR B3")

st.caption(
    "Radar de rompimentos - Monitoramento de 25 ações da B3"
)

try:

    dados = carregar_dados()

except Exception as erro:

    st.error("Nao foi possivel carregar os resultados.")

    st.info(
        "Confira usuario, repositorio e arquivo data.json."
    )

    st.code(str(erro))

    st.stop()


st.caption(
    f"Ultima execucao: {dados.get('atualizado_em', '-')}"
)

st.caption(
    f"Status: {dados.get('status', '-')}"
)

st.info(
    dados.get("mensagem", "Aguardando dados.")
)

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Acoes analisadas",
    dados.get("acoes_analisadas", 0)
)

col2.metric(
    "Alertas encontrados",
    dados.get("quantidade_alertas", 0)
)

col3.metric(
    "Erros",
    len(dados.get("erros", []))
)

col4.metric(
    "Atualizacao programada",
    "10 minutos"
)

st.divider()

# ALERTAS

st.subheader("🚀 ALERTAS DO RADAR")

alertas = dados.get("alertas", [])

if alertas:

    for alerta in alertas:
        st.markdown(alerta)

else:

    st.info(
        "Nenhum alerta encontrado na ultima analise."
    )

st.divider()

# TABELA DE ACOES

st.subheader("📊 ACOES MONITORADAS")

acoes = dados.get("acoes", [])

if acoes:

    tabela = pd.DataFrame(acoes)

    tabela = tabela.rename(columns={
        "ticker": "Acao",
        "preco": "Preco",
        "variacao_pct": "Variacao %",
        "rvol_projetado": "RVOL",
        "maxima_20d": "Maxima 20d",
        "maxima_dia": "Maxima dia",
        "distancia_maxima_dia_pct": "Distancia maxima %",
        "sinal": "Alerta"
    })

    tabela = tabela.sort_values(
        "Alerta",
        ascending=False
    )

    st.dataframe(
        tabela,
        use_container_width=True,
        hide_index=True
    )

else:

    st.warning(
        "Aguardando primeira analise do radar."
    )

# CRITERIOS

with st.expander("Criterios originais"):

    st.write("Variacao diaria: +1,5% a +5,0%")
    st.write("RVOL projetado: minimo 2,0x")
    st.write("Maxima 20 dias: proximidade de 99,5%")
    st.write("Distancia da maxima diaria: ate 1,0%")

    st.warning(
        "O motor original utiliza candles diarios do Yahoo Finance. "
        "A execucao a cada 10 minutos nao garante dados intradiarios "
        "atualizados a cada ciclo."
    )

# ERROS

erros = dados.get("erros", [])

if erros:

    with st.expander("Detalhes dos erros"):

        for erro in erros:
            st.write(erro)

st.caption(
    "BASCKA RADAR B3 - Ferramenta de monitoramento."
)

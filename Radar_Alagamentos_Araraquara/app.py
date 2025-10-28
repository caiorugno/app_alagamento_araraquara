import streamlit as st
import pandas as pd
import plotly.express as px
from modules.api_clima import get_previsao
from modules.mapa import desenhar_mapa
from modules.risco import calcular_risco

st.set_page_config(page_title="Radar de Alagamentos", layout="wide")
with open("assets/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    st.title("🌞 Radar de Alagamentos – Araraquara, Morada do Sol")
    st.markdown("<hr style='border-top: 1px solid #FF9800;'>", unsafe_allow_html=True)
    st.caption("🌞 Desenvolvido em Araraquara – Cidade onde mora o sol")




# Cabeçalho com logo e título
col1, col2 = st.columns([1, 5])
with col1:
    st.image("assets/logo.png", width=100)
with col2:
    st.title("🌧️ Radar de Alagamentos – Araraquara")

# Dados da API
dados_clima = get_previsao("Araraquara,BR")

# Tabs para organizar visualizações
tab1, tab2, tab3 = st.tabs(["📈 Previsão de Chuva", "🗺️ Mapa Interativo", "📊 Dados Brutos"])

with tab1:
    st.subheader("Previsão de Chuva nas Próximas Horas")

    # Filtro por volume mínimo
    volume_minimo = st.slider("Filtrar por volume mínimo de chuva (mm)", 0.0, 20.0, 0.0)
    dados_filtrados = dados_clima[dados_clima["Chuva (mm)"] >= volume_minimo]

    # Gráfico
    fig = px.bar(dados_filtrados, x="Hora", y="Chuva (mm)", color="Chuva (mm)",
                 labels={"Hora": "Hora", "Chuva (mm)": "Chuva (mm)"},
                 title="Volume de Chuva por Hora")
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    desenhar_mapa(dados_clima)

with tab3:
    st.subheader("Dados recebidos da API")
    st.dataframe(dados_clima)

# Rodapé opcional
st.markdown("---")
st.caption("Desenvolvido por Caio Rugno • Dados via OpenWeatherMap • Projeto piloto para monitoramento urbano")

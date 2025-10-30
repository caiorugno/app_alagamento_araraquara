import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from streamlit_folium import st_folium
import folium
from modules.api_clima import get_previsao
from modules.mapa import desenhar_mapa
from modules.risco import calcular_risco
import time

# Configuração da página
st.set_page_config(page_title="Radar de Alagamentos", layout="wide")

# Estilo e cabeçalho
with open("assets/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Cabeçalho
col1, col2 = st.columns([1, 5])
with col1:
    st.image("assets/logo.png", width=100)
with col2:
    st.title("🌧️ Radar de Alagamentos – Araraquara, Morada do Sol")
    st.caption("🌞 Desenvolvido em Araraquara – Cidade onde mora o sol")
    st.markdown("<hr style='border-top: 1px solid #FF9800;'>", unsafe_allow_html=True)

# Funções utilitárias
def geocodificar_endereco(endereco):
    geolocator = Nominatim(user_agent="radar_alagamentos", timeout=10)
    try:
        time.sleep(1)
        location = geolocator.geocode(endereco + ", Araraquara, Brasil")
        if location:
            return location.latitude, location.longitude
    except Exception as e:
        st.error(f"Erro ao buscar endereço: {e}")
    return None, None

def formatar_datas(datas_str):
    if not isinstance(datas_str, str):
        datas_str = str(datas_str)
    datas = datas_str.split(";") if datas_str else []
    datas_formatadas = []
    for d in datas:
        try:
            dt = pd.to_datetime(d, errors="coerce")
            if pd.notnull(dt):
                datas_formatadas.append(dt.strftime("%d-%m-%Y"))
        except:
            continue
    return "; ".join(datas_formatadas)

# Dados da API
dados_clima = get_previsao("Araraquara,BR")

# Preparação dos dados
if not dados_clima.empty and "Hora" in dados_clima.columns:
    dados_clima["Hora"] = pd.to_datetime(dados_clima["Hora"])
    agora = datetime.now()
    limite = agora + pd.Timedelta(hours=24)
    dados_hoje = dados_clima[(dados_clima["Hora"] >= agora) & (dados_clima["Hora"] <= limite)]
    dados_clima["Dia"] = dados_clima["Hora"].dt.date
    chuva_por_dia = dados_clima.groupby("Dia")["Chuva (mm)"].sum().reset_index()
else:
    dados_hoje = pd.DataFrame(columns=["Hora", "Chuva (mm)"])
    chuva_por_dia = pd.DataFrame(columns=["Dia", "Chuva (mm)"])

# 📍 Escolha de localização
st.markdown("### 📍 Escolha sua localização")

opcao_localizacao = st.radio("Como deseja definir sua localização?", ["Clique no mapa", "Digite seu endereço"])
lat_usuario, lon_usuario = None, None

if opcao_localizacao == "Digite seu endereço":
    endereco = st.text_input("Digite seu endereço completo (ex: Rua Maurício Galli, Araraquara)")
    if endereco:
        lat_usuario, lon_usuario = geocodificar_endereco(endereco)
        if lat_usuario is not None and lon_usuario is not None:
            st.success(f"📍 Localização encontrada: {lat_usuario:.6f}, {lon_usuario:.6f}")
            mapa_usuario = folium.Map(location=[lat_usuario, lon_usuario], zoom_start=13)
            folium.Marker([lat_usuario, lon_usuario], tooltip="Você está aqui", icon=folium.Icon(color="blue")).add_to(mapa_usuario)
            st_folium(mapa_usuario, height=400, width=700)
        else:
            st.error("Endereço não encontrado. Tente ser mais específico.")
else:
    mapa = folium.Map(location=[-21.7945, -48.1752], zoom_start=13)
    mapa.add_child(folium.LatLngPopup())
    resultado = st_folium(mapa, height=400, width=700)
    if resultado and resultado.get("last_clicked"):
        lat_usuario = resultado["last_clicked"]["lat"]
        lon_usuario = resultado["last_clicked"]["lng"]
        st.success(f"📍 Localização selecionada: {lat_usuario:.6f}, {lon_usuario:.6f}")
    else:
        st.warning("Clique no mapa para selecionar sua localização.")

# 🔍 Cálculo de risco, estatísticas e gráfico
if lat_usuario is not None and lon_usuario is not None and not dados_hoje.empty:
    try:
        pontos = pd.read_csv("data/pontos_alagamento.csv")
        colunas_esperadas = {"latitude", "longitude", "local", "ocorrencias", "ultimas_datas"}
        if pontos.empty or not colunas_esperadas.issubset(pontos.columns):
            st.warning("Arquivo de pontos de alagamento está vazio ou incompleto.")
        else:
            pontos["distancia_km"] = pontos.apply(
                lambda row: geodesic((lat_usuario, lon_usuario), (row["latitude"], row["longitude"])).km,
                axis=1
            )
            ponto_proximo = pontos.loc[pontos["distancia_km"].idxmin()]
            chuva_total = dados_hoje["Chuva (mm)"].sum()
            risco = calcular_risco(chuva_total)

            historico_raw = ponto_proximo.get("ultimas_datas", "")
            historico = formatar_datas(historico_raw)
            ocorrencias = ponto_proximo.get("ocorrencias", 0)

            st.info(f"""
            📍 Você está próximo de **{ponto_proximo['local']}** ({ponto_proximo['distancia_km']:.2f} km).  
            🌧️ Previsão de chuva: **{chuva_total:.1f} mm**  
            🚨 Risco de alagamento: **{risco.upper()}**  
            📚 Histórico de inundações: {ocorrencias} ocorrência(s)  
            🗓️ Datas registradas: {historico if historico else "Sem registros"}
            """)

            mapa_marcado = folium.Map(location=[lat_usuario, lon_usuario], zoom_start=13)
            folium.Marker([lat_usuario, lon_usuario], tooltip="Você está aqui", icon=folium.Icon(color="blue")).add_to(mapa_marcado)

            for _, row in pontos.iterrows():
                tooltip = f"{row['local']}\nOcorrências: {row['ocorrencias']}\nHistórico: {formatar_datas(row['ultimas_datas'])}"
                folium.Marker(
                    location=[row["latitude"], row["longitude"]],
                    tooltip=tooltip,
                    icon=folium.Icon(color="red", icon="info-sign")
                ).add_to(mapa_marcado)

            st_folium(mapa_marcado, height=500, width=700)

            # 📊 Estatísticas gerais
            st.markdown("### 📊 Estatísticas de Inundações")
            total_pontos = len(pontos)
            total_ocorrencias = pontos["ocorrencias"].sum()
            ponto_critico = pontos.loc[pontos["ocorrencias"].idxmax()]["local"]
            st.metric("Total de pontos monitorados", total_pontos)
            st.metric("Total de ocorrências registradas", total_ocorrencias)
            st.metric("Ponto mais crítico", ponto_critico)

            # 📈 Gráfico de evolução por ano
            pontos["ultimas_datas"] = pontos["ultimas_datas"].fillna("").astype(str)
            datas = pontos["ultimas_datas"].str.split(";").explode()
            datas = datas[datas.str.strip() != ""]
            if not datas.empty:
                datas_convertidas = pd.to_datetime(datas, errors="coerce").dropna()
                anos = datas_convertidas.dt.year
                df_anos = anos.value_counts().sort_index().reset_index()
                df_anos.columns = ["Ano", "Ocorrências"]
                fig_hist = px.bar(df_anos, x="Ano", y="Ocorrências", title="Ocorrências de Alagamento por Ano")
                st.plotly_chart(fig_hist, use_container_width=True)

    except Exception as e:
        st.warning(f"Erro ao calcular risco, estatísticas ou carregar mapa: {e}")

# 🧭 Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Previsão de Chuva (24h)",
    "🗺️ Mapa Interativo",
    "📊 Dados Brutos",
    "📅 Chuva nos Próximos Dias",
    "🚨 O que fazer em caso de alagamento"
])


with tab1:
    st.subheader("Previsão de Chuva nas Próximas 24 Horas")
    if not dados_hoje.empty:
        volume_minimo = st.slider("Filtrar por volume mínimo de chuva (mm)", 0.0, 20.0, 0.0)
        dados_filtrados = dados_hoje[dados_hoje["Chuva (mm)"] >= volume_minimo]
        fig = px.bar(dados_filtrados, x="Hora", y="Chuva (mm)", color="Chuva (mm)",
                     labels={"Hora": "Hora", "Chuva (mm)": "Chuva (mm)"},
                     title="Volume de Chuva por Hora")
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Nenhum dado de chuva disponível para as próximas 24 horas.")

with tab2:
    st.subheader("🗺️ Mapa Interativo de Risco")
    if not dados_hoje.empty:
        desenhar_mapa(dados_hoje)
        st.markdown("""
        ### 🗂️ Legenda de Risco:
        - 🟢 **Baixo** (chuva < 10 mm)  
        - 🟠 **Médio** (chuva entre 10 e 20 mm)  
        - 🔴 **Alto** (chuva ≥ 20 mm)
        """)
    else:
        st.warning("Mapa indisponível: sem dados de chuva para as próximas 24 horas.")

with tab3:
    st.subheader("📊 Dados recebidos da API (próximas horas)")
    if not dados_clima.empty:
        st.dataframe(dados_clima)
    else:
        st.warning("Nenhum dado disponível da API no momento.")

with tab4:
    st.subheader("📅 Chuva Total por Dia (Próximos 5 dias)")
    if not chuva_por_dia.empty:
        fig_dias = px.bar(chuva_por_dia, x="Dia", y="Chuva (mm)", color="Chuva (mm)",
                          labels={"Dia": "Dia", "Chuva (mm)": "Chuva (mm)"},
                          title="Previsão de Chuva por Dia")
        fig_dias.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_dias, use_container_width=True)
    else:
        st.warning("Não há dados disponíveis para os próximos dias.")

with tab5:
    st.subheader("🚨 O que fazer em caso de alagamento")
    st.markdown("Em situações de alagamento, manter a calma e agir com segurança é essencial. Aqui estão algumas orientações práticas:")

    with st.expander("🧭 Antes da chuva"):
        st.markdown("""
        - Mantenha documentos e objetos importantes em locais elevados  
        - Tenha lanternas, pilhas e rádio à disposição  
        - Evite jogar lixo nas ruas — isso entope bueiros  
        - Acompanhe previsões de chuva e alertas da Defesa Civil
        """)

    with st.expander("🌊 Durante o alagamento"):
        st.markdown("""
        - Evite contato com a água da enchente — pode estar contaminada  
        - Desligue a energia elétrica se a água começar a subir  
        - Não tente atravessar áreas alagadas a pé ou de carro  
        - Busque abrigo em locais altos e seguros
        """)

    with st.expander("🧹 Após o alagamento"):
        st.markdown("""
        - Limpe e desinfete objetos e ambientes atingidos  
        - Verifique danos na estrutura da casa antes de retornar  
        - Registre perdas e entre em contato com órgãos responsáveis  
        - Apoie vizinhos e compartilhe informações úteis
        """)

    st.markdown("### ✅ Checklist de segurança")
    st.checkbox("Desliguei os aparelhos elétricos")
    st.checkbox("Evitei contato com água da enchente")
    st.checkbox("Busquei abrigo em local seguro")
    st.checkbox("Acompanhei alertas da Defesa Civil")

    st.markdown("### 📞 Contatos úteis")
    st.markdown("""
    - Defesa Civil: 199  
    - Corpo de Bombeiros: 193  
    - SAMU: 192  
    - Prefeitura de Araraquara: [site oficial](https://www.araraquara.sp.gov.br)
    """)

    st.info("Essas orientações são gerais. Em caso de emergência, siga sempre as instruções das autoridades locais.")

# Rodapé
st.markdown("---")
st.caption("Desenvolvido por Caio Rugno • Dados via OpenWeatherMap • Projeto piloto para monitoramento urbano")
    
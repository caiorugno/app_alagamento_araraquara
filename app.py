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

# Estilo da página
with open("assets/style.css", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Cabeçalho principal
col1, col2 = st.columns([1, 5])
with col1:
    st.image("assets/logo.png", width=180)
with col2:
    st.markdown("""
    <h1 style="margin-bottom: 0; font-size: 2.5em;">
        <span style="color:#007BFF;">Rain</span><span style="color:#FCA311;">Dar</span>
    </h1>
    <p style="margin-top: 0; font-size: 16px;">Monitoramento inteligente de chuvas e alagamentos</p>
    """, unsafe_allow_html=True)

st.markdown("<hr style='border-top: 1px solid #FF9800;'>", unsafe_allow_html=True)


# Tabs principais visíveis logo abaixo do cabeçalho
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "Previsão de Chuva (24h)",
    "Mapa Interativo",
    "Resumo do Clima",
    "Chuva nos Próximos Dias",
    "O que fazer em caso de alagamento",
    "Alertas de Tempestade",
    "Mapas de Chuva em Tempo Real",
    "Sobre o Projeto" 
])


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

from pytz import timezone, UTC

from pytz import timezone, UTC
from datetime import datetime

with tab1:
    st.subheader("Previsão de Chuva nas Próximas 24 Horas")
    if not dados_clima.empty and "Hora" in dados_clima.columns:
        dados_clima["Hora"] = pd.to_datetime(dados_clima["Hora"], utc=True)

        agora_utc = pd.Timestamp.now(tz=UTC)
        limite_utc = agora_utc + pd.Timedelta(hours=24)

        dados_hoje = dados_clima[
            (dados_clima["Hora"] >= agora_utc) & (dados_clima["Hora"] <= limite_utc)
        ].copy()

        fuso_brasilia = timezone("America/Sao_Paulo")
        dados_hoje["Hora_local"] = dados_hoje["Hora"].dt.tz_convert(fuso_brasilia)

        if not dados_hoje.empty:
            volume_minimo = st.slider("Filtrar por volume mínimo de chuva (mm)", 0.0, 20.0, 0.0)
            dados_filtrados = dados_hoje[dados_hoje["Chuva (mm)"] >= volume_minimo]

            fig = px.bar(
                dados_filtrados,
                x="Hora_local",
                y="Chuva (mm)",
                color="Chuva (mm)",
                labels={"Hora_local": "Hora", "Chuva (mm)": "Chuva (mm)"},
                title="Volume de Chuva por Hora"
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            # Hora atual e localização
            hora_atual = datetime.now(fuso_brasilia).strftime("%d/%m/%Y %H:%M")
            localizacao = "Araraquara, São Paulo, Brasil"
            st.markdown("---")
            st.markdown(f"**Hora atual:** {hora_atual}")
            st.markdown(f"**Localização:** {localizacao}")
        else:
            st.warning("Nenhum dado de chuva disponível para as próximas 24 horas.")
    else:
        st.warning("Dados de chuva não disponíveis ou incompletos.")



with tab2:

    if not dados_hoje.empty:
        desenhar_mapa(dados_hoje)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        ### 🎯 Legenda de Risco:
        - 🟢 **Baixo** (chuva < 10 mm)  
        - 🟠 **Médio** (chuva entre 10 e 20 mm)  
        - 🔴 **Alto** (chuva ≥ 20 mm)
        """)
    else:
        st.warning("Mapa indisponível: sem dados de chuva para as próximas 24 horas.")

    st.markdown("<br><hr><br>", unsafe_allow_html=True)

    st.subheader("📍 Pontos de Alagamento Monitorados")
    st.markdown("""
    Este painel mostra estatísticas específicas de locais que já registraram ocorrências de alagamento em Araraquara.  
    Os dados são baseados em pontos monitorados e não representam todos os bairros da cidade.
    """)

    try:
        pontos = pd.read_csv("data/pontos_alagamento.csv")
        pontos["ultimas_datas"] = pontos["ultimas_datas"].fillna("").astype(str)

        mapa_pontos = folium.Map(location=[-21.7945, -48.1752], zoom_start=13)
        for _, row in pontos.iterrows():
            folium.Marker(
                location=[row["latitude"], row["longitude"]],
                tooltip=row["local"],
                icon=folium.Icon(color="red", icon="info-sign")
            ).add_to(mapa_pontos)

        st.markdown("### 🗺️ Mapa dos pontos monitorados")
        st_folium(mapa_pontos, height=300, width=700)

        locais_disponiveis = sorted(pontos["local"].unique())
        local_selecionado = st.selectbox("Selecione um ponto monitorado", locais_disponiveis)

        dados_local = pontos[pontos["local"] == local_selecionado]
        total_ocorrencias = dados_local["ocorrencias"].sum()

        datas = dados_local["ultimas_datas"].str.split(";").explode()
        datas = datas[datas.str.strip() != ""]
        datas_convertidas = pd.to_datetime(datas, errors="coerce").dropna()

        st.markdown(f"### 📊 Estatísticas para **{local_selecionado}**")
        st.metric("Ocorrências registradas", total_ocorrencias)

        if not datas_convertidas.empty:
            anos = datas_convertidas.dt.year
            df_anos = anos.value_counts().sort_index().reset_index()
            df_anos.columns = ["Ano", "Ocorrências"]
            fig_local = px.bar(df_anos, x="Ano", y="Ocorrências", title=f"Ocorrências em {local_selecionado} por Ano")
            st.plotly_chart(fig_local, use_container_width=True)

            st.markdown("🗓️ Datas registradas:")
            for d in datas_convertidas.sort_values():
                st.write(f"- {d.strftime('%d/%m/%Y')}")
        else:
            st.warning("Nenhuma data registrada para este ponto monitorado.")

    except Exception as e:
        st.error(f"Erro ao carregar estatísticas dos pontos monitorados: {e}")


with tab3:
    st.subheader("Resumo do Clima")
    
    if not dados_clima.empty:
        clima_atual = dados_clima.iloc[0]

        temperatura = clima_atual.get("Temperatura (°C)")
        umidade = clima_atual.get("Umidade (%)")
        vento = clima_atual.get("Velocidade do Vento (m/s)")
        pressao = clima_atual.get("Pressão Atmosférica (hPa)")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("🌡️ Temperatura", f"{temperatura:.1f} °C" if pd.notnull(temperatura) else "—")
            st.metric("💧 Umidade", f"{umidade:.0f} %" if pd.notnull(umidade) else "—")
        with col2:
            st.metric("🌬️ Vento", f"{vento:.1f} m/s" if pd.notnull(vento) else "—")
            st.metric("📊 Pressão", f"{pressao:.0f} hPa" if pd.notnull(pressao) else "—")

        st.markdown("###  Interpretação dos dados")

        if pd.notnull(temperatura):
            if 23 <= temperatura <= 26:
                st.success("🌡️ Temperatura dentro da faixa de conforto térmico recomendada (23°C a 26°C).")
            elif temperatura < 20:
                st.info("🌡️ Temperatura considerada baixa para conforto térmico.")
            else:
                st.warning("🌡️ Temperatura acima da faixa ideal — pode causar desconforto térmico.")

        if umidade is not None and not pd.isna(umidade):
            if 50 <= umidade <= 60:
                st.success("💧 Umidade ideal para saúde respiratória segundo a OMS. Ajuda a manter vias aéreas hidratadas e reduz risco de infecções.")
            elif 30 <= umidade < 50:
                st.info("💧 Umidade moderada. Pode causar leve ressecamento das mucosas, especialmente em ambientes com ar condicionado.")
            elif 20 <= umidade < 30:
                st.warning("💧 Umidade baixa — atenção! Pode provocar garganta seca, irritação nos olhos e aumento de alergias respiratórias.")
            elif umidade < 20:
                st.error("💧 Umidade extremamente baixa — risco elevado de problemas respiratórios como asma, bronquite e infecções. Evite ambientes fechados e hidrate-se com frequência.")
            elif umidade > 80:
                st.warning("💧 Umidade elevada — favorece sensação de abafamento e proliferação de fungos e ácaros.")

        if pd.notnull(vento):
            vento_kmh = vento * 3.6
            if vento_kmh < 20:
                st.info("🌬️ Vento fraco — condições calmas.")
            elif vento_kmh < 50:
                st.warning("🌬️ Vento moderado — pode causar desconforto em áreas abertas.")
            else:
                st.error("🌬️ Vento forte — atenção para possíveis impactos em estruturas e deslocamentos.")

        if pd.notnull(pressao):
            if 1000 <= pressao <= 1020:
                st.success("📊 Pressão atmosférica dentro da faixa normal ao nível do mar.")
            elif pressao < 990:
                st.warning("📊 Pressão baixa — pode indicar instabilidade ou aproximação de frente fria.")
            elif pressao > 1030:
                st.info("📊 Pressão alta — geralmente associada a tempo estável.")

        st.markdown("Esses dados representam as condições mais recentes disponíveis para Araraquara.")
    
    else:
        st.warning("Dados meteorológicos não disponíveis no momento.")


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

with tab6:
    st.subheader("🚨 Monitoramento de Tempestades Inesperadas")

    # 🔍 Análise dos dados da OpenWeatherMap
    if not dados_hoje.empty:
        alerta_detectado = False
        mensagens_alerta = []

        for _, row in dados_hoje.iterrows():
            chuva = row.get("Chuva (mm)", 0)
            vento = row.get("Velocidade do Vento (m/s)", 0) * 3.6  # km/h
            pressao = row.get("Pressão Atmosférica (hPa)", 1010)
            umidade = row.get("Umidade (%)", 0)
            hora = pd.to_datetime(row["Hora"]).strftime("%d/%m %Hh")

            if chuva >= 15:
                alerta_detectado = True
                mensagens_alerta.append(f"🌧️ {hora}: Previsão de chuva forte (**{chuva:.1f} mm**)")

            if vento >= 50:
                alerta_detectado = True
                mensagens_alerta.append(f"🌬️ {hora}: Vento forte previsto (**{vento:.0f} km/h**)")

            if pressao < 990:
                alerta_detectado = True
                mensagens_alerta.append(f"📉 {hora}: Pressão atmosférica baixa (**{pressao:.0f} hPa**)")

            if umidade >= 90:
                alerta_detectado = True
                mensagens_alerta.append(f"🫧 {hora}: Umidade elevada (**{umidade:.0f} %**)")

        if alerta_detectado:
            st.error("⚠️ Tempestade inesperada detectada nas próximas horas!")
            for msg in mensagens_alerta:
                st.markdown(f"- {msg}")
            st.markdown("🔎 Acompanhe o radar IPMet abaixo e evite áreas de risco.")
        else:
            st.success("✅ Nenhum sinal de tempestade forte nas próximas horas.")
            st.markdown("Mesmo assim, continue acompanhando o radar e as atualizações.")

    else:
        st.warning("Dados insuficientes para gerar alertas no momento.")

    st.markdown("---")

import streamlit.components.v1 as components

with tab7:
    st.subheader("🌧️ Mapas de Chuva em Tempo Real")
    st.markdown("<br><br>", unsafe_allow_html=True)  # Espaço extra entre os títulos

    with st.container():
        st.markdown("### 🌎 Mapa Nacional – Climatempo")
        st.markdown("<br>", unsafe_allow_html=True)
        components.iframe("https://www.climatempo.com.br/mapas/chuva-agora", height=600, scrolling=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    with st.container():
        st.markdown("### 🛰️ Radar Nacional – Tempo.com")
        st.markdown("<br>", unsafe_allow_html=True)
        components.iframe("https://www.tempo.com/radar/", height=600, scrolling=True)

with tab8:
    st.header("ℹ️ Sobre o Projeto")
    st.markdown("""
    O **Radar de Alagamentos – Araraquara, Morada do Sol** é uma iniciativa com propósito social.  
    Ele foi criado para oferecer informação acessível, visual e confiável sobre riscos de alagamento na cidade.

    ### Objetivos:
    - Proteger vidas e ajudar a população a se preparar melhor para eventos climáticos extremos  
    - Oferecer dados atualizados sobre chuva e pontos críticos  
    - Promover conscientização e prevenção

    ### Características:
    - Interface interativa com mapas e gráficos  
    - Dados em tempo real via OpenWeatherMap  
    - Informações úteis e orientações práticas

    Este projeto é gratuito, aberto e pensado para todos — especialmente para quem mais precisa.

    **Desenvolvido por Caio Rugno.**
    """)

# Rodapé
st.markdown("---")
st.caption("Desenvolvido por Caio Rugno • Dados via OpenWeatherMap • Projeto piloto para monitoramento urbano")
    
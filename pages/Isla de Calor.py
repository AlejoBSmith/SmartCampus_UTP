import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import time

st.set_page_config(layout='wide', initial_sidebar_state='expanded')
st.title("Dashboard - Isla de Calor")
st.image("https://i.ibb.co/Q3RQT66R/SMT.png", caption=".")

# ------------------- AUTOREFRESH -------------------
st_autorefresh(interval=50000, limit=None, key="refresh_counter")

# ------------------- CARGA DE DATOS -------------------
@st.cache_data(ttl=60)  # cache válido solo 60 segundos
def load_data():
    start = time.time()

    url_csv = "https://raw.githubusercontent.com/smartcampusutp/SmartCampus_UTP/refs/heads/main/Data/HISTORICO.csv"
    url_parquet = "https://raw.githubusercontent.com/smartcampusutp/SmartCampus_UTP/refs/heads/main/Data/HISTORICO.parquet"

    df = None
    try:
        df = pd.read_parquet(url_parquet)
    except:
        try:
            df = pd.read_csv(url_csv)
        except Exception as e:
            st.error(f"❌ Error cargando datos desde GitHub: {e}")
            return pd.DataFrame()

    df['time'] = pd.to_datetime(df['time'], errors='coerce')
    df = df.dropna(subset=['time'])
    st.write(f"⏱️ Tiempo de carga: {time.time()-start:.2f} s")
    return df

df = load_data()

# Filtrar solo NodoTest al inicio (si existe)
if "deviceName" in df.columns and "NodoTest" in df["deviceName"].unique():
    df = df[df["deviceName"] == "NodoTest"]

# ------------------- SIDEBAR -------------------
st.sidebar.header('Dashboard - UTP')
st.sidebar.header("Filtros")

# Filtro por sensor
if "deviceName" in df.columns and not df.empty:
    sensors = df["deviceName"].unique()
    selected_sensor = st.sidebar.selectbox("Seleccionar sensor", sensors)
    df_sensor = df[df["deviceName"] == selected_sensor]
else:
    st.sidebar.warning("⚠️ No se encontró columna 'deviceName'.")
    df_sensor = df

# Filtro por día
if not df_sensor.empty:
    min_date = df_sensor["time"].dt.date.min()
    max_date = df_sensor["time"].dt.date.max()
    selected_date = st.sidebar.date_input(
        "Seleccionar día",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
        key=f"date_{selected_sensor}"  # clave distinta por sensor
    )

    df_sensor = df_sensor[df_sensor["time"].dt.date == selected_date]

st.sidebar.markdown("---\nCreated by I2")

# ------------------- KPI -------------------
st.markdown('### Última Actualización')
col1, col2, col3 = st.columns(3)

if not df_sensor.empty:
    try:
        latest = df_sensor.loc[df_sensor['time'].idxmax()]
        col1.metric("Temperatura", f"{latest['temperature']:.2f} °C")
        col2.metric("Humedad", f"{latest['humidity']:.2f} %")
        col3.metric("Presión", f"{latest['pressure_hPa']:.0f} hPa")
    except Exception as e:
        st.warning(f"No se pudo obtener el último registro: {e}")
else:
    st.warning("No hay datos disponibles para el sensor o día seleccionado.")

# ------------------- TABLA -------------------
st.markdown("### Últimos registros (máx 500)")
if not df_sensor.empty:
    df_table = df_sensor.drop(columns=["Unnamed: 0"], errors="ignore")
    st.dataframe(df_table.tail(500).iloc[::-1], use_container_width=True)
else:
    st.info("Esperando datos...")

# ------------------- GRÁFICOS GAUGE -------------------
col1, col2 = st.columns(2)
if not df_sensor.empty:
    with col1:
        fig_temp = go.Figure(go.Indicator(
            mode="gauge+number",
            value=latest['temperature'],
            title={'text': "Temperatura (°C)"},
            gauge={
                'axis': {'range': [0, 35]},
                'bar': {'color': "red", 'thickness': 1},
                'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 30}
            }
        ))
        st.plotly_chart(fig_temp, use_container_width=True)

    with col2:
        fig_hum = go.Figure(go.Indicator(
            mode="gauge+number",
            value=latest['humidity'],
            title={'text': "Humedad (%)"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "blue", 'thickness': 1},
                'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 80}
            }
        ))
        st.plotly_chart(fig_hum, use_container_width=True)

# ------------------- GRÁFICOS DE LÍNEA -------------------
st.markdown('### Evolución temporal')

if not df_sensor.empty:
    df_plot = df_sensor.tail(5000)

    # Escalas dinámicas con margen 10%
    def dynamic_range(series, margin=0.1):
        min_val = series.min()
        max_val = series.max()
        delta = (max_val - min_val) * margin
        return min_val - delta, max_val + delta

    temp_range = dynamic_range(df_plot['temperature'])
    hum_range = dynamic_range(df_plot['humidity'])
    if "pressure_hPa" in df_plot.columns:
        pres_range = dynamic_range(df_plot['pressure_hPa'])

    # Gráfico de Temperatura
    st.subheader("📈 Evolución de la Temperatura")
    fig_temp = go.Figure()
    fig_temp.add_trace(go.Scatter(x=df_plot['time'], y=df_plot['temperature'], mode='lines', name='Temperatura'))
    fig_temp.update_layout(yaxis=dict(range=temp_range))
    st.plotly_chart(fig_temp, use_container_width=True)

    # Gráfico de Humedad
    st.subheader("💧 Evolución de la Humedad")
    fig_hum = go.Figure()
    fig_hum.add_trace(go.Scatter(x=df_plot['time'], y=df_plot['humidity'], mode='lines', name='Humedad'))
    fig_hum.update_layout(yaxis=dict(range=hum_range))
    st.plotly_chart(fig_hum, use_container_width=True)

    # Gráfico de Presión
    if "pressure_hPa" in df_plot.columns:
        st.subheader("🌡️ Evolución de la Presión")
        fig_pres = go.Figure()
        fig_pres.add_trace(go.Scatter(x=df_plot['time'], y=df_plot['pressure_hPa'], mode='lines', name='Presión'))
        fig_pres.update_layout(yaxis=dict(range=pres_range))
        st.plotly_chart(fig_pres, use_container_width=True)


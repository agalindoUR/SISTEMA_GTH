import streamlit as st
import pandas as pd
import plotly.express as px

def mostrar(dfs):
    st.title("📊 Dashboard de Desempeño y Reportes")

    # 1. Verificar si hay datos
    if "EVALUACIONES" not in dfs or dfs["EVALUACIONES"].empty:
        st.warning("Aún no hay datos de evaluaciones guardados. Ve a 'Gestión de Evaluaciones' y procesa un archivo.")
        return

    df = dfs["EVALUACIONES"]

    # --- SECCIÓN DE FILTROS ---
    st.sidebar.header("🔍 Filtros de Reporte")
    periodos = st.sidebar.multiselect("Selecciona Periodos:", df["Periodo"].unique(), default=df["Periodo"].unique())
    empleados = st.sidebar.multiselect("Filtrar por Empleado/Puesto:", df["Empleado"].unique(), default=df["Empleado"].unique())

    df_filtrado = df[(df["Periodo"].isin(periodos)) & (df["Empleado"].isin(empleados))]

    # --- INDICADORES CLAVE (METRICS) ---
    col1, col2, col3 = st.columns(3)
    promedio_era = df_filtrado["Promedio General"].mean()
    col1.metric("Promedio General", f"{promedio_era:.2f}")
    col2.metric("Total Evaluaciones", len(df_filtrado))
    col3.metric("Periodos Comparados", len(periodos))

    st.divider()

    # --- GRÁFICO 1: COMPARATIVO POR PERIODO (BARRAS AGRUPADAS) ---
    st.subheader("📈 Comparativo de Desempeño por Periodo")
    # Este gráfico es oro puro para ver quién subió o bajó su nota
    fig_barras = px.bar(
        df_filtrado, 
        x="Empleado", 
        y="Promedio General", 
        color="Periodo", 
        barmode="group",
        text_auto='.2f',
        title="Evolución de Notas por Trabajador",
        color_discrete_sequence=px.colors.qualitative.Prism
    )
    st.plotly_chart(fig_barras, use_container_width=True)

    # --- GRÁFICO 2: MAPA DE CALOR DE COMPETENCIAS ---
    st.subheader("🧩 Análisis Detallado de Competencias")
    
    # Aquí expandimos el "Formato Mágico" para verlo en el gráfico
    # Convertimos: "Responsabilidad: 4.5 | Trabajo: 4.0" en columnas reales
    detalles = []
    for _, fila in df_filtrado.iterrows():
        notas_str = fila["Notas Generales (Formato Mágico)"].split(" | ")
        d = {"Empleado": fila["Empleado"], "Periodo": fila["Periodo"]}
        for n in notas_str:
            comp, nota = n.split(": ")
            d[comp] = float(nota)
        detalles.append(d)
    
    df_detallado = pd.DataFrame(detalles)
    
    # Gráfico de Radar o Barras para un empleado específico
    emp_sel = st.selectbox("🎯 Ver detalle de competencias de:", empleados)
    df_emp = df_detallado[df_detallado["Empleado"] == emp_sel]
    
    # Derretimos el dataframe para graficar
    df_plot = df_emp.melt(id_vars=["Empleado", "Periodo"], var_name="Competencia", value_name="Nota")
    
    fig_radar = px.line_polar(
        df_plot, r="Nota", theta="Competencia", color="Periodo",
        line_close=True, range_r=[0,5],
        title=f"Fortalezas y Oportunidades: {emp_sel}"
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    # --- TABLA DE DATOS FINAL ---
    with st.expander("📂 Ver Tabla de Datos Completa"):
        st.dataframe(df_filtrado)

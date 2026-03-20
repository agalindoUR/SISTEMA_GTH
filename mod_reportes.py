import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def mostrar(dfs):
    st.markdown("<h2 style='color: #4A0000;'>📊 Dashboard de Desempeño Consolidado</h2>", unsafe_allow_html=True)

    # 1. Verificación de seguridad
    if "EVALUACIONES" not in dfs or dfs["EVALUACIONES"].empty:
        st.warning("⚠️ No se encontraron datos en 'EVALUACIONES'. Por favor, procesa y guarda un archivo en la pestaña de Gestión.")
        return

    df = dfs["EVALUACIONES"]

    # --- BARRA LATERAL DE FILTROS ---
    st.sidebar.header("🔍 Filtros de Análisis")
    
    # Filtro de Periodo
    lista_periodos = sorted(df["Periodo"].unique())
    periodos_sel = st.sidebar.multiselect("Selecciona Periodos:", lista_periodos, default=lista_periodos)
    
    # Filtro de Empleados
    lista_empleados = sorted(df["Empleado"].unique())
    empleados_sel = st.sidebar.multiselect("Selecciona Colaboradores:", lista_empleados, default=lista_empleados)

    # Aplicar Filtros
    df_filtrado = df[(df["Periodo"].isin(periodos_sel)) & (df["Empleado"].isin(empleados_sel))]

    if df_filtrado.empty:
        st.info("Selecciona al menos un periodo y un empleado para ver los resultados.")
        return

    # --- INDICADORES GENERALES (METRICS) ---
    promedio_grupal = df_filtrado["Promedio General"].mean()
    total_evals = len(df_filtrado)

    c1, c2, c3 = st.columns(3)
    c1.metric("Promedio Grupal", f"{promedio_grupal:.2f} / 5")
    c2.metric("Evaluaciones", total_evals)
    c3.metric("Mejor Puntaje", f"{df_filtrado['Promedio General'].max():.2f}")

    st.divider()

    # --- GRÁFICO 1: COMPARATIVO ENTRE PERIODOS ---
    st.subheader("📈 Comparativa de Evolución")
    fig_evolucion = px.bar(
        df_filtrado, 
        x="Empleado", 
        y="Promedio General", 
        color="Periodo", 
        barmode="group",
        text_auto='.2f',
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    st.plotly_chart(fig_evolucion, use_container_width=True)

    # --- SECCIÓN INDIVIDUAL Y DIAGNÓSTICO ---
    st.markdown("---")
    st.subheader("🎯 Análisis Individual y Diagnóstico")
    
    col_sel, col_diag = st.columns([1, 2])
    
    with col_sel:
        emp_analisis = st.selectbox("Selecciona un colaborador para diagnóstico:", empleados_sel)
        # Tomamos la evaluación más reciente del empleado seleccionado
        df_individual = df_filtrado[df_filtrado["Empleado"] == emp_analisis].iloc[-1:]
        nota_final = df_individual["Promedio General"].values[0]
        periodo_actual = df_individual["Periodo"].values[0]

        st.write(f"**Periodo analizado:** {periodo_actual}")
        st.write(f"**Puntaje Final:**")
        st.title(f"{nota_final:.2f}")

    with col_diag:
        # Lógica de Diagnóstico que te gustaba
        if nota_final >= 4.5:
            st.success("🌟 **Talento Sobresaliente:** Supera ampliamente las expectativas. Considerar para planes de sucesión o ascensos.")
        elif nota_final >= 3.5:
            st.info("✅ **Desempeño Sólido:** Cumple con las expectativas. Continuar fortaleciendo competencias específicas.")
        elif nota_final >= 2.5:
            st.warning("⚠️ **En Desarrollo:** Requiere acompañamiento y capacitación (Brecha identificada).")
        else:
            st.error("🚨 **Rendimiento Crítico:** No cumple con los requisitos. Requiere Plan de Acción Inmediato (PIP).")

    # --- GRÁFICO 2: RADAR DE COMPETENCIAS ---
    st.markdown("#### 🕸️ Mapa de Competencias")
    
    # Decodificar el "Formato Mágico" para el Radar
    try:
        notas_str = df_individual["Notas Generales (Formato Mágico)"].values[0].split(" | ")
        categorias = []
        valores = []
        for n in notas_str:
            parts = n.split(": ")
            categorias.append(parts[0])
            valores.append(float(parts[1]))

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=valores,
            theta=categorias,
            fill='toself',
            name=emp_analisis,
            line_color='#4A0000'
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
            showlegend=False
        )
        st.plotly_chart(fig_radar, use_container_width=True)
    except:
        st.error("No se pudo generar el radar. Asegúrate de que los datos tengan el formato correcto.")

    # --- TABLA DE DATOS ---
    with st.expander("📂 Ver registros históricos filtrados"):
        st.table(df_filtrado[["Empleado", "Periodo", "Promedio General"]])

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def mostrar(dfs):
    st.markdown("<h2 style='color: #4A0000;'>📊 Dashboard de Desempeño Consolidado</h2>", unsafe_allow_html=True)

    # 1. Verificación de seguridad inicial
    if "EVALUACIONES" not in dfs or dfs["EVALUACIONES"].empty:
        st.warning("⚠️ No se encontraron datos en 'EVALUACIONES'. Por favor, procesa y guarda un archivo en la pestaña de Evaluación.")
        return

    # Usamos una copia por seguridad para no alterar el dataframe original
    df = dfs.get("EVALUACIONES", pd.DataFrame()).copy()

    # MAGIA AQUÍ: Elimina espacios en blanco Y fuerza a que todo sea MAYÚSCULAS
    df.columns = df.columns.str.strip().str.upper()

    # Escudo protector: verificamos que la columna PROMEDIO GENERAL exista
    if "PROMEDIO GENERAL" in df.columns:
        # Limpiamos los números por si Google Sheets los guardó con comas o espacios
        df["PROMEDIO GENERAL"] = df["PROMEDIO GENERAL"].astype(str).str.replace(',', '.').str.strip()
        df["PROMEDIO GENERAL"] = pd.to_numeric(df["PROMEDIO GENERAL"], errors='coerce')
        df = df.dropna(subset=["PROMEDIO GENERAL"]) # Oculta filas donde no haya nota
    else:
        st.error("⚠️ Error: No se encontró la columna 'PROMEDIO GENERAL' (revisa cómo está escrita en tu Excel/Sheets).")
        return # Detiene la ejecución aquí

    # Escudo protector extra para los filtros
    if "PERIODO" not in df.columns or "NOMBRES Y APELLIDOS" not in df.columns:
        st.error("⚠️ Faltan las columnas 'PERIODO' o 'NOMBRES Y APELLIDOS' para poder filtrar los datos. Revisa los encabezados en tu hoja EVALUACIONES.")
        return

    # --- BARRA LATERAL DE FILTROS ---
    st.sidebar.header("🔍 Filtros de Análisis")
    
    # Filtro de Periodo
    lista_periodos = sorted(df["PERIODO"].dropna().unique().astype(str))
    periodos_sel = st.sidebar.multiselect("Selecciona Periodos:", lista_periodos, default=lista_periodos)
    
    # Filtro de Empleados
    lista_empleados = sorted(df["NOMBRES Y APELLIDOS"].dropna().unique().astype(str))
    empleados_sel = st.sidebar.multiselect("Selecciona Colaboradores:", lista_empleados, default=lista_empleados)

    # Aplicar Filtros
    df_filtrado = df[(df["PERIODO"].isin(periodos_sel)) & (df["NOMBRES Y APELLIDOS"].isin(empleados_sel))]

    if df_filtrado.empty:
        st.info("Selecciona al menos un periodo y un empleado en la barra lateral para ver los resultados.")
        return

    # --- INDICADORES GENERALES (METRICS) ---
    promedio_grupal = df_filtrado["PROMEDIO GENERAL"].mean()
    total_evals = len(df_filtrado)
    mejor_puntaje = df_filtrado['PROMEDIO GENERAL'].max()

    c1, c2, c3 = st.columns(3)
    c1.metric("Promedio Grupal", f"{promedio_grupal:.2f} / 5" if pd.notnull(promedio_grupal) else "0.00 / 5")
    c2.metric("Evaluaciones", total_evals)
    c3.metric("Mejor Puntaje", f"{mejor_puntaje:.2f}" if pd.notnull(mejor_puntaje) else "0.00")

    st.divider()

    # --- GRÁFICO 1: COMPARATIVO ENTRE PERIODOS ---
    st.subheader("📈 Comparativa de Evolución")
    fig_evolucion = px.bar(
        df_filtrado, 
        x="NOMBRES Y APELLIDOS", 
        y="PROMEDIO GENERAL", 
        color="PERIODO", 
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
        df_individual = df_filtrado[df_filtrado["NOMBRES Y APELLIDOS"] == emp_analisis].iloc[-1:]
        
        if not df_individual.empty:
            nota_final = df_individual["PROMEDIO GENERAL"].values[0]
            periodo_actual = df_individual["PERIODO"].values[0]

            st.write(f"**Periodo analizado:** {periodo_actual}")
            st.write(f"**Puntaje Final:**")
            st.markdown(f"<h1 style='color: #4A0000;'>{nota_final:.2f}</h1>", unsafe_allow_html=True)
        else:
            nota_final = 0

    with col_diag:
        if not df_individual.empty:
            # Lógica de Diagnóstico
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
    
    if not df_individual.empty and "NOTAS GENERALES" in df_individual.columns:
        # Decodificar el texto para el Radar (Columna NOTAS GENERALES)
        try:
            notas_str = str(df_individual["NOTAS GENERALES"].values[0])
            
            if notas_str and notas_str != "nan":
                # Cortamos el texto por los separadores " | "
                partes_notas = notas_str.split(" | ")
                categorias = []
                valores = []
                
                for n in partes_notas:
                    if ": " in n:
                        parts = n.split(": ")
                        categorias.append(parts[0].strip())
                        valores.append(float(parts[1].strip()))

                if categorias and valores:
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
                else:
                    st.warning("El formato de las notas no permite generar el radar.")
            else:
                st.info("No hay detalle de competencias registrado.")
        except Exception as e:
            st.error("No se pudo generar el radar. Revisa el formato de los datos en la columna NOTAS GENERALES.")
    elif "NOTAS GENERALES" not in df_individual.columns:
        st.info("La columna 'NOTAS GENERALES' no existe, no se puede generar el gráfico de radar.")

    # --- TABLA DE DATOS ---
    with st.expander("📂 Ver registros históricos filtrados"):
        # Mostramos unas columnas clave si existen
        cols_mostrar = ["NOMBRES Y APELLIDOS", "PERIODO", "PROMEDIO GENERAL"]
        if "AREA" in df_filtrado.columns and "CARGO" in df_filtrado.columns:
            cols_mostrar = ["NOMBRES Y APELLIDOS", "PERIODO", "AREA", "CARGO", "PROMEDIO GENERAL"]
            
        st.dataframe(df_filtrado[cols_mostrar], hide_index=True, use_container_width=True)

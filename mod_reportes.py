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

    # Usamos una copia por seguridad
    df = dfs.get("EVALUACIONES", pd.DataFrame()).copy()
    df.columns = df.columns.str.strip().str.upper()

    # Escudo protector principal
    if "PROMEDIO GENERAL" in df.columns:
        df["PROMEDIO GENERAL"] = df["PROMEDIO GENERAL"].astype(str).str.replace(',', '.').str.strip()
        df["PROMEDIO GENERAL"] = pd.to_numeric(df["PROMEDIO GENERAL"], errors='coerce')
        df = df.dropna(subset=["PROMEDIO GENERAL"])
    else:
        st.error("⚠️ Error: No se encontró la columna 'PROMEDIO GENERAL'.")
        return

    # Asegurar que existan columnas clave para evitar errores
    if "PERIODO" not in df.columns or "NOMBRES Y APELLIDOS" not in df.columns:
        st.error("⚠️ Faltan las columnas 'PERIODO' o 'NOMBRES Y APELLIDOS'.")
        return
        
    if "AREA" not in df.columns: df["AREA"] = "No registrada"
    if "CARGO" not in df.columns: df["CARGO"] = "No registrado"

    # --- BARRA LATERAL DE FILTROS (EN CASCADA) ---
    st.sidebar.header("🔍 Filtros Dinámicos")
    
    lista_periodos = sorted(df["PERIODO"].dropna().unique().astype(str))
    periodos_sel = st.sidebar.multiselect("1. Periodos:", lista_periodos, default=lista_periodos)
    
    lista_areas = sorted(df["AREA"].dropna().unique().astype(str))
    areas_sel = st.sidebar.multiselect("2. Áreas:", lista_areas, default=lista_areas)
    
    lista_cargos = sorted(df["CARGO"].dropna().unique().astype(str))
    cargos_sel = st.sidebar.multiselect("3. Cargos / Puestos:", lista_cargos, default=lista_cargos)

    # Pre-filtro para actualizar la lista de empleados
    df_temp = df[(df["PERIODO"].isin(periodos_sel)) & 
                 (df["AREA"].isin(areas_sel)) & 
                 (df["CARGO"].isin(cargos_sel))]

    lista_empleados = sorted(df_temp["NOMBRES Y APELLIDOS"].dropna().unique().astype(str))
    empleados_sel = st.sidebar.multiselect("4. Colaboradores:", lista_empleados, default=lista_empleados)

    # Filtro Final
    df_filtrado = df_temp[df_temp["NOMBRES Y APELLIDOS"].isin(empleados_sel)]

    if df_filtrado.empty:
        st.info("👆 Usa los filtros de la barra lateral para explorar los datos.")
        return

    # --- INDICADORES GENERALES ---
    promedio_grupal = df_filtrado["PROMEDIO GENERAL"].mean()
    total_evals = len(df_filtrado)
    mejor_puntaje = df_filtrado['PROMEDIO GENERAL'].max()

    c1, c2, c3 = st.columns(3)
    c1.metric("Promedio Global (Filtro)", f"{promedio_grupal:.2f} / 5" if pd.notnull(promedio_grupal) else "0.00 / 5")
    c2.metric("Total Evaluaciones (Filtro)", total_evals)
    c3.metric("Pico Máximo", f"{mejor_puntaje:.2f}" if pd.notnull(mejor_puntaje) else "0.00")

    st.divider()

    # --- GRÁFICO 1: COMPARATIVO DINÁMICO ---
    st.subheader("📈 Análisis Comparativo y Evolución")
    
    # Selector de tipo de comparación
    tipo_comparacion = st.radio("Agrupar métricas por:", ["Colaborador", "Área", "Cargo"], horizontal=True)
    
    col_agrupacion = "NOMBRES Y APELLIDOS" if tipo_comparacion == "Colaborador" else ("AREA" if tipo_comparacion == "Área" else "CARGO")
    
    # Agrupamos y promediamos para que el gráfico sea exacto
    df_grafico = df_filtrado.groupby([col_agrupacion, "PERIODO"])["PROMEDIO GENERAL"].mean().reset_index()
    
    fig_evolucion = px.bar(
        df_grafico, 
        x=col_agrupacion, 
        y="PROMEDIO GENERAL", 
        color="PERIODO", 
        barmode="group",
        text_auto='.2f',
        color_discrete_sequence=px.colors.qualitative.Bold,
        title=f"Promedio de Evaluación por {tipo_comparacion}"
    )
    st.plotly_chart(fig_evolucion, use_container_width=True)

    # --- NUEVA SECCIÓN: RANKINGS ---
    st.markdown("---")
    st.subheader("🏆 Rankings Destacados")
    r1, r2 = st.columns(2)
    
    with r1:
        st.markdown("**Top 5: Mejores Colaboradores (Promedio histórico)**")
        df_top_emp = df_filtrado.groupby("NOMBRES Y APELLIDOS")["PROMEDIO GENERAL"].mean().reset_index()
        df_top_emp = df_top_emp.sort_values(by="PROMEDIO GENERAL", ascending=False).head(5)
        fig_top = px.bar(df_top_emp, y="NOMBRES Y APELLIDOS", x="PROMEDIO GENERAL", orientation='h', text_auto='.2f', color="PROMEDIO GENERAL", color_continuous_scale="Reds")
        fig_top.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False, margin=dict(l=0, r=0, t=0, b=0), height=250)
        st.plotly_chart(fig_top, use_container_width=True)
        
    with r2:
        st.markdown("**Desempeño por Áreas**")
        df_top_area = df_filtrado.groupby("AREA")["PROMEDIO GENERAL"].mean().reset_index()
        df_top_area = df_top_area.sort_values(by="PROMEDIO GENERAL", ascending=False)
        fig_area = px.bar(df_top_area, x="AREA", y="PROMEDIO GENERAL", text_auto='.2f', color="AREA", color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_area.update_layout(showlegend=False, margin=dict(l=0, r=0, t=0, b=0), height=250)
        st.plotly_chart(fig_area, use_container_width=True)

    # --- SECCIÓN INDIVIDUAL Y DIAGNÓSTICO (MEJORADA) ---
    st.markdown("---")
    st.subheader("🎯 Análisis Individual: Histórico Promediado")
    
    col_sel, col_diag = st.columns([1, 2])
    
    with col_sel:
        emp_analisis = st.selectbox("Selecciona un colaborador para diagnóstico profundo:", empleados_sel)
        # Obtenemos TODAS las evaluaciones del empleado seleccionado
        df_individual = df_filtrado[df_filtrado["NOMBRES Y APELLIDOS"] == emp_analisis]
        
        if not df_individual.empty:
            nota_promedio_final = df_individual["PROMEDIO GENERAL"].mean()
            evaluaciones_contadas = len(df_individual)

            st.write(f"**Evaluaciones analizadas:** {evaluaciones_contadas}")
            st.write(f"**Puntaje Promedio:**")
            st.markdown(f"<h1 style='color: #4A0000;'>{nota_promedio_final:.2f}</h1>", unsafe_allow_html=True)
        else:
            nota_promedio_final = 0

    with col_diag:
        if not df_individual.empty:
            if nota_promedio_final >= 4.5:
                st.success("🌟 **Talento Sobresaliente:** Supera ampliamente las expectativas en su histórico. Perfil ideal para liderazgo o ascensos.")
            elif nota_promedio_final >= 3.5:
                st.info("✅ **Desempeño Sólido:** Cumple consistentemente con las expectativas. Mantener planes de fidelización.")
            elif nota_promedio_final >= 2.5:
                st.warning("⚠️ **En Desarrollo / Fluctuante:** Requiere acompañamiento y capacitación (Identificar brechas en el mapa de competencias).")
            else:
                st.error("🚨 **Rendimiento Crítico:** Histórico por debajo de los requisitos. Requiere Plan de Acción Inmediato (PIP).")

    # --- GRÁFICO 2: RADAR DE COMPETENCIAS PROMEDIADAS ---
    if not df_individual.empty and "NOTAS GENERALES" in df_individual.columns:
        st.markdown("#### 🕸️ Mapa de Competencias y Comentarios")
        
        # Diccionario para sumar y promediar las competencias de todas las evaluaciones
        dic_competencias = {}
        
        for notas_str in df_individual["NOTAS GENERALES"].dropna():
            if str(notas_str) != "nan":
                partes_notas = str(notas_str).split(" | ")
                for n in partes_notas:
                    if ": " in n:
                        parts = n.split(": ")
                        cat = parts[0].strip()
                        try:
                            val = float(parts[1].strip())
                            if cat not in dic_competencias:
                                dic_competencias[cat] = []
                            dic_competencias[cat].append(val)
                        except:
                            pass

        if dic_competencias:
            categorias = []
            valores = []
            
            # Promediamos cada competencia
            for cat, lista_vals in dic_competencias.items():
                avg_val = sum(lista_vals) / len(lista_vals)
                categorias.append(cat)
                valores.append(avg_val)
                
            col_radar, col_comentarios = st.columns([1.5, 1])
            
            with col_radar:
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=valores, theta=categorias, fill='toself', name=emp_analisis, line_color='#4A0000'
                ))
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False, margin=dict(l=40, r=40, t=20, b=20))
                st.plotly_chart(fig_radar, use_container_width=True)
                
            with col_comentarios:
                st.markdown("**Evaluación por Competencia:**")
                for cat, val in zip(categorias, valores):
                    if val >= 4.5: estado = "🟢 Fortaleza"
                    elif val >= 3.5: estado = "🟡 Adecuado"
                    else: estado = "🔴 A mejorar"
                    st.write(f"- **{cat}:** {val:.2f} ({estado})")
        else:
            st.info("No hay detalle de competencias registrado para este colaborador.")

    # --- TABLA DE DATOS ---
    with st.expander("📂 Ver registros históricos detallados"):
        cols_mostrar = ["NOMBRES Y APELLIDOS", "PERIODO", "AREA", "CARGO", "PROMEDIO GENERAL", "TIPO DE EVALUACION"]
        # Filtrar solo columnas que realmente existan en el df para no generar errores
        cols_finales = [c for c in cols_mostrar if c in df_filtrado.columns]
        st.dataframe(df_filtrado[cols_finales], hide_index=True, use_container_width=True)

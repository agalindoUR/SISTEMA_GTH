import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- Función auxiliar para procesar competencias ---
def obtener_promedios_competencias(df_subset):
    dic_competencias = {}
    if "NOTAS GENERALES" in df_subset.columns:
        for notas_str in df_subset["NOTAS GENERALES"].dropna():
            if str(notas_str).strip() != "nan" and str(notas_str).strip() != "":
                partes_notas = str(notas_str).split(" | ")
                for n in partes_notas:
                    if ": " in n:
                        try:
                            cat, val = n.split(": ")
                            cat = cat.strip()
                            val = float(val.strip())
                            if cat not in dic_competencias:
                                dic_competencias[cat] = []
                            dic_competencias[cat].append(val)
                        except:
                            pass
    return {k: sum(v)/len(v) for k, v in dic_competencias.items()}

def mostrar(dfs):
    st.markdown("<h2 style='color: #FFD700;'>📊 Dashboard de Desempeño Consolidado</h2>", unsafe_allow_html=True)

    if "EVALUACIONES" not in dfs or dfs["EVALUACIONES"].empty:
        st.warning("⚠️ No se encontraron datos en 'EVALUACIONES'. Por favor, sube y procesa un archivo en la pestaña de Evaluaciones.")
        return

    df = dfs.get("EVALUACIONES", pd.DataFrame()).copy()
    df.columns = [str(c).strip().upper() for c in df.columns]

    if "PROMEDIO GENERAL" in df.columns:
        df["PROMEDIO GENERAL"] = df["PROMEDIO GENERAL"].astype(str).str.replace(',', '.').str.strip()
        df["PROMEDIO GENERAL"] = pd.to_numeric(df["PROMEDIO GENERAL"], errors='coerce')
        df = df.dropna(subset=["PROMEDIO GENERAL"])
    else:
        st.error(f"⚠️ Error: No se encontró 'PROMEDIO GENERAL'. Columnas detectadas: {list(df.columns)}")
        return

    if "PERIODO" not in df.columns or "NOMBRES Y APELLIDOS" not in df.columns:
        st.error("⚠️ Faltan las columnas 'PERIODO' o 'NOMBRES Y APELLIDOS'.")
        return
        
    if "AREA" not in df.columns: df["AREA"] = "No registrada"
    if "CARGO" not in df.columns: df["CARGO"] = "No registrado"

    # --- BARRA LATERAL DE FILTROS ---
    st.sidebar.header("🔍 Filtros Dinámicos")
    lista_periodos = sorted(df["PERIODO"].dropna().unique().astype(str))
    periodos_sel = st.sidebar.multiselect("1. Periodos:", lista_periodos, default=lista_periodos)
    
    lista_areas = sorted(df["AREA"].dropna().unique().astype(str))
    areas_sel = st.sidebar.multiselect("2. Áreas:", lista_areas, default=lista_areas)
    
    lista_cargos = sorted(df["CARGO"].dropna().unique().astype(str))
    cargos_sel = st.sidebar.multiselect("3. Cargos / Puestos:", lista_cargos, default=lista_cargos)

    df_temp = df[(df["PERIODO"].isin(periodos_sel)) & 
                 (df["AREA"].isin(areas_sel)) & 
                 (df["CARGO"].isin(cargos_sel))]

    lista_empleados = sorted(df_temp["NOMBRES Y APELLIDOS"].dropna().unique().astype(str))
    empleados_sel = st.sidebar.multiselect("4. Colaboradores:", lista_empleados, default=lista_empleados)

    df_filtrado = df_temp[df_temp["NOMBRES Y APELLIDOS"].isin(empleados_sel)]

    if df_filtrado.empty:
        st.info("👆 Usa los filtros de la barra lateral para explorar los datos.")
        return

    # --- INDICADORES GENERALES ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Promedio Global (Filtro)", f"{df_filtrado['PROMEDIO GENERAL'].mean():.2f} / 5")
    c2.metric("Total Evaluaciones (Filtro)", len(df_filtrado))
    c3.metric("Pico Máximo", f"{df_filtrado['PROMEDIO GENERAL'].max():.2f}")
    st.divider()

    # --- GRÁFICO 1: EVOLUCIÓN GENERAL ---
    st.subheader("📈 Análisis Histórico General")
    tipo_comparacion = st.radio("Agrupar métricas por:", ["Colaborador", "Área", "Cargo"], horizontal=True)
    col_agrupacion = "NOMBRES Y APELLIDOS" if tipo_comparacion == "Colaborador" else ("AREA" if tipo_comparacion == "Área" else "CARGO")
    
    df_grafico = df_filtrado.groupby([col_agrupacion, "PERIODO"])["PROMEDIO GENERAL"].mean().reset_index()
    fig_evolucion = px.bar(df_grafico, x=col_agrupacion, y="PROMEDIO GENERAL", color="PERIODO", barmode="group", text_auto='.2f', color_discrete_sequence=px.colors.qualitative.Bold)
    st.plotly_chart(fig_evolucion, use_container_width=True)

    # --- COMPARATIVA DIRECTA (CARA A CARA) ---
    st.markdown("---")
    st.subheader("⚖️ Comparativa Directa (Cara a Cara)")
    st.write("Selecciona entidades específicas para analizar sus diferencias en cada competencia.")
    
    modo_vs = st.radio("¿Qué deseas comparar?", ["Colaborador vs Colaborador", "Área vs Área"], horizontal=True)
    
    if "Colaborador" in modo_vs:
        opciones_vs = lista_empleados
        col_vs = "NOMBRES Y APELLIDOS"
    else:
        opciones_vs = lista_areas
        col_vs = "AREA"

    seleccionados_vs = st.multiselect(f"Selecciona (máx 3 recomendados):", opciones_vs, max_selections=4)

    if len(seleccionados_vs) >= 2:
        col_graf_vs, col_txt_vs = st.columns([1.5, 1])
        
        datos_radar = []
        dic_promedios_entidades = {}
        todas_las_competencias = set()

        # Procesar datos de los seleccionados
        for entidad in seleccionados_vs:
            df_entidad = df_filtrado[df_filtrado[col_vs] == entidad]
            promedios_comp = obtener_promedios_competencias(df_entidad)
            dic_promedios_entidades[entidad] = promedios_comp
            
            for comp, val in promedios_comp.items():
                datos_radar.append({"Entidad": entidad, "Competencia": comp, "Puntaje": val})
                todas_las_competencias.add(comp)

        with col_graf_vs:
            if datos_radar:
                df_radar = pd.DataFrame(datos_radar)
                fig_vs = px.line_polar(df_radar, r="Puntaje", theta="Competencia", color="Entidad", line_close=True, markers=True)
                fig_vs.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 5])), 
                    margin=dict(l=40, r=40, t=20, b=20),
                    paper_bgcolor="rgba(0,0,0,0)", # Fondo transparente
                    plot_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig_vs, use_container_width=True)

        with col_txt_vs:
            # MAGIA VISUAL: Caja con fondo oscuro semi-transparente y texto claro
            html_analisis = """
            <div style='background-color: rgba(0, 0, 0, 0.4); padding: 20px; border-radius: 10px; border-left: 5px solid #FFD700; color: #FFFFFF;'>
                <h4 style='color: #FFD700; margin-top: 0; font-family: sans-serif;'>💡 Conclusión Analítica</h4>
            """
            
            # MAGIA ANALÍTICA: Evaluar competencia por competencia
            for comp in sorted(list(todas_las_competencias)):
                puntajes_comp = []
                for entidad, promedios in dic_promedios_entidades.items():
                    if comp in promedios:
                        puntajes_comp.append({"entidad": entidad, "puntaje": promedios[comp]})
                
                if len(puntajes_comp) > 1:
                    # Ordenar de mayor a menor
                    puntajes_comp_ordenados = sorted(puntajes_comp, key=lambda x: x["puntaje"], reverse=True)
                    ganador = puntajes_comp_ordenados[0]
                    ultimo = puntajes_comp_ordenados[-1]
                    
                    diferencia = ganador["puntaje"] - ultimo["puntaje"]
                    
                    html_analisis += f"<div style='margin-bottom: 12px;'><b style='color: #FFFFAA;'>{comp}:</b><br>"
                    
                    if diferencia <= 0.2:
                        html_analisis += f"🤝 <i>Empate técnico.</i> Todas las partes promedian de forma muy similar (Aprox. {ganador['puntaje']:.2f})."
                    else:
                        html_analisis += f"🏆 <b>{ganador['entidad']}</b> lidera con <b>{ganador['puntaje']:.2f}</b>. "
                        if len(puntajes_comp_ordenados) > 2:
                            html_analisis += f"Por otro lado, <b>{ultimo['entidad']}</b> presenta la mayor oportunidad de mejora ({ultimo['puntaje']:.2f})."
                        else:
                            html_analisis += f"Superando a <b>{ultimo['entidad']}</b> ({ultimo['puntaje']:.2f})."
                    
                    html_analisis += "</div>"

            html_analisis += "</div>"
            
            # Mostrar el HTML renderizado
            st.markdown(html_analisis, unsafe_allow_html=True)

    elif len(seleccionados_vs) == 1:
        st.info("Selecciona al menos 2 opciones para iniciar la comparativa.")

    # --- RANKINGS AVANZADOS (NUEVA SECCIÓN REEMPLAZADA) ---
    st.markdown("---")
    st.subheader("🏆 Rankings de Desempeño")

    # Filtros de Ranking
    col1, col2 = st.columns([1, 1])
    with col1:
        modo_orden = st.radio("Ordenar por puntaje:", ["Mayor a Menor (Top 🏆)", "Menor a Mayor (Mejora 📈)"], horizontal=True)
        es_ascendente = True if "Menor" in modo_orden else False
    
    with col2:
        col_tipo = "TIPO DE TRABAJADORA" if "TIPO DE TRABAJADORA" in df.columns else ("TIPO DE EVALUACION" if "TIPO DE EVALUACION" in df.columns else None)
        filtro_tipo = ["Todos"]
        if col_tipo:
            filtro_tipo += sorted(df[col_tipo].dropna().unique().tolist())
        tipo_sel = st.selectbox("Filtrar por tipo de colaborador:", filtro_tipo)

    # Aplicar filtros al DF de ranking
    df_rank = df_filtrado.copy()
    if tipo_sel != "Todos" and col_tipo:
        df_rank = df_rank[df_rank[col_tipo] == tipo_sel]

    # Agrupar para tener un solo valor por persona/área
    df_rank_emp = df_rank.groupby("NOMBRES Y APELLIDOS")["PROMEDIO GENERAL"].mean().reset_index()
    df_rank_emp = df_rank_emp.sort_values(by="PROMEDIO GENERAL", ascending=es_ascendente)
    
    df_rank_area = df_rank.groupby("AREA")["PROMEDIO GENERAL"].mean().reset_index()
    df_rank_area = df_rank_area.sort_values(by="PROMEDIO GENERAL", ascending=es_ascendente)

    # Configuración de Colores (Semáforo 1 al 5)
    color_scale = [
        [0.0, "rgb(200, 0, 0)"],   # Rojo
        [0.5, "rgb(255, 255, 0)"], # Amarillo
        [1.0, "rgb(0, 150, 0)"]    # Verde
    ]

    tab1, tab2 = st.tabs(["👤 Ranking de Colaboradores", "🏢 Ranking por Áreas"])

    with tab1:
        st.write(f"Mostrando {len(df_rank_emp)} colaboradores. Si la lista es larga, usa la barra de desplazamiento a la derecha del gráfico.")
        altura_dinamica = max(400, len(df_rank_emp) * 25)
        
        fig_emp = px.bar(
            df_rank_emp, 
            x="PROMEDIO GENERAL", 
            y="NOMBRES Y APELLIDOS",
            orientation='h',
            text="PROMEDIO GENERAL",
            color="PROMEDIO GENERAL",
            color_continuous_scale=color_scale,
            range_color=[1, 5], 
            labels={"PROMEDIO GENERAL": "Puntaje", "NOMBRES Y APELLIDOS": "Colaborador"}
        )
        fig_emp.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig_emp.update_layout(
            height=altura_dinamica, 
            yaxis={'categoryorder':'total ascending' if es_ascendente else 'total descending'},
            coloraxis_showscale=False,
            margin=dict(l=200, r=40, t=20, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_emp, use_container_width=True)

    with tab2:
        altura_area = max(400, len(df_rank_area) * 35)
        fig_area = px.bar(
            df_rank_area, 
            x="PROMEDIO GENERAL", 
            y="AREA",
            orientation='h',
            text="PROMEDIO GENERAL",
            color="PROMEDIO GENERAL",
            color_continuous_scale=color_scale,
            range_color=[1, 5],
            labels={"PROMEDIO GENERAL": "Puntaje", "AREA": "Área"}
        )
        fig_area.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig_area.update_layout(
            height=altura_area, 
            yaxis={'categoryorder':'total ascending' if es_ascendente else 'total descending'},
            coloraxis_showscale=False,
            margin=dict(l=200, r=40, t=20, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_area, use_container_width=True)


    # --- ANÁLISIS INDIVIDUAL PROFUNDO ---
    st.markdown("---")
    st.subheader("🎯 Análisis Individual Profundo")
    col_sel, col_diag = st.columns([1, 2])
    
    with col_sel:
        emp_analisis = st.selectbox("Selecciona un colaborador para diagnóstico:", empleados_sel)
        df_individual = df_filtrado[df_filtrado["NOMBRES Y APELLIDOS"] == emp_analisis]
        if not df_individual.empty:
            st.markdown(f"**Puntaje Promedio Histórico:** <h1 style='color: #FFD700;'>{df_individual['PROMEDIO GENERAL'].mean():.2f}</h1>", unsafe_allow_html=True)

    with col_diag:
        if not df_individual.empty:
            nota = df_individual["PROMEDIO GENERAL"].mean()
            if nota >= 4.5: st.success("🌟 **Sobresaliente:** Perfil ideal para liderazgo o ascensos.")
            elif nota >= 3.5: st.info("✅ **Sólido:** Cumple consistentemente.")
            elif nota >= 2.5: st.warning("⚠️ **En Desarrollo:** Requiere capacitación.")
            else: st.error("🚨 **Crítico:** Requiere Plan de Acción Inmediato (PIP).")

    if not df_individual.empty:
        promedios_ind = obtener_promedios_competencias(df_individual)
        if promedios_ind:
            col_radar, col_comentarios = st.columns([1.5, 1])
            with col_radar:
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(r=list(promedios_ind.values()), theta=list(promedios_ind.keys()), fill='toself', name=emp_analisis, line_color='#FFD700'))
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False, margin=dict(l=40, r=40, t=20, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_radar, use_container_width=True)
            with col_comentarios:
                st.markdown("**Desglose:**")
                for cat, val in promedios_ind.items():
                    estado = "🟢 Fuerte" if val >= 4.5 else ("🟡 Medio" if val >= 3.5 else "🔴 Bajo")
                    st.write(f"- **{cat}:** {val:.2f} ({estado})")

    with st.expander("📂 Ver registros históricos detallados"):
        cols_mostrar = ["NOMBRES Y APELLIDOS", "PERIODO", "AREA", "CARGO", "PROMEDIO GENERAL", "TIPO DE EVALUACION", "TIPO DE TRABAJADORA"]
        st.dataframe(df_filtrado[[c for c in cols_mostrar if c in df_filtrado.columns]], hide_index=True, use_container_width=True)

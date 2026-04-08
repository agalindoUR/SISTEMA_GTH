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
    # Retornar diccionario con promedios
    return {k: sum(v)/len(v) for k, v in dic_competencias.items()}

def mostrar(dfs):
    st.markdown("<h2 style='color: #4A0000;'>📊 Dashboard de Desempeño Consolidado</h2>", unsafe_allow_html=True)

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

    # --- NUEVO: COMPARATIVA DIRECTA (CARA A CARA) ---
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

        # Procesar datos de los seleccionados
        for entidad in seleccionados_vs:
            df_entidad = df_filtrado[df_filtrado[col_vs] == entidad]
            promedios_comp = obtener_promedios_competencias(df_entidad)
            dic_promedios_entidades[entidad] = promedios_comp
            
            for comp, val in promedios_comp.items():
                datos_radar.append({"Entidad": entidad, "Competencia": comp, "Puntaje": val})

        with col_graf_vs:
            if datos_radar:
                df_radar = pd.DataFrame(datos_radar)
                fig_vs = px.line_polar(df_radar, r="Puntaje", theta="Competencia", color="Entidad", line_close=True, markers=True, template="plotly_white")
                fig_vs.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), margin=dict(l=40, r=40, t=20, b=20))
                st.plotly_chart(fig_vs, use_container_width=True)
            else:
                st.info("No hay detalles de competencias para graficar.")

        with col_txt_vs:
            st.markdown("#### 💡 Conclusión del Análisis")
            if len(seleccionados_vs) == 2:
                ent_A, ent_B = seleccionados_vs[0], seleccionados_vs[1]
                comps_A = dic_promedios_entidades[ent_A]
                comps_B = dic_promedios_entidades[ent_B]
                
                comentarios = []
                for comp in set(comps_A.keys()).intersection(set(comps_B.keys())):
                    valA = comps_A[comp]
                    valB = comps_B[comp]
                    diff = valA - valB
                    
                    if diff >= 0.4:
                        comentarios.append(f"🟢 **{ent_A}** supera claramente a {ent_B} en **{comp}** ({valA:.2f} vs {valB:.2f}).")
                    elif diff <= -0.4:
                        comentarios.append(f"🔴 **{ent_B}** es superior en **{comp}** ({valB:.2f} vs {valA:.2f}).")
                    else:
                        comentarios.append(f"⚪ Nivel muy parejo en **{comp}** (Aprox. {valA:.2f}).")
                
                for c in comentarios:
                    st.write(c)
            else:
                st.write(f"Comparando {len(seleccionados_vs)} entidades. Revisa el gráfico de radar para identificar visualmente quién abarca mayor área en cada competencia.")

    elif len(seleccionados_vs) == 1:
        st.info("Selecciona al menos 2 opciones para iniciar la comparativa.")

    # --- RANKINGS ---
    st.markdown("---")
    st.subheader("🏆 Rankings Destacados")
    r1, r2 = st.columns(2)
    with r1:
        st.markdown("**Top Mejores Colaboradores**")
        df_top_emp = df_filtrado.groupby("NOMBRES Y APELLIDOS")["PROMEDIO GENERAL"].mean().reset_index().sort_values(by="PROMEDIO GENERAL", ascending=False).head(5)
        fig_top = px.bar(df_top_emp, y="NOMBRES Y APELLIDOS", x="PROMEDIO GENERAL", orientation='h', text_auto='.2f', color="PROMEDIO GENERAL", color_continuous_scale="Reds")
        fig_top.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False, margin=dict(l=0, r=0, t=0, b=0), height=250)
        st.plotly_chart(fig_top, use_container_width=True)
    with r2:
        st.markdown("**Desempeño por Áreas**")
        df_top_area = df_filtrado.groupby("AREA")["PROMEDIO GENERAL"].mean().reset_index().sort_values(by="PROMEDIO GENERAL", ascending=False)
        fig_area = px.bar(df_top_area, x="AREA", y="PROMEDIO GENERAL", text_auto='.2f', color="AREA", color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_area.update_layout(showlegend=False, margin=dict(l=0, r=0, t=0, b=0), height=250)
        st.plotly_chart(fig_area, use_container_width=True)

    # --- ANÁLISIS INDIVIDUAL PROFUNDO ---
    st.markdown("---")
    st.subheader("🎯 Análisis Individual Profundo")
    col_sel, col_diag = st.columns([1, 2])
    
    with col_sel:
        emp_analisis = st.selectbox("Selecciona un colaborador:", empleados_sel)
        df_individual = df_filtrado[df_filtrado["NOMBRES Y APELLIDOS"] == emp_analisis]
        if not df_individual.empty:
            st.markdown(f"**Puntaje Promedio Histórico:** <h1 style='color: #4A0000;'>{df_individual['PROMEDIO GENERAL'].mean():.2f}</h1>", unsafe_allow_html=True)

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
                fig_radar.add_trace(go.Scatterpolar(r=list(promedios_ind.values()), theta=list(promedios_ind.keys()), fill='toself', name=emp_analisis, line_color='#4A0000'))
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False, margin=dict(l=40, r=40, t=20, b=20))
                st.plotly_chart(fig_radar, use_container_width=True)
            with col_comentarios:
                st.markdown("**Desglose:**")
                for cat, val in promedios_ind.items():
                    estado = "🟢 Fuerte" if val >= 4.5 else ("🟡 Medio" if val >= 3.5 else "🔴 Bajo")
                    st.write(f"- **{cat}:** {val:.2f} ({estado})")

    with st.expander("📂 Ver registros históricos detallados"):
        cols_mostrar = ["NOMBRES Y APELLIDOS", "PERIODO", "AREA", "CARGO", "PROMEDIO GENERAL", "TIPO DE EVALUACION"]
        st.dataframe(df_filtrado[[c for c in cols_mostrar if c in df_filtrado.columns]], hide_index=True, use_container_width=True)

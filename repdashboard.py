# ==========================================
# MÓDULO: DASHBOARD DE DESEMPEÑO
# ==========================================
import streamlit as st
import pandas as pd

def mostrar(dfs):
    st.markdown("<h2 style='color: #FFD700; text-align: center;'>📈 Dashboard de Evaluación de Desempeño</h2>", unsafe_allow_html=True)
    
    # Cargamos la data de evaluaciones
    df_evals = dfs.get("EVALUACIONES", pd.DataFrame())
    
    if df_evals.empty:
        st.warning("Aún no hay evaluaciones registradas en el sistema.")
    else:
        # Selector de colaborador a analizar
        lista_evaluados = df_evals["apellidos y nombres"].unique()
        empleado_sel = st.selectbox("🔍 Selecciona un colaborador para ver sus resultados:", lista_evaluados)
        
        # Filtramos los datos de ese empleado (tomamos la evaluación más reciente)
        datos_emp = df_evals[df_evals["apellidos y nombres"] == empleado_sel].iloc[-1]
        
        st.markdown(f"### 👤 {empleado_sel}")
        st.caption(f"Puesto evaluado: **{datos_emp.get('puesto evaluado', '-')}** | Evaluador: **{datos_emp.get('evaluador', '-')}** | Fecha: **{datos_emp.get('fecha', '-')}**")
        
        # Función para decodificar notas
        def decodificar_notas(texto):
            if pd.isna(texto) or str(texto).strip() == "": return {}
            diccionario = {}
            items = str(texto).split("|")
            for item in items:
                if ":" in item:
                    clave, valor = item.split(":")
                    try:
                        diccionario[clave.strip()] = float(valor.strip())
                    except:
                        diccionario[clave.strip()] = 0.0
            return diccionario

        notas_gen = decodificar_notas(datos_emp.get("notas generales", ""))
        notas_esp = decodificar_notas(datos_emp.get("notas especificas", ""))
        notas_kpi = decodificar_notas(datos_emp.get("notas kpis", ""))
        
        # CREAMOS LAS 4 PESTAÑAS
        tab1, tab2, tab3, tab4 = st.tabs(["🧠 C. Generales", "🛠️ C. Específicas", "📈 KPIs", "📊 Consolidado"])
        
        with tab1:
            st.markdown("<h4 style='color: #FFD700;'>Evaluación de Competencias Generales</h4>", unsafe_allow_html=True)
            if not notas_gen:
                st.info("No hay datos de competencias generales.")
            else:
                for comp, nota in notas_gen.items():
                    porcentaje = int((nota / 5.0) * 100)
                    st.write(f"**{comp}** - Nota: {nota}/5")
                    st.progress(porcentaje)
                    
        with tab2:
            st.markdown("<h4 style='color: #FF8C00;'>Evaluación de Competencias Específicas</h4>", unsafe_allow_html=True)
            if not notas_esp:
                st.info("No hay datos de competencias específicas.")
            else:
                for comp, nota in notas_esp.items():
                    porcentaje = int((nota / 5.0) * 100)
                    st.write(f"**{comp}** - Nota: {nota}/5")
                    st.progress(porcentaje)
                    
        with tab3:
            st.markdown("<h4 style='color: #00E5FF;'>Indicadores de Desempeño (KPIs)</h4>", unsafe_allow_html=True)
            if not notas_kpi:
                st.info("No hay datos de KPIs.")
            else:
                for kpi, nota in notas_kpi.items():
                    porcentaje = int((nota / 5.0) * 100)
                    st.write(f"**{kpi}** - Nivel de logro: {nota}/5")
                    st.progress(porcentaje)
                    
        with tab4:
            st.markdown("#### 📊 Resumen Ejecutivo")
            prom_gen = sum(notas_gen.values())/len(notas_gen) if notas_gen else 0
            prom_esp = sum(notas_esp.values())/len(notas_esp) if notas_esp else 0
            prom_kpi = sum(notas_kpi.values())/len(notas_kpi) if notas_kpi else 0
            
            try:
                prom_total = float(datos_emp.get("promedio", 0))
            except:
                prom_total = 0.0
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Promedio General", f"{prom_total}/5")
            c2.metric("Comp. Generales", f"{prom_gen:.1f}/5")
            c3.metric("Comp. Específicas", f"{prom_esp:.1f}/5")
            c4.metric("Desempeño (KPIs)", f"{prom_kpi:.1f}/5")
            
            st.divider()
            
            st.markdown("#### 🎯 Diagnóstico:")
            if prom_total >= 4.5:
                st.success("🌟 **Talento Sobresaliente:** Supera ampliamente las expectativas del puesto. Considerar para planes de sucesión o ascensos.")
            elif prom_total >= 3.5:
                st.info("✅ **Desempeño Sólido:** Cumple con las expectativas del puesto. Continuar fortaleciendo competencias específicas.")
            elif prom_total >= 2.5:
                st.warning("⚠️ **En Desarrollo:** Requiere acompañamiento y capacitación (Brecha identificada).")
            else:
                st.error("🚨 **Rendimiento Crítico:** No cumple con los requisitos del puesto. Requiere Plan de Acción Inmediato (PIP).")

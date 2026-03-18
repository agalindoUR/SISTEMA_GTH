# ==========================================
# MÓDULO: ESTRUCTURA Y PUESTOS (MOF)
# ==========================================
import streamlit as st
import pandas as pd

def mostrar(dfs):
    st.markdown("<h2 style='color: #FFD700; text-align: center; margin-bottom: 20px;'>🏢 Directorio de Perfiles y Puestos (MOF)</h2>", unsafe_allow_html=True)
    
    df_puestos = dfs.get("ESTRUCTURA_PUESTOS", pd.DataFrame())
    
    if df_puestos.empty:
        st.warning("No hay datos en la hoja 'ESTRUCTURA_PUESTOS' de Google Sheets.")
    else:
        col_puesto = "puesto"
        col_area = "area"
        col_reporta = "reporta a"
        
        puesto_sel = st.selectbox("🔍 Selecciona el puesto que deseas consultar:", df_puestos[col_puesto].unique())
        datos_puesto = df_puestos[df_puestos[col_puesto] == puesto_sel].iloc[0]
        
        # Encabezado principal del puesto
        st.markdown(f"""
            <div style='background: linear-gradient(90deg, #1A1A1A 0%, #2D2D2D 100%); padding: 25px; border-radius: 15px; border-left: 8px solid #FFD700; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 25px;'>
                <h2 style='color: #FFD700; margin-top:0; font-size: 28px;'>{puesto_sel}</h2>
                <div style='display: flex; gap: 20px; flex-wrap: wrap;'>
                    <span style='background-color: #333; padding: 5px 15px; border-radius: 20px; color: white; border: 1px solid #555;'>🏢 <b>Área:</b> {datos_puesto.get(col_area, '-')}</span>
                    <span style='background-color: #333; padding: 5px 15px; border-radius: 20px; color: white; border: 1px solid #555;'>👤 <b>Reporta a:</b> {datos_puesto.get(col_reporta, '-')}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Función mágica para renderizar diferentes estilos
        def render_items(texto, estilo):
            if pd.isna(texto) or str(texto).strip() == "": return "<p style='color:#888;'><i>No definido</i></p>"
            items = str(texto).split("|")
            
            if estilo == "funciones":
                return "".join([f"<div style='background-color: rgba(76, 175, 80, 0.05); border-left: 3px solid #4CAF50; padding: 10px 15px; margin-bottom: 8px; border-radius: 4px; color: #E0E0E0; font-size: 14px;'><span style='color:#4CAF50; margin-right: 8px;'>✔️</span>{i.strip()}</div>" for i in items])
            elif estilo == "kpis":
                return "".join([f"<div style='background-color: rgba(0, 229, 255, 0.05); border-left: 3px solid #00E5FF; padding: 10px 15px; margin-bottom: 8px; border-radius: 4px; color: #E0E0E0; font-size: 14px;'><span style='color:#00E5FF; margin-right: 8px;'>🎯</span>{i.strip()}</div>" for i in items])
            elif estilo == "tag_gen": 
                tags = "".join([f"<span style='display: inline-block; background-color: rgba(255, 215, 0, 0.1); border: 1px solid rgba(255, 215, 0, 0.5); color: #FFD700; padding: 5px 12px; margin: 4px 4px 4px 0; border-radius: 15px; font-weight: 500; font-size: 13px;'>{i.strip()}</span>" for i in items])
                return f"<div style='margin-bottom: 15px;'>{tags}</div>"
            elif estilo == "tag_esp": 
                tags = "".join([f"<span style='display: inline-block; background-color: rgba(255, 111, 0, 0.1); border: 1px solid rgba(255, 111, 0, 0.5); color: #FFB300; padding: 5px 12px; margin: 4px 4px 4px 0; border-radius: 15px; font-weight: 500; font-size: 13px;'>{i.strip()}</span>" for i in items])
                return f"<div style='margin-bottom: 15px;'>{tags}</div>"

        # Columnas principales
        col1, col2 = st.columns([1.2, 1])
        
        with col1:
            st.markdown("<h3 style='color: #DDDDDD;'>⚙️ Funciones Principales</h3>", unsafe_allow_html=True)
            st.markdown(render_items(datos_puesto.get('funciones', ''), "funciones"), unsafe_allow_html=True)
            
            st.markdown("<h3 style='color: #00E5FF; margin-top: 25px;'>📈 Indicadores de Éxito (KPIs)</h3>", unsafe_allow_html=True)
            st.markdown(render_items(datos_puesto.get('kpis', ''), "kpis"), unsafe_allow_html=True)

        with col2:
            st.markdown("<h3 style='color: #FFD700;'>🧠 Competencias Generales</h3>", unsafe_allow_html=True)
            st.markdown(render_items(datos_puesto.get('comp generales', ''), "tag_gen"), unsafe_allow_html=True)
            
            st.markdown("<h3 style='color: #FF8C00; margin-top: 25px;'>🛠️ Competencias Específicas</h3>", unsafe_allow_html=True)
            st.markdown(render_items(datos_puesto.get('comp especificas', ''), "tag_esp"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.divider()
        
        # Jerarquía
        st.markdown("<h3 style='text-align: center; color: #FFF;'>🌳 Organigrama Directo</h3>", unsafe_allow_html=True)
        jefe = datos_puesto.get(col_reporta, "")
        subordinados = df_puestos[df_puestos[col_reporta] == puesto_sel][col_puesto].tolist()
        
        c_jefe, c_sub = st.columns(2)
        with c_jefe:
            st.info(f"⬆️ **Jefe Inmediato:** {jefe if str(jefe).strip() else 'Nivel Máximo (Directorio / Gerencia)'}")
        with c_sub:
            if subordinados:
                st.success(f"⬇️ **Personal a cargo ({len(subordinados)}):** {', '.join(subordinados)}")
            else:
                st.warning("👤 Sin personal a cargo")

import streamlit as st
import pandas as pd

def mostrar(dfs):
    st.markdown("<h2 style='color: #4A0000;'>📋 Gestión de Evaluaciones de Desempeño</h2>", unsafe_allow_html=True)
    
    # Creamos las pestañas de navegación interna
    tab_carga, tab_interna, tab_ficha = st.tabs([
        "📥 Carga Masiva (Google Forms)", 
        "📝 Realizar Evaluación Interna", 
        "📇 Ficha Individual Completa"
    ])
    
    # ==========================================
    # PESTAÑA 1: CARGA MASIVA
    # ==========================================
    with tab_carga:
        st.markdown("### 📤 Importar resultados de Google Forms")
        st.info("Sube el archivo Excel o CSV descargado de tu formulario de evaluación. El sistema procesará las respuestas y calculará los promedios por competencia automáticamente.")
        
        col1, col2 = st.columns(2)
        with col1:
            periodo_sel = st.selectbox("📅 Selecciona el Periodo:", ["2025-I", "2025-II", "2026-I"])
        with col2:
            tipo_eval_sel = st.selectbox("🏷️ Tipo de Evaluación:", ["Competencias Generales", "Competencias Específicas", "KPIs"])
            
        archivo_subido = st.file_uploader("Sube el archivo CSV/Excel de Google Forms", type=["csv", "xlsx"])
        
        if archivo_subido is not None:
            st.success("¡Archivo cargado en memoria! (Aquí conectaremos el código del 'Traductor' en el siguiente paso)")
            # Aquí irá la lógica de Pandas para agrupar las columnas largas y sacar promedios.

    # ==========================================
    # PESTAÑA 2: EVALUACIÓN INTERNA (Y ENLACES)
    # ==========================================
    with tab_interna:
        st.markdown("### 📝 Formulario de Evaluación Interna")
        st.write("Genera una evaluación manual en el sistema o copia el enlace para enviarlo a un evaluador.")
        
        # Simulación de buscador de empleados
        df_per = dfs.get("PERSONAL", pd.DataFrame())
        if not df_per.empty:
            lista_emp = df_per["dni"].astype(str) + " - " + df_per.get("nombres", "Empleado")
            emp_a_evaluar = st.selectbox("Selecciona al trabajador a evaluar:", lista_emp)
            
            st.markdown(f"**🔗 Enlace directo para el evaluador:**")
            # Esto es un ejemplo de cómo Streamlit puede generar links directos
            st.code(f"https://tu-sistema-gth.streamlit.app/?evaluar={emp_a_evaluar.split(' - ')[0]}&periodo=2025-I")
            
            st.button("Realizar evaluación en pantalla ahora", type="primary")
        else:
            st.warning("No hay datos de personal cargados.")

    # ==========================================
    # PESTAÑA 3: FICHA INDIVIDUAL (BOLETA DE NOTAS)
    # ==========================================
    with tab_ficha:
        st.markdown("### 📇 Ficha de Evaluación Detallada")
        st.write("Consulta el detalle exacto (pregunta por pregunta) de un trabajador.")
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.text_input("🔍 Ingresa el DNI del trabajador:")
        with col_f2:
            st.selectbox("📅 Filtrar por Periodo:", ["Todos", "2025-I", "2025-II"])
            
        st.info("Aquí mostraremos la vista estilo 'Boleta de Notas' desglosada por Tipo (Generales, Específicas, KPIs).")

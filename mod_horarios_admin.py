import streamlit as st
import pandas as pd
from datetime import datetime

def mostrar(dfs, save_data=None):
    st.title("⏰ Gestión de Horarios Administrativos (2 Turnos por Día)")

    # 1. Validación de la tabla CONTRATOS
    if not isinstance(dfs, dict) or "CONTRATOS" not in dfs:
        st.error("No se encontraron los datos de 'CONTRATOS' en el sistema.")
        return

    df_contratos = dfs["CONTRATOS"].copy()
    
    # Normalizar columnas: eliminar espacios y convertir a mayúsculas
    df_contratos.columns = df_contratos.columns.astype(str).str.strip().str.upper()

    # 2. Búsqueda flexible de la columna de Estado
    col_estado = [c for c in df_contratos.columns if "ESTADO" in c]

    if col_estado:
        nombre_col_estado = col_estado[0]
        df_activos = df_contratos[
            df_contratos[nombre_col_estado].astype(str).str.upper().str.contains('ACT')
        ].copy()
    else:
        st.warning("⚠️ No se detectó una columna 'ESTADO'. Se mostrarán todos los registros.")
        df_activos = df_contratos.copy()

    if df_activos.empty:
        st.warning("No se encontraron colaboradores con contratos activos.")
        return

    # 3. Validación de columnas obligatorias
    columnas_requeridas = ['DNI', 'AREA', 'CARGO', 'F_INICIO', 'F_FIN']
    columnas_faltantes = [col for col in columnas_requeridas if col not in df_activos.columns]

    if columnas_faltantes:
        st.error(f"❌ La tabla CONTRATOS no contiene las siguientes columnas requeridas: {columnas_faltantes}")
        st.info(f"💡 Columnas disponibles en tu tabla: {list(df_activos.columns)}")
        return

    # 4. Búsqueda dinámica de nombres y apellidos
    col_nombres = next((c for c in df_activos.columns if c in ['NOMBRES', 'NOMBRE', 'TRABAJADOR', 'COLABORADOR']), "")
    col_apellidos = next((c for c in df_activos.columns if c in ['APELLIDOS', 'APELLIDO']), "")
    
    if col_nombres and col_apellidos:
        df_activos['NOMBRES_COMPLETOS'] = df_activos[col_nombres].astype(str) + " " + df_activos[col_apellidos].astype(str)
    elif col_nombres:
        df_activos['NOMBRES_COMPLETOS'] = df_activos[col_nombres].astype(str)
    elif col_apellidos:
        df_activos['NOMBRES_COMPLETOS'] = df_activos[col_apellidos].astype(str)
    else:
        df_activos['NOMBRES_COMPLETOS'] = ""

    # Crear lista desplegable de búsqueda incluyendo el nombre
    df_activos['DISPLAY'] = (
        df_activos['DNI'].astype(str) + " - " + 
        (df_activos['NOMBRES_COMPLETOS'] + " - " if df_activos['NOMBRES_COMPLETOS'].any() else "") +
        df_activos['AREA'].astype(str) + " (" + 
        df_activos['CARGO'].astype(str) + ")"
    )
    
    colaborador_sel = st.selectbox("Seleccione Colaborador Activo:", df_activos['DISPLAY'].unique())
    
    # Filtrar fila elegida
    contrato_row = df_activos[df_activos['DISPLAY'] == colaborador_sel].iloc[0]
    dni_sel = str(contrato_row['DNI'])
    f_inicio_contrato = str(contrato_row['F_INICIO'])
    f_fin_contrato = str(contrato_row['F_FIN'])

    st.success(f"📋 **Vigencia de Contrato Detectada:** Del `{f_inicio_contrato}` al `{f_fin_contrato}`")
    st.markdown("---")
    st.subheader("🗓️ Configuración de Jornada Semanal (Doble Turno)")

    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    horarios_config = {}

    for dia in dias_semana:
        with st.expander(f"📌 Configurar {dia}", expanded=(dia in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"])):
            asiste = st.checkbox(f"¿Labora el {dia}?", value=(dia in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]), key=f"check_{dia}")
            
            if asiste:
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    e1 = st.time_input(f"Entrada Mañana ({dia})", value=datetime.strptime("08:00", "%H:%M").time(), key=f"e1_{dia}")
                with c2:
                    s1 = st.time_input(f"Salida Mañana ({dia})", value=datetime.strptime("13:00", "%H:%M").time(), key=f"s1_{dia}")
                with c3:
                    e2 = st.time_input(f"Entrada Tarde ({dia})", value=datetime.strptime("14:00", "%H:%M").time(), key=f"e2_{dia}")
                with c4:
                    s2 = st.time_input(f"Salida Tarde ({dia})", value=datetime.strptime("17:00", "%H:%M").time(), key=f"s2_{dia}")
                
                horarios_config[dia] = {"LABORA": "SI", "E1": str(e1), "S1": str(s1), "E2": str(e2), "S2": str(s2)}
            else:
                horarios_config[dia] = {"LABORA": "NO", "E1": "-", "S1": "-", "E2": "-", "S2": "-"}

    if st.button("💾 Guardar Horario en Base de Datos", type="primary"):
        nuevo_registro = {
            "FECHA_REGISTRO": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "DNI": dni_sel,
            "F_INICIO_VIGENCIA": f_inicio_contrato,
            "F_FIN_VIGENCIA": f_fin_contrato,
            "LUN_LAB": horarios_config["Lunes"]["LABORA"], "LUN_E1": horarios_config["Lunes"]["E1"], "LUN_S1": horarios_config["Lunes"]["S1"], "LUN_E2": horarios_config["Lunes"]["E2"], "LUN_S2": horarios_config["Lunes"]["S2"],
            "MAR_LAB": horarios_config["Martes"]["LABORA"], "MAR_E1": horarios_config["Martes"]["E1"], "MAR_S1": horarios_config["Martes"]["S1"], "MAR_E2": horarios_config["Martes"]["E2"], "MAR_S2": horarios_config["Martes"]["S2"],
            "MIE_LAB": horarios_config["Miércoles"]["LABORA"], "MIE_E1": horarios_config["Miércoles"]["E1"], "MIE_S1": horarios_config["Miércoles"]["S1"], "MIE_E2": horarios_config["Miércoles"]["E2"], "MIE_S2": horarios_config["Miércoles"]["S2"],
            "JUE_LAB": horarios_config["Jueves"]["LABORA"], "JUE_E1": horarios_config["Jueves"]["E1"], "JUE_S1": horarios_config["Jueves"]["S1"], "JUE_E2": horarios_config["Jueves"]["E2"], "JUE_S2": horarios_config["Jueves"]["S2"],
            "VIE_LAB": horarios_config["Viernes"]["LABORA"], "VIE_E1": horarios_config["Viernes"]["E1"], "VIE_S1": horarios_config["Viernes"]["S1"], "VIE_E2": horarios_config["Viernes"]["E2"], "VIE_S2": horarios_config["Viernes"]["S2"],
            "SAB_LAB": horarios_config["Sábado"]["LABORA"], "SAB_E1": horarios_config["Sábado"]["E1"], "SAB_S1": horarios_config["Sábado"]["S1"], "SAB_E2": horarios_config["Sábado"]["E2"], "SAB_S2": horarios_config["Sábado"]["S2"],
            "DOM_LAB": horarios_config["Domingo"]["LABORA"], "DOM_E1": horarios_config["Domingo"]["E1"], "DOM_S1": horarios_config["Domingo"]["S1"], "DOM_E2": horarios_config["Domingo"]["E2"], "DOM_S2": horarios_config["Domingo"]["S2"],
            "TOLERANCIA_MIN": 5
        }

        try:
            if callable(save_data):
                save_data("HORARIOS_ADMIN", pd.DataFrame([nuevo_registro]))
                st.balloons()
                st.success(f"¡Horario asignado con éxito a DNI {dni_sel}!")
            else:
                st.error("No se ha definido la función de guardado (save_data). Verifica la llamada en app.py.")
        except Exception as err:
            st.error(f"Error al guardar los datos: {err}")

render_mod_horarios_admin = mostrarardar los datos: {err}")

render_mod_horarios_admin = mostrar

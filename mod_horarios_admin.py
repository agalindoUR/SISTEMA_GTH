import streamlit as st
import pandas as pd
from datetime import datetime

# --- LECTURA OPTIMIZADA CON CACHÉ (Evita saturar la API de Google Sheets) ---
@st.cache_data(ttl=300)  # Mantiene los datos en memoria por 5 minutos (300 s)
def obtener_contratos_cached(_client, sheet_name="DB_SISTEMA_GTH"):
    sheet = _client.open(sheet_name).worksheet("CONTRATOS")
    datos = sheet.get_all_records()
    df = pd.DataFrame(datos)
    # Limpieza de espacios en nombres de columnas
    df.columns = df.columns.str.strip()
    return df

def guardar_horario_gsheet(_client, registro_dict, sheet_name="DB_SISTEMA_GTH"):
    sheet = _client.open(sheet_name).worksheet("HORARIOS_ADMIN")
    
    # Convertir diccionario a fila para Google Sheets
    row = list(registro_dict.values())
    sheet.append_row(row)
    
    # Limpiar caché para actualizar vistas
    st.cache_data.clear()

# --- VISTA PRINCIPAL DEL MÓDULO ---
def render_mod_horarios_admin(client):
    st.title("⏰ Gestión de Horarios Administrativos (2 Turnos por Día)")

    # 1. Carga de contratos desde caché
    try:
        df_contratos = obtener_contratos_cached(client)
    except Exception as e:
        st.error(f"Error al conectar con la base de datos de contratos: {e}")
        return

    # Filtrar solo colaboradores con contratos o registros activos
    df_activos = df_contratos[df_contratos['ESTADO'].astype(str).str.upper().str.contains('ACT')].copy()
    
    if df_activos.empty:
        st.warning("No se encontraron colaboradores con contratos activos.")
        return

    # Crear lista desplegable de búsqueda (DNI + Cargo + Area)
    df_activos['DISPLAY'] = df_activos['DNI'].astype(str) + " - " + df_activos['AREA'].astype(str) + " (" + df_activos['CARGO'].astype(str) + ")"
    
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
                
                horarios_config[dia] = {
                    "LABORA": "SI",
                    "E1": str(e1), "S1": str(s1),
                    "E2": str(e2), "S2": str(s2)
                }
            else:
                horarios_config[dia] = {
                    "LABORA": "NO",
                    "E1": "-", "S1": "-", "E2": "-", "S2": "-"
                }

    if st.button("💾 Guardar Horario en Base de Datos", type="primary"):
        # Estructurar registro plano para la pestaña HORARIOS_ADMIN
        nuevo_registro = {
            "FECHA_REGISTRO": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "DNI": dni_sel,
            "F_INICIO_VIGENCIA": f_inicio_contrato,
            "F_FIN_VIGENCIA": f_fin_contrato,
            # Lunes
            "LUN_LAB": horarios_config["Lunes"]["LABORA"],
            "LUN_E1": horarios_config["Lunes"]["E1"], "LUN_S1": horarios_config["Lunes"]["S1"],
            "LUN_E2": horarios_config["Lunes"]["E2"], "LUN_S2": horarios_config["Lunes"]["S2"],
            # Martes
            "MAR_LAB": horarios_config["Martes"]["LABORA"],
            "MAR_E1": horarios_config["Martes"]["E1"], "MAR_S1": horarios_config["Martes"]["S1"],
            "MAR_E2": horarios_config["Martes"]["E2"], "MAR_S2": horarios_config["Martes"]["S2"],
            # Miércoles
            "MIE_LAB": horarios_config["Miércoles"]["LABORA"],
            "MIE_E1": horarios_config["Miércoles"]["E1"], "MIE_S1": horarios_config["Miércoles"]["S1"],
            "MIE_E2": horarios_config["Miércoles"]["E2"], "MIE_S2": horarios_config["Miércoles"]["S2"],
            # Jueves
            "JUE_LAB": horarios_config["Jueves"]["LABORA"],
            "JUE_E1": horarios_config["Jueves"]["E1"], "JUE_S1": horarios_config["Jueves"]["S1"],
            "JUE_E2": horarios_config["Jueves"]["E2"], "JUE_S2": horarios_config["Jueves"]["S2"],
            # Viernes
            "VIE_LAB": horarios_config["Viernes"]["LABORA"],
            "VIE_E1": horarios_config["Viernes"]["E1"], "VIE_S1": horarios_config["Viernes"]["S1"],
            "VIE_E2": horarios_config["Viernes"]["E2"], "VIE_S2": horarios_config["Viernes"]["S2"],
            # Sábado
            "SAB_LAB": horarios_config["Sábado"]["LABORA"],
            "SAB_E1": horarios_config["Sábado"]["E1"], "SAB_S1": horarios_config["Sábado"]["S1"],
            "SAB_E2": horarios_config["Sábado"]["E2"], "SAB_S2": horarios_config["Sábado"]["S2"],
            # Domingo
            "DOM_LAB": horarios_config["Domingo"]["LABORA"],
            "DOM_E1": horarios_config["Domingo"]["E1"], "DOM_S1": horarios_config["Domingo"]["S1"],
            "DOM_E2": horarios_config["Domingo"]["E2"], "DOM_S2": horarios_config["Domingo"]["S2"],
            "TOLERANCIA_MIN": 5
        }

        try:
            guardar_horario_gsheet(client, nuevo_registro)
            st.balloons()
            st.success(f"¡Horario asignado con éxito a DNI {dni_sel} para el periodo {f_inicio_contrato} a {f_fin_contrato}!")
        except Exception as err:
            st.error(f"Error al guardar en Google Sheets: {err}")

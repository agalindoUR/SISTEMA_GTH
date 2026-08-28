import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta

def mostrar(dfs, save_data=None):
    st.title("⏰ Gestión de Horarios Administrativos")

    # 1. Validación de la tabla CONTRATOS
    if not isinstance(dfs, dict) or "CONTRATOS" not in dfs:
        st.error("No se encontraron los datos de 'CONTRATOS' en el sistema.")
        return

    df_contratos = dfs["CONTRATOS"].copy()
    
    # Normalizar columnas y eliminar duplicadas
    df_contratos.columns = df_contratos.columns.astype(str).str.strip().str.upper()
    df_contratos = df_contratos.loc[:, ~df_contratos.columns.duplicated()]

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

    # 3. Identificación precisa de Nombres y Apellidos
    cols = df_activos.columns.tolist()
    
    # Búsqueda EXACTA para evitar errores con columnas como "TIPO_ADMINISTRATIVO"
    posibles_nom = ['NOMBRES', 'NOMBRE', 'NOMBRES Y APELLIDOS', 'APELLIDOS Y NOMBRES', 'TRABAJADOR', 'COLABORADOR', 'EMPLEADO']
    posibles_ape = ['APELLIDOS', 'APELLIDO']
    
    col_nom = next((c for c in cols if c in posibles_nom), None)
    col_ape = next((c for c in cols if c in posibles_ape), None)

    # UI de Respaldo por si el Excel tiene nombres de columna muy raros
    with st.expander("⚙️ ¿No sale el nombre? Configurar columnas manualmente"):
        st.caption("Usa esto solo si en la lista desplegable de abajo no aparecen los nombres.")
        c_m1, c_m2 = st.columns(2)
        col_nom_manual = c_m1.selectbox("Columna principal (Nombres):", ["Automático"] + cols)
        col_ape_manual = c_m2.selectbox("Columna secundaria (Apellidos):", ["Automático", "Ninguna"] + cols)

    if col_nom_manual != "Automático":
        col_nom = col_nom_manual
    if col_ape_manual != "Automático":
        col_ape = None if col_ape_manual == "Ninguna" else col_ape_manual

    def format_name(row):
        n = str(row[col_nom]) if col_nom and pd.notna(row[col_nom]) else ""
        a = str(row[col_ape]) if col_ape and pd.notna(row[col_ape]) else ""
        
        if n and a and (a in n or n in a):
            res = n if len(n) > len(a) else a
        else:
            res = f"{n} {a}".strip()
            
        return res if res else "NOMBRE NO DETECTADO"

    df_activos['NOMBRES_COMPLETOS'] = df_activos.apply(format_name, axis=1)

    # Crear lista desplegable de búsqueda
    df_activos['DISPLAY'] = (
        df_activos.get('DNI', pd.Series(dtype=str)).astype(str) + " - " + 
        df_activos['NOMBRES_COMPLETOS'] + " - " +
        df_activos.get('AREA', pd.Series(dtype=str)).astype(str) + " (" + 
        df_activos.get('CARGO', pd.Series(dtype=str)).astype(str) + ")"
    )
    
    colaborador_sel = st.selectbox("Seleccione Colaborador Activo:", df_activos['DISPLAY'].unique())
    
    contrato_row = df_activos[df_activos['DISPLAY'] == colaborador_sel].iloc[0]
    dni_sel = str(contrato_row.get('DNI', ''))
    f_inicio_contrato = str(contrato_row.get('F_INICIO', '-'))
    f_fin_contrato = str(contrato_row.get('F_FIN', '-'))

    st.success(f"📋 **Vigencia de Contrato Detectada:** Del `{f_inicio_contrato}` al `{f_fin_contrato}`")
    st.markdown("---")
    
    # ESPACIO RESERVADO PARA EL TOTAL DE HORAS
    marcador_horas = st.empty()
    
    st.subheader("🗓️ Configuración de Jornada Semanal")

    # --- LÓGICA DE COPIA (Debe ir antes de renderizar los inputs) ---
    if st.button("🔄 Copiar horario del Lunes a Martes-Viernes", type="secondary"):
        for d in ["Martes", "Miércoles", "Jueves", "Viernes"]:
            st.session_state[f"check_{d}"] = st.session_state.get("check_Lunes", True)
            st.session_state[f"tm_{d}"] = st.session_state.get("tm_Lunes", True)
            st.session_state[f"tt_{d}"] = st.session_state.get("tt_Lunes", True)
            if "e1_Lunes" in st.session_state: st.session_state[f"e1_{d}"] = st.session_state["e1_Lunes"]
            if "s1_Lunes" in st.session_state: st.session_state[f"s1_{d}"] = st.session_state["s1_Lunes"]
            if "e2_Lunes" in st.session_state: st.session_state[f"e2_{d}"] = st.session_state["e2_Lunes"]
            if "s2_Lunes" in st.session_state: st.session_state[f"s2_{d}"] = st.session_state["s2_Lunes"]

    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    horarios_config = {}
    total_horas_semanales = 0.0

    def calcular_diferencia_horas(inicio, fin):
        dt_inicio = datetime.combine(date.today(), inicio)
        dt_fin = datetime.combine(date.today(), fin)
        if dt_fin < dt_inicio:
            dt_fin += timedelta(days=1)
        return (dt_fin - dt_inicio).total_seconds() / 3600.0

    def get_time(key, default_str):
        if key not in st.session_state:
            st.session_state[key] = datetime.strptime(default_str, "%H:%M").time()
        return st.session_state[key]

    for dia in dias_semana:
        with st.expander(f"📌 Configurar {dia}", expanded=(dia in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"])):
            
            if f"check_{dia}" not in st.session_state:
                st.session_state[f"check_{dia}"] = (dia in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"])
            
            asiste = st.checkbox(f"¿Labora el {dia}?", key=f"check_{dia}")
            horarios_config[dia] = {"LABORA": "NO", "E1": "-", "S1": "-", "E2": "-", "S2": "-"}
            
            if asiste:
                horarios_config[dia]["LABORA"] = "SI"
                col_m, col_t = st.columns(2)
                
                with col_m:
                    if f"tm_{dia}" not in st.session_state: st.session_state[f"tm_{dia}"] = True
                    turno_manana = st.checkbox("☀️ Habilitar Turno Mañana", key=f"tm_{dia}")
                    
                    if turno_manana:
                        sub_c1, sub_c2 = st.columns(2)
                        with sub_c1:
                            e1 = st.time_input("Entrada", value=get_time(f"e1_{dia}", "08:00"), key=f"e1_{dia}")
                        with sub_c2:
                            s1 = st.time_input("Salida", value=get_time(f"s1_{dia}", "13:00"), key=f"s1_{dia}")
                        
                        horarios_config[dia]["E1"] = str(e1)
                        horarios_config[dia]["S1"] = str(s1)
                        total_horas_semanales += calcular_diferencia_horas(e1, s1)
                
                with col_t:
                    if f"tt_{dia}" not in st.session_state: st.session_state[f"tt_{dia}"] = True
                    turno_tarde = st.checkbox("🌙 Habilitar Turno Tarde", key=f"tt_{dia}")
                    
                    if turno_tarde:
                        sub_c3, sub_c4 = st.columns(2)
                        with sub_c3:
                            e2 = st.time_input("Entrada", value=get_time(f"e2_{dia}", "16:00"), key=f"e2_{dia}")
                        with sub_c4:
                            s2 = st.time_input("Salida", value=get_time(f"s2_{dia}", "19:00"), key=f"s2_{dia}")
                        
                        horarios_config[dia]["E2"] = str(e2)
                        horarios_config[dia]["S2"] = str(s2)
                        total_horas_semanales += calcular_diferencia_horas(e2, s2)

    # Imprimir el total de horas
    marcador_horas.metric("⏱️ TOTAL HORAS SEMANALES ASIGNADAS", f"{total_horas_semanales:.2f} hrs")

    st.markdown("---")
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

        if callable(save_data):
            try:
                # Intento 1: Guardado normal como DataFrame
                df_guardar = pd.DataFrame([nuevo_registro])
                save_data("HORARIOS_ADMIN", df_guardar)
                st.balloons()
                st.success(f"¡Horario asignado con éxito a DNI {dni_sel}! (Total: {total_horas_semanales:.2f} hrs)")
            except ValueError as e:
                # Si el app.py tiene un error lógico (el del ambiguous truth value) lo atrapamos aquí
                if "truth value" in str(e).lower() or "ambiguous" in str(e).lower():
                    try:
                        # Intento 2: Como lista de diccionarios (A prueba de validaciones booleanas)
                        save_data("HORARIOS_ADMIN", [nuevo_registro])
                        st.balloons()
                        st.success(f"¡Horario asignado con éxito a DNI {dni_sel}! (Total: {total_horas_semanales:.2f} hrs)")
                    except:
                        try:
                            # Intento 3: Como diccionario simple
                            save_data("HORARIOS_ADMIN", nuevo_registro)
                            st.balloons()
                            st.success(f"¡Horario asignado con éxito a DNI {dni_sel}! (Total: {total_horas_semanales:.2f} hrs)")
                        except Exception as e3:
                            st.error(f"Error persistente al guardar: {e3}")
                else:
                    st.error(f"Error al guardar los datos: {e}")
            except Exception as e:
                st.error(f"Error inesperado: {e}")
        else:
            st.error("No se ha definido la función de guardado (save_data). Verifica la llamada en app.py.")

render_mod_horarios_admin = mostrar

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta


def mostrar(dfs, save_data=None):
    st.title("⏰ Gestión de Horarios Administrativos")

    if not isinstance(dfs, dict) or "CONTRATOS" not in dfs:
        st.error("No se encontraron los datos de 'CONTRATOS' en el sistema.")
        return

    # Normalización de Tabla CONTRATOS
    df_contratos = dfs["CONTRATOS"].copy()
    df_contratos.columns = df_contratos.columns.astype(str).str.strip().str.upper()
    df_contratos = df_contratos.loc[:, ~df_contratos.columns.duplicated()]

    # Normalización de Tabla Personal (si existe)
    nombre_tabla_personal = next(
        (
            k
            for k in dfs.keys()
            if k.upper()
            in [
                "DATOS GENERALES",
                "DATOS_GENERALES",
                "PERSONAL",
                "EMPLEADOS",
                "TRABAJADORES",
            ]
        ),
        None,
    )
    if nombre_tabla_personal:
        df_personal = dfs[nombre_tabla_personal].copy()
        df_personal.columns = (
            df_personal.columns.astype(str).str.strip().str.upper()
        )
        df_personal = df_personal.loc[:, ~df_personal.columns.duplicated()]

        col_dni_con = next(
            (c for c in df_contratos.columns if "DNI" in c or "DOC" in c), None
        )
        col_dni_per = next(
            (c for c in df_personal.columns if "DNI" in c or "DOC" in c), None
        )

        if col_dni_con and col_dni_per:
            df_contratos = pd.merge(
                df_contratos,
                df_personal,
                left_on=col_dni_con,
                right_on=col_dni_per,
                how="left",
            )

    col_estado = [c for c in df_contratos.columns if "ESTADO" in c]
    df_activos = (
        df_contratos[
            df_contratos[col_estado[0]]
            .astype(str)
            .str.upper()
            .str.contains("ACT")
        ].copy()
        if col_estado
        else df_contratos.copy()
    )

    if df_activos.empty:
        st.warning("No se encontraron colaboradores con contratos activos.")
        return

    cols = df_activos.columns.tolist()
    col_nom = next(
        (
            c
            for c in cols
            if c
            in [
                "NOMBRES",
                "NOMBRE",
                "NOMBRES Y APELLIDOS",
                "APELLIDOS Y NOMBRES",
                "TRABAJADOR",
            ]
        ),
        None,
    )
    col_ape = next((c for c in cols if c in ["APELLIDOS", "APELLIDO"]), None)

    def format_name(row):
        n = str(row[col_nom]) if col_nom and pd.notna(row[col_nom]) else ""
        a = str(row[col_ape]) if col_ape and pd.notna(row[col_ape]) else ""
        if n and a and (a in n or n in a):
            return n if len(n) > len(a) else a
        return f"{a} {n}".strip() if a else n.strip() or "NOMBRE NO DETECTADO"

    df_activos["NOMBRES_COMPLETOS"] = df_activos.apply(format_name, axis=1)

    col_dni = next((c for c in cols if "DNI" in c or "DOC" in c), "DNI")
    col_cargo = next((c for c in cols if "CARGO" in c or "PUESTO" in c), "CARGO")

    df_activos["DISPLAY"] = (
        df_activos[col_dni].astype(str)
        + " - "
        + df_activos["NOMBRES_COMPLETOS"]
        + " ("
        + df_activos[col_cargo].astype(str).fillna("Sin cargo")
        + ")"
    )

    colaborador_sel = st.selectbox(
        "Seleccione Colaborador Activo:", df_activos["DISPLAY"].unique()
    )
    contrato_row = df_activos[df_activos["DISPLAY"] == colaborador_sel].iloc[0]
    dni_sel = str(contrato_row.get(col_dni, ""))
    f_inicio_contrato = str(contrato_row.get("F_INICIO", "-"))
    f_fin_contrato = str(contrato_row.get("F_FIN", "-"))

    # Limpiar caché temporal de la interfaz al cambiar de colaborador
    if st.session_state.get("ultimo_dni_seleccionado") != dni_sel:
        for k in list(st.session_state.keys()):
            if k.startswith(
                ("check_", "tm_", "tt_", "e1_", "s1_", "e2_", "s2_")
            ):
                del st.session_state[k]
        st.session_state["ultimo_dni_seleccionado"] = dni_sel

    # --- LECTURA Y NORMALIZACIÓN DE HORARIOS_ADMIN ---
    horario_bd = None
    if "HORARIOS_ADMIN" in dfs and not dfs["HORARIOS_ADMIN"].empty:
        df_horarios = dfs["HORARIOS_ADMIN"].copy()
        df_horarios.columns = (
            df_horarios.columns.astype(str).str.strip().str.upper()
        )
        df_horarios = df_horarios.loc[:, ~df_horarios.columns.duplicated()]
        dfs["HORARIOS_ADMIN"] = df_horarios

        col_dni_horario = next(
            (c for c in df_horarios.columns if "DNI" in c or "DOC" in c), None
        )

        if col_dni_horario:
            df_filtro = df_horarios[
                df_horarios[col_dni_horario].astype(str) == dni_sel
            ]
            if not df_filtro.empty:
                horario_bd = df_filtro.iloc[-1]

    def parse_time(time_str, default):
        if pd.isna(time_str) or str(time_str).strip() in [
            "",
            "-",
            "nan",
            "None",
        ]:
            return datetime.strptime(default, "%H:%M").time()
        try:
            val = str(time_str).strip()
            if len(val.split(":")) == 3:
                return datetime.strptime(val, "%H:%M:%S").time()
            return datetime.strptime(val, "%H:%M").time()
        except Exception:
            return datetime.strptime(default, "%H:%M").time()

    if horario_bd is not None:
        st.success(
            f"📋 **Vigencia de Contrato Detectada:** Del `{f_inicio_contrato}` al `{f_fin_contrato}` | ✅ **Horario guardado previamente cargado.**"
        )
    else:
        st.success(
            f"📋 **Vigencia de Contrato Detectada:** Del `{f_inicio_contrato}` al `{f_fin_contrato}` | 🆕 **Nuevo horario (valores por defecto).**"
        )

    st.markdown("---")

    marcador_horas = st.empty()
    st.subheader("🗓️ Configuración de Jornada Semanal")

    if st.button("🔄 Copiar horario del Lunes a Martes-Viernes", type="secondary"):
        for d in ["Martes", "Miércoles", "Jueves", "Viernes"]:
            for key in ["check", "tm", "tt", "e1", "s1", "e2", "s2"]:
                if f"{key}_Lunes" in st.session_state:
                    st.session_state[f"{key}_{d}"] = st.session_state[
                        f"{key}_Lunes"
                    ]

    dias_semana = [
        "Lunes",
        "Martes",
        "Miércoles",
        "Jueves",
        "Viernes",
        "Sábado",
        "Domingo",
    ]
    mapa_dias = {
        "Lunes": "LUN",
        "Martes": "MAR",
        "Miércoles": "MIE",
        "Jueves": "JUE",
        "Viernes": "VIE",
        "Sábado": "SAB",
        "Domingo": "DOM",
    }
    horarios_config = {}
    total_horas_semanales = 0.0

    def calcular_diferencia_horas(inicio, fin):
        dt_inicio = datetime.combine(date.today(), inicio)
        dt_fin = datetime.combine(date.today(), fin)
        if dt_fin < dt_inicio:
            dt_fin += timedelta(days=1)
        return (dt_fin - dt_inicio).total_seconds() / 3600.0

    for dia in dias_semana:
        prefijo = mapa_dias[dia]

        if horario_bd is not None:
            def_labora = (
                str(horario_bd.get(f"{prefijo}_LAB", "NO")).strip().upper()
                == "SI"
            )
            v_e1 = str(horario_bd.get(f"{prefijo}_E1", "-"))
            v_s1 = str(horario_bd.get(f"{prefijo}_S1", "-"))
            v_e2 = str(horario_bd.get(f"{prefijo}_E2", "-"))
            v_s2 = str(horario_bd.get(f"{prefijo}_S2", "-"))

            def_tm = v_e1 not in ["-", "", "nan", "None"]
            def_tt = v_e2 not in ["-", "", "nan", "None"]

            val_e1 = parse_time(v_e1, "08:00")
            val_s1 = parse_time(v_s1, "13:00")
            val_e2 = parse_time(v_e2, "16:00")
            val_s2 = parse_time(v_s2, "19:00")
        else:
            def_labora = dia in [
                "Lunes",
                "Martes",
                "Miércoles",
                "Jueves",
                "Viernes",
            ]
            def_tm = True
            def_tt = True
            val_e1, val_s1 = parse_time("08:00", "08:00"), parse_time(
                "13:00", "13:00"
            )
            val_e2, val_s2 = parse_time("16:00", "16:00"), parse_time(
                "19:00", "19:00"
            )

        if f"check_{dia}" not in st.session_state:
            st.session_state[f"check_{dia}"] = def_labora
        if f"tm_{dia}" not in st.session_state:
            st.session_state[f"tm_{dia}"] = def_tm
        if f"tt_{dia}" not in st.session_state:
            st.session_state[f"tt_{dia}"] = def_tt
        if f"e1_{dia}" not in st.session_state:
            st.session_state[f"e1_{dia}"] = val_e1
        if f"s1_{dia}" not in st.session_state:
            st.session_state[f"s1_{dia}"] = val_s1
        if f"e2_{dia}" not in st.session_state:
            st.session_state[f"e2_{dia}"] = val_e2
        if f"s2_{dia}" not in st.session_state:
            st.session_state[f"s2_{dia}"] = val_s2

        with st.expander(
            f"📌 Configurar {dia}",
            expanded=(
                dia in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
            ),
        ):
            asiste = st.checkbox(f"¿Labora el {dia}?", key=f"check_{dia}")
            horarios_config[dia] = {
                "LABORA": "NO",
                "E1": "-",
                "S1": "-",
                "E2": "-",
                "S2": "-",
            }

            if asiste:
                horarios_config[dia]["LABORA"] = "SI"
                col_m, col_t = st.columns(2)

                with col_m:
                    turno_manana = st.checkbox(
                        "☀️ Habilitar Turno Mañana", key=f"tm_{dia}"
                    )
                    if turno_manana:
                        sub_c1, sub_c2 = st.columns(2)
                        with sub_c1:
                            e1 = st.time_input("Entrada", key=f"e1_{dia}")
                        with sub_c2:
                            s1 = st.time_input("Salida", key=f"s1_{dia}")

                        horarios_config[dia]["E1"] = str(e1)
                        horarios_config[dia]["S1"] = str(s1)
                        total_horas_semanales += calcular_diferencia_horas(
                            e1, s1
                        )

                with col_t:
                    turno_tarde = st.checkbox(
                        "🌙 Habilitar Turno Tarde", key=f"tt_{dia}"
                    )
                    if turno_tarde:
                        sub_c3, sub_c4 = st.columns(2)
                        with sub_c3:
                            e2 = st.time_input("Entrada", key=f"e2_{dia}")
                        with sub_c4:
                            s2 = st.time_input("Salida", key=f"s2_{dia}")

                        horarios_config[dia]["E2"] = str(e2)
                        horarios_config[dia]["S2"] = str(s2)
                        total_horas_semanales += calcular_diferencia_horas(
                            e2, s2
                        )

    marcador_horas.metric(
        "⏱️ TOTAL HORAS SEMANALES ASIGNADAS",
        f"{total_horas_semanales:.2f} hrs",
    )

    st.markdown("---")
    if st.button("💾 Guardar Horario en Base de Datos", type="primary"):
        nuevo_registro = {
            "FECHA_REGISTRO": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "DNI": dni_sel,
            "F_INICIO_VIGENCIA": f_inicio_contrato,
            "F_FIN_VIGENCIA": f_fin_contrato,
            "LUN_LAB": horarios_config["Lunes"]["LABORA"],
            "LUN_E1": horarios_config["Lunes"]["E1"],
            "LUN_S1": horarios_config["Lunes"]["S1"],
            "LUN_E2": horarios_config["Lunes"]["E2"],
            "LUN_S2": horarios_config["Lunes"]["S2"],
            "MAR_LAB": horarios_config["Martes"]["LABORA"],
            "MAR_E1": horarios_config["Martes"]["E1"],
            "MAR_S1": horarios_config["Martes"]["S1"],
            "MAR_E2": horarios_config["Martes"]["E2"],
            "MAR_S2": horarios_config["Martes"]["S2"],
            "MIE_LAB": horarios_config["Miércoles"]["LABORA"],
            "MIE_E1": horarios_config["Miércoles"]["E1"],
            "MIE_S1": horarios_config["Miércoles"]["S1"],
            "MIE_E2": horarios_config["Miércoles"]["E2"],
            "MIE_S2": horarios_config["Miércoles"]["S2"],
            "JUE_LAB": horarios_config["Jueves"]["LABORA"],
            "JUE_E1": horarios_config["Jueves"]["E1"],
            "JUE_S1": horarios_config["Jueves"]["S1"],
            "JUE_E2": horarios_config["Jueves"]["E2"],
            "JUE_S2": horarios_config["Jueves"]["S2"],
            "VIE_LAB": horarios_config["Viernes"]["LABORA"],
            "VIE_E1": horarios_config["Viernes"]["E1"],
            "VIE_S1": horarios_config["Viernes"]["S1"],
            "VIE_E2": horarios_config["Viernes"]["E2"],
            "VIE_S2": horarios_config["Viernes"]["S2"],
            "SAB_LAB": horarios_config["Sábado"]["LABORA"],
            "SAB_E1": horarios_config["Sábado"]["E1"],
            "SAB_S1": horarios_config["Sábado"]["S1"],
            "SAB_E2": horarios_config["Sábado"]["E2"],
            "SAB_S2": horarios_config["Sábado"]["S2"],
            "DOM_LAB": horarios_config["Domingo"]["LABORA"],
            "DOM_E1": horarios_config["Domingo"]["E1"],
            "DOM_S1": horarios_config["Domingo"]["S1"],
            "DOM_E2": horarios_config["Domingo"]["E2"],
            "DOM_S2": horarios_config["Domingo"]["S2"],
            "TOLERANCIA_MIN": 5,
        }

        if callable(save_data):
            try:
                df_nuevo = pd.DataFrame([nuevo_registro])

                if "HORARIOS_ADMIN" in dfs and not dfs["HORARIOS_ADMIN"].empty:
                    df_base = dfs["HORARIOS_ADMIN"].copy()
                    
                    # Mapeo inteligente: empareja las columnas ignorando espacios y guiones bajos
                    col_map = {}
                    for col_nuevo in df_nuevo.columns:
                        col_clean_nuevo = str(col_nuevo).replace('_', '').replace(' ', '').upper()
                        for col_base in df_base.columns:
                            col_clean_base = str(col_base).replace('_', '').replace(' ', '').upper()
                            if col_clean_nuevo == col_clean_base:
                                col_map[col_nuevo] = col_base
                                break
                    
                    df_nuevo.rename(columns=col_map, inplace=True)

                    col_dni_bd = next((c for c in df_base.columns if 'DNI' in str(c).upper() or 'DOC' in str(c).upper()), None)

                    if col_dni_bd:
                        mask = df_base[col_dni_bd].astype(str).str.strip() == str(dni_sel).strip()
                        if mask.any():
                            # Actualizar fila existente en las columnas correspondientes
                            idx_to_update = df_base[mask].index[-1]
                            for col in df_nuevo.columns:
                                df_base.at[idx_to_update, col] = df_nuevo.iloc[0][col]
                            dfs["HORARIOS_ADMIN"] = df_base
                        else:
                            # Anexar nueva fila alineada a las columnas existentes
                            dfs["HORARIOS_ADMIN"] = pd.concat([df_base, df_nuevo], ignore_index=True)
                    else:
                        dfs["HORARIOS_ADMIN"] = pd.concat([df_base, df_nuevo], ignore_index=True)
                else:
                    dfs["HORARIOS_ADMIN"] = df_nuevo

                save_data(dfs, "HORARIOS_ADMIN")

                st.balloons()
                st.success(f"¡Horario guardado con éxito! (DNI {dni_sel} - Total: {total_horas_semanales:.2f} hrs)")
            except Exception as e:
                st.error(f"Ocurrió un error al intentar guardar: {e}")
        else:
            st.error("No se ha definido la función de guardado (save_data).")

render_mod_horarios_admin = mostrar

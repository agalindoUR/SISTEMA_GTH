import uuid
from datetime import date

replace_dict = {}  # Auxiliary placeholder if needed
import pandas as pd
import streamlit as st


def renderizar_experiencia_laboral(
    dni_buscado, dfs, exportar_df_a_sheets, col_conf=None
):
    HEADERS_EXP = [
        "DNI",
        "PUESTO",
        "LUGAR",
        "TIPO DE EXPERIENCIA",
        "FECHA DE INICIO",
        "FECHA DE FIN",
        "MOTIVO DE CESE",
    ]

    def normalizar_df_exp(df_in):
        """Garantiza que el DataFrame contenga la columna 'id' y todas las columnas requeridas."""
        if df_in is None or df_in.empty:
            return pd.DataFrame(columns=["id"] + HEADERS_EXP)

        df_out = df_in.copy()

        # 1. Identificar o crear la columna 'id'
        col_id_existente = next(
            (c for c in df_out.columns if str(c).strip().lower() == "id"), None
        )

        if col_id_existente:
            df_out = df_out.rename(columns={col_id_existente: "id"})
        else:
            df_out["id"] = [str(uuid.uuid4()) for _ in range(len(df_out))]

        # Asegurar que ninguna fila tenga un 'id' vacío o nulo
        df_out["id"] = df_out["id"].apply(
            lambda x: (
                str(uuid.uuid4())
                if pd.isna(x) or str(x).strip() in ["", "nan", "None"]
                else str(x)
            )
        )

        # 2. Normalizar nombres de las demás columnas
        renombres = {
            "dni": "DNI",
            "puesto": "PUESTO",
            "lugar": "LUGAR",
            "tipo de experiencia": "TIPO DE EXPERIENCIA",
            "tipo_experiencia": "TIPO DE EXPERIENCIA",
            "fecha de inicio": "FECHA DE INICIO",
            "fecha_inicio": "FECHA DE INICIO",
            "fecha de fin": "FECHA DE FIN",
            "fecha_fin": "FECHA DE FIN",
            "motivo de cese": "MOTIVO DE CESE",
            "motivo_cese": "MOTIVO DE CESE",
        }
        df_out = df_out.rename(columns=renombres)
        df_out = df_out.drop(columns=["SEL", "sel"], errors="ignore")
        df_out = df_out.loc[:, ~df_out.columns.duplicated()]

        for col in HEADERS_EXP:
            if col not in df_out.columns:
                df_out[col] = ""

        cols_ordenadas = ["id"] + HEADERS_EXP
        return df_out[cols_ordenadas].fillna("").astype(str)

    # --- Sincronizar e inyectar 'id' en la memoria global ---
    if "dfs" in st.session_state and "EXP. LABORAL" in st.session_state["dfs"]:
        df_exp_general = normalizar_df_exp(
            st.session_state["dfs"]["EXP. LABORAL"]
        )
    else:
        df_exp_general = normalizar_df_exp(
            dfs.get("EXP. LABORAL", pd.DataFrame())
        )

    dfs["EXP. LABORAL"] = df_exp_general
    if "dfs" not in st.session_state:
        st.session_state["dfs"] = {}
    st.session_state["dfs"]["EXP. LABORAL"] = df_exp_general

    # Filtrar datos del empleado
    vst_df = df_exp_general[
        df_exp_general["DNI"].astype(str) == str(dni_buscado)
    ].copy()

    if "SEL" not in vst_df.columns:
        vst_df.insert(0, "SEL", False)

    # --- Funciones Auxiliares ---
    def calcular_meses(f_ini, f_fin):
        try:
            inicio = pd.to_datetime(f_ini, errors="coerce", dayfirst=True)
            fin = pd.to_datetime(f_fin, errors="coerce", dayfirst=True)
            if pd.isna(inicio) or pd.isna(fin):
                return 0
            return max(0, int((fin - inicio).days / 30.44))
        except Exception:
            return 0

    def dar_formato_fecha(fecha_str):
        try:
            if pd.isna(fecha_str) or str(fecha_str).strip() in [
                "",
                "NaT",
                "None",
            ]:
                return "N/A"
            return pd.to_datetime(fecha_str, dayfirst=True).strftime("%d/%m/%Y")
        except Exception:
            return str(fecha_str)

    def formato_tiempo(total_meses):
        anios = total_meses // 12
        meses = total_meses % 12
        if anios > 0 and meses > 0:
            return f"{anios} años y {meses} meses"
        elif anios > 0:
            return f"{anios} años"
        elif meses > 0:
            return f"{meses} meses"
        else:
            return "0 meses"

    def agrupar_contratos_continuos(df_c):
        if df_c.empty:
            return pd.DataFrame()

        df = df_c.copy()

        # Detección flexible e insensible a mayúsculas/minúsculas de columnas de fecha
        col_ini = next(
            (
                c
                for c in df.columns
                if any(
                    k in str(c).strip().lower()
                    for k in ["f_inicio", "fecha_inicio", "fecha inicio", "inicio"]
                )
            ),
            None,
        )
        col_fin = next(
            (
                c
                for c in df.columns
                if any(
                    k in str(c).strip().lower()
                    for k in [
                        "f_fin",
                        "fecha_fin",
                        "fecha fin",
                        "fin",
                        "termino",
                    ]
                )
            ),
            None,
        )

        col_puesto = next(
            (
                c
                for c in df.columns
                if any(
                    k in str(c).strip().lower() for k in ["cargo", "puesto"]
                )
            ),
            None,
        )
        col_tipo_trab = next(
            (
                c
                for c in df.columns
                if any(
                    k in str(c).strip().lower()
                    for k in ["trabajador", "modalidad", "tipo"]
                )
            ),
            None,
        )
        col_tipo_cont = next(
            (
                c
                for c in df.columns
                if "contrato" in str(c).strip().lower()
                and "tipo" in str(c).strip().lower()
            ),
            None,
        )

        if not col_ini:
            return pd.DataFrame()

        df["f_ini_dt"] = pd.to_datetime(
            df[col_ini], errors="coerce", dayfirst=True
        )
        df["f_fin_dt"] = (
            pd.to_datetime(df[col_fin], errors="coerce", dayfirst=True)
            if col_fin
            else pd.NaT
        )
        df = (
            df.dropna(subset=["f_ini_dt"])
            .sort_values("f_ini_dt")
            .reset_index(drop=True)
        )

        if df.empty:
            return pd.DataFrame()

        grupos = []
        actual = None

        for idx, row in df.iterrows():
            puesto = (
                str(row[col_puesto])
                if col_puesto and pd.notna(row[col_puesto])
                else "N/A"
            )
            tipo_raw = (
                str(row[col_tipo_trab])
                if col_tipo_trab and pd.notna(row[col_tipo_trab])
                else "Administrativo"
            )
            tipo_exp = (
                "Docente" if "docente" in tipo_raw.lower() else "Administrativo"
            )
            tipo_contrato = (
                str(row[col_tipo_cont])
                if col_tipo_cont and pd.notna(row[col_tipo_cont])
                else "N/A"
            )

            ini_dt = row["f_ini_dt"]
            fin_dt = row["f_fin_dt"] if pd.notna(row["f_fin_dt"]) else ini_dt

            if actual is None:
                actual = {
                    "puesto": puesto,
                    "tipo_exp": tipo_exp,
                    "tipo_contrato": tipo_contrato,
                    "f_inicio": row[col_ini],
                    "f_fin": row[col_fin] if col_fin else row[col_ini],
                    "f_ini_dt": ini_dt,
                    "f_fin_dt": fin_dt,
                }
            else:
                dias_diferencia = (ini_dt - actual["f_fin_dt"]).days
                mismo_puesto = (
                    str(puesto).strip().lower()
                    == str(actual["puesto"]).strip().lower()
                )
                mismo_tipo = tipo_exp == actual["tipo_exp"]

                if mismo_puesto and mismo_tipo and dias_diferencia <= 2:
                    if fin_dt > actual["f_fin_dt"]:
                        actual["f_fin_dt"] = fin_dt
                        actual["f_fin"] = (
                            row[col_fin] if col_fin else row[col_ini]
                        )
                else:
                    grupos.append(actual)
                    actual = {
                        "puesto": puesto,
                        "tipo_exp": tipo_exp,
                        "tipo_contrato": tipo_contrato,
                        "f_inicio": row[col_ini],
                        "f_fin": row[col_fin] if col_fin else row[col_ini],
                        "f_ini_dt": ini_dt,
                        "f_fin_dt": fin_dt,
                    }
        if actual is not None:
            grupos.append(actual)

        return pd.DataFrame(grupos)

    # --- Cargar datos de Contratos ---
    df_contratos = dfs.get("CONTRATOS", pd.DataFrame())
    col_dni_contratos = next(
        (c for c in df_contratos.columns if str(c).strip().lower() == "dni"),
        None,
    )

    contratos_empleado = pd.DataFrame()
    if not df_contratos.empty and col_dni_contratos:
        contratos_raw = df_contratos[
            df_contratos[col_dni_contratos].astype(str).str.strip()
            == str(dni_buscado).strip()
        ]
        contratos_empleado = agrupar_contratos_continuos(contratos_raw)

    meses_docente = 0
    meses_admin = 0

    # --- Distribución en Columnas ---
    col_izq, col_der = st.columns([2, 1])

    with col_izq:
        st.markdown(
            "<h3 style='color: #FFD700;'>🏢 Experiencia Interna (Universidad Roosevelt)</h3>",
            unsafe_allow_html=True,
        )
        if contratos_empleado.empty:
            st.markdown(
                "<p style='color:#DDDDDD;'>No hay contratos internos registrados.</p>",
                unsafe_allow_html=True,
            )
        else:
            for idx, row in contratos_empleado.iterrows():
                # Búsqueda segura de claves para evitar KeyError
                f_ini = row.get(
                    "f_inicio",
                    row.get(
                        "F_INICIO",
                        row.get("FECHA DE INICIO", row.get("FECHA INICIO", "")),
                    ),
                )
                f_fin = row.get(
                    "f_fin",
                    row.get(
                        "F_FIN",
                        row.get("FECHA DE FIN", row.get("FECHA FIN", "")),
                    ),
                )
                f_ini_str, f_fin_str = dar_formato_fecha(
                    f_ini
                ), dar_formato_fecha(f_fin)

                puesto = row.get(
                    "puesto",
                    row.get("PUESTO", row.get("CARGO", row.get("cargo", "N/A"))),
                )
                tipo_exp = row.get(
                    "tipo_exp",
                    row.get("TIPO DE EXPERIENCIA", "Administrativo"),
                )
                tipo_contrato = row.get(
                    "tipo_contrato",
                    row.get(
                        "TIPO CONTRATO", row.get("tipo contrato", "N/A")
                    ),
                )

                meses_calc = calcular_meses(f_ini, f_fin)
                if tipo_exp == "Docente":
                    meses_docente += meses_calc
                else:
                    meses_admin += meses_calc

                st.markdown(
                    f"""
                <div style='background-color: #F9F6EE; padding: 15px; border-radius: 8px; border-left: 6px solid #4A0000; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #CCCCCC;'>
                    <div style='color: #000000; font-size: 1.1em; font-weight: bold; margin-bottom: 5px;'>{puesto} <span style='font-size: 0.85em; color: #555555;'>(Interno - {tipo_exp})</span></div>
                    <div style='color: #222222; font-size: 0.95em;'>
                        <strong>Lugar:</strong> Universidad Roosevelt <br>
                        <strong>Periodo:</strong> {f_ini_str} hasta {f_fin_str} <br>
                        <strong>Tipo de Contrato:</strong> {tipo_contrato}
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

        st.markdown(
            "<h3 style='color: #FFD700; margin-top: 20px;'>💼 Experiencia Externa Registrada</h3>",
            unsafe_allow_html=True,
        )
        if vst_df.empty:
            st.markdown(
                "<p style='color:#DDDDDD;'>No hay experiencia externa registrada.</p>",
                unsafe_allow_html=True,
            )
        else:
            for idx, row in vst_df.iterrows():
                f_ini, f_fin = row.get("FECHA DE INICIO", "N/A"), row.get(
                    "FECHA DE FIN", "N/A"
                )
                f_ini_str, f_fin_str = dar_formato_fecha(
                    f_ini
                ), dar_formato_fecha(f_fin)

                tipo_exp_raw = str(
                    row.get("TIPO DE EXPERIENCIA", "Administrativo")
                )
                tipo_exp = (
                    "Docente"
                    if "docente" in tipo_exp_raw.lower()
                    else "Administrativo"
                )

                meses_calc = calcular_meses(f_ini, f_fin)
                if tipo_exp == "Docente":
                    meses_docente += meses_calc
                else:
                    meses_admin += meses_calc

                puesto_ext = row.get("PUESTO", "N/A")
                lugar_ext = row.get("LUGAR", "N/A")
                motivo_ext = row.get("MOTIVO DE CESE", "N/A")

                st.markdown(
                    f"""
                <div style='background-color: #F9F6EE; padding: 15px; border-radius: 8px; border-left: 6px solid #004A80; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #CCCCCC;'>
                    <div style='color: #000000; font-size: 1.1em; font-weight: bold; margin-bottom: 5px;'>{puesto_ext} <span style='font-size: 0.85em; color: #555555;'>({tipo_exp.capitalize()})</span></div>
                    <div style='color: #222222; font-size: 0.95em;'>
                        <strong>Lugar:</strong> {lugar_ext} <br>
                        <strong>Periodo:</strong> {f_ini_str} hasta {f_fin_str} <br>
                        <strong>Motivo de cese:</strong> {motivo_ext}
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

    with col_der:
        st.markdown(
            "<h3 style='color: #FFD700;'>📊 Resumen</h3>", unsafe_allow_html=True
        )

        html_resumen = f"""
        <div style='background-color: #4A0000; padding: 20px; border-radius: 10px; border: 2px solid #FFD700; box-shadow: 2px 2px 10px rgba(0,0,0,0.5); position: sticky; top: 50px;'>
            <h4 style='color: #FFD700; margin-bottom: 15px; text-align: center; border-bottom: 1px solid #FFD700; padding-bottom: 10px;'>Tiempo Total Calculado</h4>
            <div style='margin-bottom: 15px;'>
                <p style='margin: 0; color: #FFFFFF; font-size: 0.9em;'>👨‍🏫 Como Docente</p>
                <p style='margin: 0; color: #FFD700; font-size: 1.2em; font-weight: bold;'>{formato_tiempo(meses_docente)}</p>
            </div>
            <div style='margin-bottom: 15px;'>
                <p style='margin: 0; color: #FFFFFF; font-size: 0.9em;'>💼 Como Administrativo</p>
                <p style='margin: 0; color: #FFD700; font-size: 1.2em; font-weight: bold;'>{formato_tiempo(meses_admin)}</p>
            </div>
            <div style='margin-top: 15px; padding-top: 10px; border-top: 1px solid #FFD700;'>
                <p style='margin: 0; color: #FFFFFF; font-size: 0.9em;'>🌟 Experiencia General</p>
                <p style='margin: 0; color: #00FF00; font-size: 1.4em; font-weight: bold;'>{formato_tiempo(meses_docente + meses_admin)}</p>
            </div>
        </div>
        """
        st.markdown(html_resumen, unsafe_allow_html=True)

    # --- SECCIÓN DE GESTIÓN DE BD ---
    st.markdown("<br>", unsafe_allow_html=True)

    def actualizar_y_guardar_bd(df_modificado_usuario):
        df_mod_clean = normalizar_df_exp(df_modificado_usuario)
        df_otros = df_exp_general[
            df_exp_general["DNI"].astype(str) != str(dni_buscado)
        ]
        df_final = pd.concat([df_otros, df_mod_clean], ignore_index=True)
        df_final = normalizar_df_exp(df_final)

        dfs["EXP. LABORAL"] = df_final
        if "dfs" not in st.session_state:
            st.session_state["dfs"] = {}
        st.session_state["dfs"]["EXP. LABORAL"] = df_final

        try:
            st.cache_data.clear()
        except Exception:
            pass

        try:
            exportar_df_a_sheets(df_final, "EXP. LABORAL")
            return True, "✅ ¡Guardado en Google Sheets con éxito!"
        except Exception as e:
            return False, f"⚠️ Error al guardar en Google Sheets: {e}"

    # 1. FORMULARIO NUEVO REGISTRO
    with st.expander("➕ Nuevo Registro de Experiencia Externa", expanded=True):
        with st.form(
            key=f"form_nueva_exp_{dni_buscado}", clear_on_submit=True
        ):
            st.markdown(
                "<h4 style='color: #4A0000;'>Ingresa los datos de la nueva experiencia laboral</h4>",
                unsafe_allow_html=True,
            )

            c_f1, c_f2 = st.columns(2)
            with c_f1:
                nuevo_puesto = st.text_input(
                    "Puesto / Cargo *",
                    placeholder="Escribe el puesto aquí",
                    key=f"inp_puesto_{dni_buscado}",
                )
                nuevo_lugar = st.text_input(
                    "Lugar / Empresa / Institución *",
                    placeholder="Escribe la empresa aquí",
                    key=f"inp_lugar_{dni_buscado}",
                )
                tipo_exp_opt = st.selectbox(
                    "Tipo de Experiencia *",
                    ["Administrativo", "Docente"],
                    key=f"inp_tipo_{dni_buscado}",
                )

            with c_f2:
                f_inicio = st.date_input(
                    "Fecha de Inicio",
                    value=date.today(),
                    min_value=date(1950, 1, 1),
                    max_value=date(2100, 12, 31),
                    key=f"inp_fini_{dni_buscado}",
                )
                f_fin = st.date_input(
                    "Fecha de Fin",
                    value=date.today(),
                    min_value=date(1950, 1, 1),
                    max_value=date(2100, 12, 31),
                    key=f"inp_ffin_{dni_buscado}",
                )
                motivo_cese = st.text_input(
                    "Motivo de Cese",
                    placeholder="Motivo de salida",
                    key=f"inp_motivo_{dni_buscado}",
                )

            btn_guardar = st.form_submit_button(
                "💾 Registrar en EXP. LABORAL", use_container_width=True
            )

            if btn_guardar:
                puesto_clean = nuevo_puesto.strip()
                lugar_clean = nuevo_lugar.strip()

                if not puesto_clean or not lugar_clean:
                    st.error("⚠️ Debes escribir un Puesto y un Lugar válidos.")
                else:
                    nueva_fila_dict = {
                        "id": str(uuid.uuid4()),
                        "DNI": str(dni_buscado),
                        "PUESTO": puesto_clean,
                        "LUGAR": lugar_clean,
                        "TIPO DE EXPERIENCIA": tipo_exp_opt,
                        "FECHA DE INICIO": (
                            f_inicio.strftime("%Y-%m-%d") if f_inicio else ""
                        ),
                        "FECHA DE FIN": (
                            f_fin.strftime("%Y-%m-%d") if f_fin else ""
                        ),
                        "MOTIVO DE CESE": motivo_cese.strip(),
                    }

                    nueva_fila = pd.DataFrame([nueva_fila_dict])
                    df_actualizado_usuario = pd.concat(
                        [
                            vst_df.drop(columns=["SEL"], errors="ignore"),
                            nueva_fila,
                        ],
                        ignore_index=True,
                    )

                    exito, msg = actualizar_y_guardar_bd(df_actualizado_usuario)
                    if exito:
                        st.success(msg)
                    else:
                        st.warning(msg)
                    st.rerun()

    # 2. EDICIÓN / ELIMINACIÓN DE REGISTROS
    with st.expander(
        "⚙️ Clic aquí para Editar o Eliminar Experiencia Externa"
    ):
        st.markdown(
            "<p style='color:#DDDDDD;'>Modifica los valores en la tabla o marca la casilla <b>SEL</b> para eliminar.</p>",
            unsafe_allow_html=True,
        )

        ed = st.data_editor(
            vst_df,
            hide_index=True,
            use_container_width=True,
            key=f"data_editor_exp_{dni_buscado}",
            column_config={
                "id": None,
                "SEL": st.column_config.CheckboxColumn("SEL", default=False),
            },
        )

        col_b1, col_b2 = st.columns(2)

        with col_b1:
            if st.button(
                "✏️ Guardar Cambios Editados en Tabla",
                type="secondary",
                use_container_width=True,
                key=f"btn_save_table_{dni_buscado}",
            ):
                ed_normalizado = normalizar_df_exp(ed)
                ed_normalizado["DNI"] = str(dni_buscado)

                exito, msg = actualizar_y_guardar_bd(ed_normalizado)
                if exito:
                    st.success(msg)
                else:
                    st.warning(msg)
                st.rerun()

        with col_b2:
            if "SEL" in ed.columns:
                sel = ed[ed["SEL"] == True]
                if not sel.empty:
                    if st.button(
                        "🗑️ Eliminar Seleccionados",
                        type="primary",
                        use_container_width=True,
                        key=f"btn_del_table_{dni_buscado}",
                    ):
                        ed_filtrado = ed.drop(
                            sel.index, errors="ignore"
                        ).copy()
                        ed_normalizado = normalizar_df_exp(ed_filtrado)
                        ed_normalizado["DNI"] = str(dni_buscado)

                        exito, msg = actualizar_y_guardar_bd(ed_normalizado)
                        if exito:
                            st.success(
                                "✅ Registro eliminado de Google Sheets."
                            )
                        else:
                            st.warning(msg)
                        st.rerun()

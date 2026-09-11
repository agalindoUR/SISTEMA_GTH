import os
import streamlit as st
import pandas as pd
from datetime import date, datetime
from io import BytesIO
from docx import Document

def gen_papeleta_vac(apellidos, nombres, dni_b, position, f_ingreso, period, start_d, end_d, days):
    if not os.path.exists("Template_Papeleta.docx"):
        return st.error("⚠️ No se encontró la plantilla 'Template_Papeleta.docx'.")

    doc = Document("Template_Papeleta.docx")
    fin_dt = pd.to_datetime(end_d, errors="coerce")
    retorno_dt = (fin_dt + pd.Timedelta(days=1 if fin_dt.weekday() < 5 else (2 if fin_dt.weekday() == 5 else 1))) if pd.notna(fin_dt) else None
  
    hoy = date.today()
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
  
    reps = {
        "{{APELLIDOS}}": str(apellidos).upper(), "{{NOMBRES}}": str(nombres).upper(),
        "{{DNI}}": str(dni_b), "{{CARGO}}": str(position).upper(),
        "{{F_INGRESO}}": f_ingreso.strftime("%d/%m/%Y") if isinstance(f_ingreso, (date, datetime)) else str(f_ingreso),
        "{{PERIODO}}": str(period), "{{DIAS}}": str(days),
        "{{F_INICIO}}": start_d.strftime("%d/%m/%Y") if isinstance(start_d, (date, datetime)) else str(start_d),
        "{{F_FIN}}": end_d.strftime("%d/%m/%Y") if isinstance(end_d, (date, datetime)) else str(end_d),
        "{{F_RETORNO}}": retorno_dt.strftime("%d/%m/%Y") if retorno_dt else "",
        "{{FECHA_FIRMA}}": f"Huancayo, {hoy.day} de {meses[hoy.month-1]} de {hoy.year}"
    }

    def replace_text(element):
        for run in element.runs:
            for k, v in reps.items():
                if k in run.text: run.text = run.text.replace(k, v)

    for p in doc.paragraphs: replace_text(p)
    for t in doc.tables:
        for r in t.rows:
            for c in r.cells:
                for p in c.paragraphs: replace_text(p)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
# =========================================================================
# 🏖️ PESTAÑA: VACACIONES (Lógica Integrada)
# =========================================================================
elif h_name == "VACACIONES":
    df_contratos_base = dfs.get("CONTRATOS", pd.DataFrame())

    # Detectar dinámicamente columna DNI en Contratos
    col_dni_cb = (
        next(
            (
                c
                for c in df_contratos_base.columns
                if str(c).strip().lower() == "dni"
            ),
            None,
        )
        if not df_contratos_base.empty
        else None
    )

    df_contratos = (
        df_contratos_base[
            df_contratos_base[col_dni_cb].astype(str).str.strip()
            == str(dni_buscado).strip()
        ]
        if not df_contratos_base.empty and col_dni_cb
        else pd.DataFrame()
    )

    # Detectar dinámicamente columna 'tipo contrato'
    col_tipo_cont = (
        next(
            (
                c
                for c in df_contratos.columns
                if "tipo" in str(c).strip().lower()
                and "contrato" in str(c).strip().lower()
            ),
            None,
        )
        if not df_contratos.empty
        else None
    )

    df_tc = (
        df_contratos[
            df_contratos[col_tipo_cont]
            .astype(str)
            .str.lower()
            .str.contains("planilla", na=False)
        ]
        if not df_contratos.empty and col_tipo_cont
        else pd.DataFrame()
    )

    detalles = []
    dias_generados_totales = 0

    # Detectar dinámicamente columnas en c_df (vacaciones del trabajador)
    col_gozados = (
        next(
            (
                c
                for c in c_df.columns
                if "gozad" in str(c).strip().lower()
                or (
                    "dias" in str(c).strip().lower()
                    and "goz" in str(c).strip().lower()
                )
            ),
            None,
        )
        if not c_df.empty
        else None
    )

    col_periodo = (
        next(
            (c for c in c_df.columns if "periodo" in str(c).strip().lower()),
            None,
        )
        if not c_df.empty
        else None
    )

    dias_gozados_totales = (
        pd.to_numeric(c_df[col_gozados], errors="coerce").sum()
        if not c_df.empty and col_gozados
        else 0
    )

    if not df_tc.empty:
        df_tc_calc = df_tc.copy()

        # Detectar dinámicamente columnas de inicio y fin de contrato
        col_ini_tc = next(
            (
                c
                for c in df_tc_calc.columns
                if any(
                    k in str(c).strip().lower()
                    for k in [
                        "f_inicio",
                        "fecha_inicio",
                        "fecha inicio",
                        "inicio",
                    ]
                )
            ),
            None,
        )
        col_fin_tc = next(
            (
                c
                for c in df_tc_calc.columns
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

        df_tc_calc["f_inicio_dt"] = (
            pd.to_datetime(
                df_tc_calc[col_ini_tc], errors="coerce", dayfirst=True
            )
            if col_ini_tc
            else pd.NaT
        )
        df_tc_calc["f_fin_dt"] = (
            pd.to_datetime(
                df_tc_calc[col_fin_tc], errors="coerce", dayfirst=True
            )
            if col_fin_tc
            else pd.NaT
        )

        start_global = df_tc_calc["f_inicio_dt"].min()

        if pd.notnull(start_global):
            curr_start = start_global.date()

            while curr_start <= date.today():
                curr_end = (
                    pd.to_datetime(curr_start)
                    + pd.DateOffset(years=1)
                    - pd.Timedelta(days=1)
                ).date()
                days_in_p = 0

                for _, r in df_tc_calc.iterrows():
                    c_start = (
                        r["f_inicio_dt"].date()
                        if pd.notnull(r["f_inicio_dt"])
                        else None
                    )
                    c_end = (
                        r["f_fin_dt"].date()
                        if pd.notnull(r["f_fin_dt"])
                        else None
                    )

                    if c_start and c_end:
                        o_start = max(curr_start, c_start)
                        o_end = min(curr_end, c_end, date.today())
                        if o_start <= o_end:
                            days_in_p += (o_end - o_start).days + 1

                total_dias_periodo = (curr_end - curr_start).days + 1
                gen_p = round((days_in_p / total_dias_periodo) * 30, 2)
                p_name = f"{curr_start.year}-{curr_start.year + 1}"

                goz_p = 0
                if not c_df.empty and col_periodo and col_gozados:
                    goz_df = c_df[
                        c_df[col_periodo].astype(str).str.strip() == p_name
                    ]
                    goz_p = pd.to_numeric(
                        goz_df[col_gozados], errors="coerce"
                    ).sum()

                if gen_p > 0 or goz_p > 0:
                    detalles.append(
                        {
                            "Periodo": p_name,
                            "Del": curr_start.strftime("%d/%m/%Y"),
                            "Al": curr_end.strftime("%d/%m/%Y"),
                            "Días Generados": gen_p,
                            "Dias Gozados": goz_p,
                            "Saldo": round(gen_p - goz_p, 2),
                        }
                    )

                dias_generados_totales += gen_p
                curr_start = (
                    pd.to_datetime(curr_start) + pd.DateOffset(years=1)
                ).date()

    saldo_v = round(dias_generados_totales - dias_gozados_totales, 2)

    # Dashboard Resumen
    st.markdown(
        f"""
        <div style="display: flex; gap: 15px; margin-bottom: 20px;">
            <div style="flex: 1; background-color: #4A0000; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #FFD700;">
                <h2 style="color: #FFD700; margin: 0; font-size: 2.5em;">{dias_generados_totales:.2f}</h2>
                <p style="color: #FFFFFF; margin: 0; font-weight: bold; font-size: 1.1em;">Días Generados Totales</p>
            </div>
            <div style="flex: 1; background-color: #4A0000; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #FFD700;">
                <h2 style="color: #FFD700; margin: 0; font-size: 2.5em;">{dias_gozados_totales:.2f}</h2>
                <p style="color: #FFFFFF; margin: 0; font-weight: bold; font-size: 1.1em;">Dias Gozados</p>
            </div>
            <div style="flex: 1; background-color: #4A0000; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #FFD700;">
                <h2 style="color: #FFD700; margin: 0; font-size: 2.5em;">{saldo_v:.2f}</h2>
                <p style="color: #FFFFFF; margin: 0; font-weight: bold; font-size: 1.1em;">Saldo Disponible</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Tabla Desglose
    if detalles:
        st.markdown(
            "<h4 style='color: #FFD700;'>Desglose por Periodos</h4>",
            unsafe_allow_html=True,
        )
        div_table = (
            "<div style='display: flex; flex-direction: column; width: 100%; border: 2px solid #FFD700; border-radius: 8px; overflow: hidden; margin-bottom: 20px;'>"
            "<div style='display: flex; background-color: #4A0000; color: #FFD700; font-weight: bold;'>"
            "<div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>PERIODO</div>"
            "<div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>DEL</div>"
            "<div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>AL</div>"
            "<div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>DÍAS GENERADOS</div>"
            "<div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>DIAS GOZADOS</div>"
            "<div style='flex: 1; padding: 12px; text-align: center;'>SALDO</div></div>"
        )
        for d in detalles:
            div_table += (
                f"<div style='display: flex; background-color: #FFF9C4; color: #4A0000; font-weight: bold; border-top: 1px solid #FFD700;'>"
                f"<div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Periodo']}</div>"
                f"<div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Del']}</div>"
                f"<div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Al']}</div>"
                f"<div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Días Generados']:.2f}</div>"
                f"<div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Dias Gozados']:.2f}</div>"
                f"<div style='flex: 1; padding: 10px; text-align: center;'>{d['Saldo']:.2f}</div></div>"
            )
        div_table += "</div>"
        st.markdown(div_table, unsafe_allow_html=True)

    # Preparación de DataFrame editable (Combina Parte 2 y Parte 3)
    if not c_df.empty:
        vst = c_df.copy()
        cols_ocultar = [
            c
            for c in vst.columns
            if str(c).strip().lower()
            in ["apellidos y nombres", "apellidos", "nombres"]
        ]
        vst = vst.drop(columns=cols_ocultar)

        col_conf = {}
        for col in vst.columns:
            col_lower = str(col).lower()
            if "fecha" in col_lower or "f_" in col_lower:
                vst[col] = pd.to_datetime(
                    vst[col], errors="coerce", dayfirst=True
                ).dt.date
                col_conf[str(col).upper()] = st.column_config.DateColumn(
                    format="DD/MM/YYYY",
                    min_value=date(1950, 1, 1),
                    max_value=date(2100, 12, 31),
                )
            elif col_lower.strip() == "periodo":
                vst[col] = vst[col].astype(str)
                col_conf[str(col).upper()] = st.column_config.TextColumn()

        vst.columns = [str(col).upper() for col in vst.columns]
        vst = vst.loc[:, ~vst.columns.duplicated()]

        # Insertar columna 'SEL' si no existe
        if "SEL" not in vst.columns:
            vst.insert(0, "SEL", False)

        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("⚙️ Clic aquí para ver el Detalle Completo, Editar o Eliminar Vacaciones"):
            st.markdown("<p style='color:#000000; background-color:#FFD700; padding:5px; border-radius:5px;'><b>Detalle de registros:</b> Activa la casilla <b>SEL</b> para modificar, eliminar o imprimir papeleta.</p>", unsafe_allow_html=True)
            st.markdown("""<style>[data-testid="stDataEditor"] { border: 2px solid #FFD700 !important; border-radius: 8px !important; }</style>""", unsafe_allow_html=True)
            
            # Data Editor
            ed = st.data_editor(
                vst, 
                hide_index=True, 
                use_container_width=True, 
                column_config=col_conf, 
                key=f"ed_{h_name}_oculta"
            )
            
            sel_vac = ed[ed["SEL"] == True]
        
        # Lógica para Papeleta mediante Selección (Parte 3)
        if not sel_vac.empty:
            st.markdown("---")
            current_cargo = "TRABAJADOR"
            f_ingreso_val = ""
            df_c_data = dfs.get("CONTRATOS", pd.DataFrame())
            if not df_c_data.empty and 'dni' in df_c_data.columns:
                df_c_data = df_c_data[df_c_data["dni"].astype(str).str.strip() == str(dni_buscado).strip()]
            
            if not df_c_data.empty:
                try:
                    last_contract = df_c_data.assign(f_fin_dt=pd.to_datetime(df_c_data['f_fin'], errors='coerce')).sort_values('f_fin_dt').iloc[-1]
                    current_cargo = last_contract.get("cargo", "TRABAJADOR")
                    
                    df_planilla = df_c_data[df_c_data["tipo contrato"].astype(str).str.lower().str.contains("planilla", na=False)]
                    if not df_planilla.empty:
                        f_min = pd.to_datetime(df_planilla['f_inicio'], errors='coerce').min()
                        if pd.notnull(f_min): 
                            f_ingreso_val = f_min.date()```python
# =========================================================================
# 🏖️ PESTAÑA: VACACIONES (DISEÑO INTEGRADO Y LÓGICA DE PAPELETA DINÁMICA)
# =========================================================================
elif h_name == "VACACIONES":
    df_contratos_base = dfs.get("CONTRATOS", pd.DataFrame())

    # Detectar dinámicamente columna DNI en Contratos
    col_dni_cb = (
        next((c for c in df_contratos_base.columns if str(c).strip().lower() == "dni"), None)
        if not df_contratos_base.empty else None
    )

    df_contratos = (
        df_contratos_base[df_contratos_base[col_dni_cb].astype(str).str.strip() == str(dni_buscado).strip()]
        if not df_contratos_base.empty and col_dni_cb else pd.DataFrame()
    )

    # Detectar dinámicamente columna 'tipo contrato'
    col_tipo_cont = (
        next((c for c in df_contratos.columns if "tipo" in str(c).strip().lower() and "contrato" in str(c).strip().lower()), None)
        if not df_contratos.empty else None
    )

    df_tc = (
        df_contratos[df_contratos[col_tipo_cont].astype(str).str.lower().str.contains("planilla", na=False)]
        if not df_contratos.empty and col_tipo_cont else pd.DataFrame()
    )

    detalles = []
    dias_generados_totales = 0

    # Detectar dinámicamente columnas en c_df (vacaciones del trabajador)
    col_gozados = (
        next((c for c in c_df.columns if "gozad" in str(c).strip().lower() or ("dias" in str(c).strip().lower() and "goz" in str(c).strip().lower())), None)
        if not c_df.empty else None
    )

    col_periodo = (
        next((c for c in c_df.columns if "periodo" in str(c).strip().lower()), None)
        if not c_df.empty else None
    )

    dias_gozados_totales = (
        pd.to_numeric(c_df[col_gozados], errors="coerce").sum()
        if not c_df.empty and col_gozados else 0
    )

    if not df_tc.empty:
        df_tc_calc = df_tc.copy()

        # Detectar dinámicamente columnas de inicio y fin de contrato
        col_ini_tc = next((c for c in df_tc_calc.columns if any(k in str(c).strip().lower() for k in ["f_inicio", "fecha_inicio", "fecha inicio", "inicio"])), None)
        col_fin_tc = next((c for c in df_tc_calc.columns if any(k in str(c).strip().lower() for k in ["f_fin", "fecha_fin", "fecha fin", "fin", "termino"])), None)

        df_tc_calc["f_inicio_dt"] = pd.to_datetime(df_tc_calc[col_ini_tc], errors="coerce", dayfirst=True) if col_ini_tc else pd.NaT
        df_tc_calc["f_fin_dt"] = pd.to_datetime(df_tc_calc[col_fin_tc], errors="coerce", dayfirst=True) if col_fin_tc else pd.NaT

        start_global = df_tc_calc["f_inicio_dt"].min()

        if pd.notnull(start_global):
            curr_start = start_global.date()

            while curr_start <= date.today():
                curr_end = (pd.to_datetime(curr_start) + pd.DateOffset(years=1) - pd.Timedelta(days=1)).date()
                days_in_p = 0

                for _, r in df_tc_calc.iterrows():
                    c_start = r["f_inicio_dt"].date() if pd.notnull(r["f_inicio_dt"]) else None
                    c_end = r["f_fin_dt"].date() if pd.notnull(r["f_fin_dt"]) else None

                    if c_start and c_end:
                        o_start = max(curr_start, c_start)
                        o_end = min(curr_end, c_end, date.today())
                        if o_start <= o_end:
                            days_in_p += (o_end - o_start).days + 1

                total_dias_periodo = (curr_end - curr_start).days + 1
                gen_p = round((days_in_p / total_dias_periodo) * 30, 2)
                p_name = f"{curr_start.year}-{curr_start.year + 1}"

                goz_p = 0
                if not c_df.empty and col_periodo and col_gozados:
                    goz_df = c_df[c_df[col_periodo].astype(str).str.strip() == p_name]
                    goz_p = pd.to_numeric(goz_df[col_gozados], errors="coerce").sum()

                if gen_p > 0 or goz_p > 0:
                    detalles.append({
                        "Periodo": p_name,
                        "Del": curr_start.strftime("%d/%m/%Y"),
                        "Al": curr_end.strftime("%d/%m/%Y"),
                        "Días Generados": gen_p,
                        "Dias Gozados": goz_p,
                        "Saldo": round(gen_p - goz_p, 2),
                    })

                dias_generados_totales += gen_p
                curr_start = (pd.to_datetime(curr_start) + pd.DateOffset(years=1)).date()

    saldo_v = round(dias_generados_totales - dias_gozados_totales, 2)

    st.markdown(
        f"""
        <div style="display: flex; gap: 15px; margin-bottom: 20px;">
            <div style="flex: 1; background-color: #4A0000; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #FFD700;">
                <h2 style="color: #FFD700; margin: 0; font-size: 2.5em;">{dias_generados_totales:.2f}</h2>
                <p style="color: #FFFFFF; margin: 0; font-weight: bold; font-size: 1.1em;">Días Generados Totales</p>
            </div>
            <div style="flex: 1; background-color: #4A0000; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #FFD700;">
                <h2 style="color: #FFD700; margin: 0; font-size: 2.5em;">{dias_gozados_totales:.2f}</h2>
                <p style="color: #FFFFFF; margin: 0; font-weight: bold; font-size: 1.1em;">Dias Gozados</p>
            </div>
            <div style="flex: 1; background-color: #4A0000; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #FFD700;">
                <h2 style="color: #FFD700; margin: 0; font-size: 2.5em;">{saldo_v:.2f}</h2>
                <p style="color: #FFFFFF; margin: 0; font-weight: bold; font-size: 1.1em;">Saldo Disponible</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if detalles:
        st.markdown("<h4 style='color: #FFD700;'>Desglose por Periodos</h4>", unsafe_allow_html=True)
        div_table = (
            "<div style='display: flex; flex-direction: column; width: 100%; border: 2px solid #FFD700; border-radius: 8px; overflow: hidden; margin-bottom: 20px;'>"
            "<div style='display: flex; background-color: #4A0000; color: #FFD700; font-weight: bold;'>"
            "<div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>PERIODO</div>"
            "<div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>DEL</div>"
            "<div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>AL</div>"
            "<div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>DÍAS GENERADOS</div>"
            "<div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>DIAS GOZADOS</div>"
            "<div style='flex: 1; padding: 12px; text-align: center;'>SALDO</div></div>"
        )
        for d in detalles:
            div_table += (
                f"<div style='display: flex; background-color: #FFF9C4; color: #4A0000; font-weight: bold; border-top: 1px solid #FFD700;'>"
                f"<div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Periodo']}</div>"
                f"<div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Del']}</div>"
                f"<div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Al']}</div>"
                f"<div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Días Generados']:.2f}</div>"
                f"<div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Dias Gozados']:.2f}</div>"
                f"<div style='flex: 1; padding: 10px; text-align: center;'>{d['Saldo']:.2f}</div></div>"
            )
        div_table += "</div>"
        st.markdown(div_table, unsafe_allow_html=True)

    if not c_df.empty:
        vst = c_df.copy()
        cols_ocultar = [c for c in vst.columns if str(c).strip().lower() in ["apellidos y nombres", "apellidos", "nombres"]]
        vst = vst.drop(columns=cols_ocultar)
        
        # Asegurar que exista la columna SEL para el editor interactivo
        if "SEL" not in vst.columns:
            vst.insert(0, "SEL", False)

        col_conf = {"SEL": st.column_config.CheckboxColumn("SEL", default=False)}
        
        for col in vst.columns:
            if col == "SEL": continue
            col_lower = str(col).lower()
            if "fecha" in col_lower or "f_" in col_lower:
                vst[col] = pd.to_datetime(vst[col], errors="coerce", dayfirst=True).dt.date
                col_conf[str(col).upper()] = st.column_config.DateColumn(
                    format="DD/MM/YYYY",
                    min_value=date(1950, 1, 1),
                    max_value=date(2100, 12, 31),
                )
            elif col_lower.strip() == "periodo":
                vst[col] = vst[col].astype(str)
                col_conf[str(col).upper()] = st.column_config.TextColumn()

        vst.columns = [str(col).upper() for col in vst.columns]
        vst = vst.loc[:, ~vst.columns.duplicated()]

        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("⚙️ Clic aquí para ver el Detalle Completo, Editar o Eliminar Vacaciones"):
            st.markdown("<p style='color:#000000; background-color:#FFD700; padding:5px; border-radius:5px;'><b>Detalle de registros:</b> Activa la casilla <b>SEL</b> para generar papeleta, modificar o eliminar un registro.</p>", unsafe_allow_html=True)
            st.markdown("""<style>[data-testid="stDataEditor"] { border: 2px solid #FFD700 !important; border-radius: 8px !important; }</style>""", unsafe_allow_html=True)
            
            ed = st.data_editor(vst, hide_index=True, use_container_width=True, column_config=col_conf, key=f"ed_{h_name}_oculta")
        
        # Extraer selección para generar papeleta interactiva
        sel_vac = ed[ed["SEL"] == True] if "SEL" in ed.columns else pd.DataFrame()

        if not sel_vac.empty:
            st.markdown("---")
            st.markdown("### 📄 Generar Papeleta de Vacaciones Seleccionada")
            
            current_cargo = "TRABAJADOR"
            f_ingreso_val = ""
            
            # Extraer datos dinámicos del contrato para la papeleta
            if not df_contratos.empty:
                try:
                    col_cargo_pap = next((c for c in df_contratos.columns if any(k in str(c).strip().lower() for k in ["cargo", "puesto"])), None)
                    if col_cargo_pap:
                        last_contract = df_contratos.assign(f_fin_dt=pd.to_datetime(df_contratos[col_fin_tc], errors='coerce')).sort_values('f_fin_dt').iloc[-1]
                        current_cargo = last_contract.get(col_cargo_pap, "TRABAJADOR")
                    
                    if not df_tc.empty and col_ini_tc:
                        f_min = pd.to_datetime(df_tc[col_ini_tc], errors='coerce', dayfirst=True).min()
                        if pd.notnull(f_min): 
                            f_ingreso_val = f_min.date()
                except Exception as e:
                    st.warning(f"No se pudieron consolidar los contratos para la papeleta: {e}")

            r_sel = sel_vac.iloc[0]
            
            cols_per = [c for c in r_sel.index if "PERIODO" in str(c).upper()]
            cols_ini = [c for c in r_sel.index if "INICIO" in str(c).upper()]
            cols_fin = [c for c in r_sel.index if "FIN" in str(c).upper()]
            cols_dias = [c for c in r_sel.index if "GOZADOS" in str(c).upper()]

            def get_valid_val(cols):
                for c in cols:
                    val = r_sel.get(c)
                    if pd.notnull(val) and str(val).strip() not in ["", "NaT", "None"]:
                        return val
                return None

            p_papeleta = str(get_valid_val(cols_per) or "")
            fi_papeleta_raw = get_valid_val(cols_ini)
            ff_papeleta_raw = get_valid_val(cols_fin)
            dg_papeleta_raw = get_valid_val(cols_dias) or 0
            
            try:
                fi_papeleta = pd.to_datetime(fi_papeleta_raw).date() if fi_papeleta_raw else None
            except Exception:
                fi_papeleta = None
                
            try:
                ff_papeleta = pd.to_datetime(ff_papeleta_raw).date() if ff_papeleta_raw else None
            except Exception:
                ff_papeleta = None

            try:
                dg_papeleta = int(float(dg_papeleta_raw))
            except (ValueError, TypeError):
                dg_papeleta = 0

            if st.button(f"📄 Generar Papeleta de Impresión (Periodo {p_papeleta})", key="btn_print_vaca_tab", use_container_width=False):
                if fi_papeleta is None or ff_papeleta is None:
                    st.error(f"⚠️ Aún no se detectan fechas válidas en la fila seleccionada. Inicio extraído: '{fi_papeleta_raw}' | Fin extraído: '{ff_papeleta_raw}'")
                else:
                    papeleta_word = gen_papeleta_vac(ape_c, nom_p_c, dni_buscado, current_cargo, f_ingreso_val, p_papeleta, fi_papeleta, ff_papeleta, dg_papeleta)
                    if papeleta_word:
                        st.markdown("""<style>[data-testid="stDownloadButton"] button { background-color: #FFD700 !important; color: #4A0000 !important; font-weight: bold !important; border: 2px solid #4A0000 !important; width: 100% !important; }</style>""", unsafe_allow_html=True)
                        st.download_button(
                            label=f"⬇️ Descargar Papeleta - {nom_c if 'nom_c' in locals() else dni_buscado}.docx",
                            data=papeleta_word,
                            file_name=f"Papeleta_{dni_buscado}_{p_papeleta}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key="dl_papeleta_tab"
                        )
            st.markdown("---")

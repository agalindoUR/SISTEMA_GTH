import streamlit as st
import pandas as pd
from datetime import date, datetime

def calcular_vacaciones(c_df, df_contratos):
    # Filtramos los contratos de "planilla"
    df_tc = df_contratos[df_contratos["tipo contrato"].astype(str).str.lower().str.contains("planilla", na=False)] if not df_contratos.empty else pd.DataFrame()
    
    detalles = []
    dias_generados_totales = 0
    dias_gozados_totales = pd.to_numeric(c_df["dias gozados"], errors='coerce').sum()

    if not df_tc.empty:
        df_tc_calc = df_tc.copy()
        df_tc_calc['f_inicio_dt'] = pd.to_datetime(df_tc_calc['f_inicio'], errors='coerce')
        df_tc_calc['f_fin_dt'] = pd.to_datetime(df_tc_calc['f_fin'], errors='coerce')
        
        start_global = df_tc_calc['f_inicio_dt'].min()
        
        if pd.notnull(start_global):
            start_global = start_global.date()
            curr_start = start_global
            
            while curr_start <= date.today():
                curr_end = (pd.to_datetime(curr_start) + pd.DateOffset(years=1) - pd.Timedelta(days=1)).date()
                days_in_p = 0
                
                for _, r in df_tc_calc.iterrows():
                    c_start = r['f_inicio_dt'].date() if pd.notnull(r['f_inicio_dt']) else None
                    c_end = r['f_fin_dt'].date() if pd.notnull(r['f_fin_dt']) else None
                    if c_start and c_end:
                        o_start = max(curr_start, c_start)
                        o_end = min(curr_end, c_end, date.today())
                        if o_start <= o_end: 
                            days_in_p += (o_end - o_start).days + 1
                
                # CÁLCULO PROPORCIONAL EXACTO
                total_dias_periodo = (curr_end - curr_start).days + 1
                gen_p = round((days_in_p / total_dias_periodo) * 30, 2)
                
                p_name = f"{curr_start.year}-{curr_start.year+1}"
                goz_df = c_df[c_df["periodo"].astype(str).str.strip() == p_name]
                goz_p = pd.to_numeric(goz_df["dias gozados"], errors='coerce').sum()
                
                if gen_p > 0 or goz_p > 0:
                    detalles.append({"Periodo": p_name, "Del": curr_start.strftime("%d/%m/%Y"), "Al": curr_end.strftime("%d/%m/%Y"), "Días Generados": gen_p, "Dias Gozados": goz_p, "Saldo": round(gen_p - goz_p, 2)})
                
                dias_generados_totales += gen_p
                curr_start = (pd.to_datetime(curr_start) + pd.DateOffset(years=1)).date()

    saldo_v = round(dias_generados_totales - dias_gozados_totales, 2)

    st.markdown(f"""
    <div style="display: flex; gap: 15px; margin-bottom: 20px;">
        <div style="flex: 1; background-color: #4A0000; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #FFD700;"><h2 style="color: #FFD700; margin: 0; font-size: 2.5em;">{dias_generados_totales:.2f}</h2><p style="color: #FFFFFF; margin: 0; font-weight: bold; font-size: 1.1em;">Días Generados Totales</p></div>
        <div style="flex: 1; background-color: #4A0000; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #FFD700;"><h2 style="color: #FFD700; margin: 0; font-size: 2.5em;">{dias_gozados_totales:.2f}</h2><p style="color: #FFFFFF; margin: 0; font-weight: bold; font-size: 1.1em;">Dias Gozados</p></div>
        <div style="flex: 1; background-color: #4A0000; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #FFD700;"><h2 style="color: #FFD700; margin: 0; font-size: 2.5em;">{saldo_v:.2f}</h2><p style="color: #FFFFFF; margin: 0; font-weight: bold; font-size: 1.1em;">Saldo Disponible</p></div>
    </div>
    """, unsafe_allow_html=True)
    
    if detalles:
        st.markdown("<h4 style='color: #FFD700;'>Desglose por Periodos</h4>", unsafe_allow_html=True)
        div_table = "<div style='display: flex; flex-direction: column; width: 100%; border: 2px solid #FFD700; border-radius: 8px; overflow: hidden; margin-bottom: 20px;'><div style='display: flex; background-color: #4A0000; color: #FFD700; font-weight: bold;'><div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>PERIODO</div><div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>DEL</div><div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>AL</div><div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>DÍAS GENERADOS</div><div style='flex: 1; padding: 12px; text-align: center; border-right: 1px solid #FFD700;'>DIAS GOZADOS</div><div style='flex: 1; padding: 12px; text-align: center;'>SALDO</div></div>"
        for d in detalles:
            div_table += f"<div style='display: flex; background-color: #FFF9C4; color: #4A0000; font-weight: bold; border-top: 1px solid #FFD700;'><div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Periodo']}</div><div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Del']}</div><div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Al']}</div><div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Días Generados']:.2f}</div><div style='flex: 1; padding: 10px; text-align: center; border-right: 1px solid #FFD700;'>{d['Dias Gozados']:.2f}</div><div style='flex: 1; padding: 10px; text-align: center;'>{d['Saldo']:.2f}</div></div>"
        div_table += "</div>"
        st.markdown(div_table, unsafe_allow_html=True)


def mostrar_experiencia(vst, dfs, h_name, col_conf, dni_buscado):
    # Dividimos la pantalla
    col_izq, col_der = st.columns([2, 1])
    
    df_contratos = dfs.get("CONTRATOS", pd.DataFrame())
    col_dni_contratos = "DNI" if "DNI" in df_contratos.columns else "dni"
    
    contratos_empleado = pd.DataFrame()
    if not df_contratos.empty and col_dni_contratos in df_contratos.columns:
        contratos_empleado = df_contratos[df_contratos[col_dni_contratos] == str(dni_buscado)]
    
    # LÓGICA DE CÁLCULO DE TIEMPO
    meses_docente = 0
    meses_admin = 0
    
    def calcular_meses(f_ini, f_fin):
        try:
            inicio = pd.to_datetime(f_ini, errors='coerce')
            fin = pd.to_datetime(f_fin, errors='coerce')
            if pd.isna(inicio) or pd.isna(fin): return 0
            return max(0, int((fin - inicio).days / 30.44))
        except:
            return 0
            
    def dar_formato_fecha(fecha_str):
        try:
            if pd.isna(fecha_str) or str(fecha_str).strip() == "" or str(fecha_str) == "NaT": return "N/A"
            return pd.to_datetime(fecha_str).strftime('%d/%m/%Y')
        except:
            return str(fecha_str)

    # COLUMNA IZQUIERDA: TARJETAS
    with col_izq:
        st.markdown("<h3 style='color: #FFD700;'>🏢 Experiencia Interna (Universidad Roosevelt)</h3>", unsafe_allow_html=True)
        if contratos_empleado.empty:
            st.markdown("<p style='color:#DDDDDD;'>No hay contratos internos registrados.</p>", unsafe_allow_html=True)
        else:
            for idx, row in contratos_empleado.iterrows():
                f_ini = row.get('f_inicio', row.get('F_INICIO', 'N/A'))
                f_fin = row.get('f_fin', row.get('F_FIN', 'N/A'))
                f_ini_str = dar_formato_fecha(f_ini)
                f_fin_str = dar_formato_fecha(f_fin)
                puesto = row.get('cargo', row.get('CARGO', row.get('PUESTO', 'N/A')))
                tipo_trabajador_raw = str(row.get('TIPO DE TRABAJADOR', row.get('tipo de trabajador', 'Administrativo')))
                tipo_exp = "Docente" if "docente" in tipo_trabajador_raw.lower() else "Administrativo"
                
                meses_calc = calcular_meses(f_ini, f_fin)
                if tipo_exp == "Docente": meses_docente += meses_calc
                else: meses_admin += meses_calc

                st.markdown(f"""
                <div style='background-color: #F9F6EE; padding: 15px; border-radius: 8px; border-left: 6px solid #4A0000; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #CCCCCC;'>
                    <div style='color: #000000; font-size: 1.1em; font-weight: bold; margin-bottom: 5px;'>{puesto} <span style='font-size: 0.85em; color: #555555;'>(Interno - {tipo_exp})</span></div>
                    <div style='color: #222222; font-size: 0.95em;'>
                        <strong>Lugar:</strong> Universidad Roosevelt <br>
                        <strong>Periodo:</strong> {f_ini_str} al {f_fin_str} <br>
                        <strong>Tipo de Contrato:</strong> {row.get('tipo contrato', row.get('TIPO CONTRATO', 'N/A'))}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("<h3 style='color: #FFD700; margin-top: 20px;'>💼 Experiencia Externa Registrada</h3>", unsafe_allow_html=True)
        if vst.empty:
            st.markdown("<p style='color:#DDDDDD;'>No hay experiencia externa registrada.</p>", unsafe_allow_html=True)
        else:
            for idx, row in vst.iterrows():
                f_ini = row.get('FECHA DE INICIO', row.get('fecha de inicio', 'N/A'))
                f_fin = row.get('FECHA DE FIN', row.get('fecha de fin', 'N/A'))
                f_ini_str = dar_formato_fecha(f_ini)
                f_fin_str = dar_formato_fecha(f_fin)
                tipo_exp_raw = str(row.get('TIPO DE EXPERIENCIA', row.get('tipo de experiencia', 'Administrativo')))
                tipo_exp = "Docente" if "docente" in tipo_exp_raw.lower() else "Administrativo"
                
                meses_calc = calcular_meses(f_ini, f_fin)
                if tipo_exp == "Docente": meses_docente += meses_calc
                else: meses_admin += meses_calc

                puesto_ext = row.get('PUESTO', row.get('puesto', 'N/A'))
                lugar_ext = row.get('LUGAR', row.get('lugar', 'N/A'))
                motivo_ext = row.get('MOTIVO DE CESE', row.get('motivo de cese', 'N/A'))

                st.markdown(f"""
                <div style='background-color: #F9F6EE; padding: 15px; border-radius: 8px; border-left: 6px solid #004A80; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #CCCCCC;'>
                    <div style='color: #000000; font-size: 1.1em; font-weight: bold; margin-bottom: 5px;'>{puesto_ext} <span style='font-size: 0.85em; color: #555555;'>({tipo_exp.capitalize()})</span></div>
                    <div style='color: #222222; font-size: 0.95em;'>
                        <strong>Lugar:</strong> {lugar_ext} <br>
                        <strong>Periodo:</strong> {f_ini_str} al {f_fin_str} <br>
                        <strong>Motivo de cese:</strong> {motivo_ext}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
    # COLUMNA DERECHA: RESUMEN
    with col_der:
        def formato_tiempo(total_meses):
            anios = total_meses // 12
            meses = total_meses % 12
            if anios > 0 and meses > 0: return f"{anios} años y {meses} meses"
            elif anios > 0: return f"{anios} años"
            elif meses > 0: return f"{meses} meses"
            else: return "0 meses"

        st.markdown("<h3 style='color: #FFD700;'>📊 Resumen</h3>", unsafe_allow_html=True)
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

    # TABLA DE EDICIÓN
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("⚙️ Clic aquí para Editar o Eliminar Experiencia Externa"):
        st.markdown("<p style='color:#DDDDDD;'>Activa la casilla <b>SEL</b> para modificar o eliminar un registro.</p>", unsafe_allow_html=True)
        st.markdown("""<style>[data-testid="stDataEditor"] { border: 2px solid #FFD700 !important; border-radius: 10px !important; }</style>""", unsafe_allow_html=True)
        
        ed = st.data_editor(vst, hide_index=True, use_container_width=True, column_config=col_conf, key=f"ed_{h_name}_oculta")
        
        for col in ed.columns:
            if "fecha" in col.lower() or "f_" in col.lower():
                ed[col] = ed[col].astype(str).replace(["NaT", "None"], "")
                
        sel = ed[ed["SEL"] == True]
        
    return sel

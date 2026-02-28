# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import date
from io import BytesIO
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="Gestión Roosevelt", page_icon="🎓", layout="wide")

# ==========================================
# 1. CONFIGURACIÓN Y CONSTANTES
# ==========================================
DB = "DB_SISTEMA_GTH.xlsx"
F_N = "MG. ARTURO JAVIER GALINDO MARTINEZ"
F_C = "JEFE DE GESTIÓN DEL TALENTO HUMANO"

MOTIVOS_CESE = ["Término de contrato", "Renuncia", "Despido", "Mutuo acuerdo", "Fallecimiento", "Otros"]

COLUMNAS = {
    "PERSONAL": ["dni", "apellidos y nombres", "link"],
    "DATOS GENERALES": ["apellidos y nombres", "dni", "dirección", "link de dirección", "estado civil", "fecha de nacimiento", "edad"],
    "DATOS FAMILIARES": ["parentesco", "apellidos y nombres", "dni", "fecha de nacimiento", "edad", "estudios", "telefono"],
    "EXP. LABORAL": ["tipo de experiencia", "lugar", "puesto", "fecha inicio", "fecha de fin", "motivo cese"],
    "FORM. ACADEMICA": ["grado, titulo o especialización", "descripcion", "universidad", "año"],
    "INVESTIGACION": ["año publicación", "autor, coautor o asesor", "tipo de investigación publicada", "nivel de publicación", "lugar de publicación"],
    # NUEVAS COLUMNAS DE CONTRATOS APLICADAS:
    "CONTRATOS": ["id", "dni", "cargo", "remuneración básica", "bonificación", "condición de trabajo", "f_inicio", "f_fin", "tipo de trabajador", "modalidad", "temporalidad", "link", "tipo contrato", "estado", "motivo cese"],
    "VACACIONES": ["periodo", "fecha de inicio", "fecha de fin", "días generados", "días gozados", "saldo", "link"],
    "OTROS BENEFICIOS": ["periodo", "tipo de beneficio", "link"],
    "MERITOS Y DEMERITOS": ["periodo", "merito o demerito", "motivo", "link"],
    "EVALUACION DEL DESEMPEÑO": ["periodo", "merito o demerito", "motivo", "link"],
    "LIQUIDACIONES": ["periodo", "firmo", "link"]
}

# ==========================================
# 2. FUNCIONES DE DATOS Y WORD
# ==========================================
def load_data():
    if not os.path.exists(DB):
        with pd.ExcelWriter(DB) as w:
            for h, cols in COLUMNAS.items():
                pd.DataFrame(columns=cols).to_excel(w, sheet_name=h, index=False)
    dfs = {}
    with pd.ExcelFile(DB) as x:
        for h in COLUMNAS.keys():
            df = pd.read_excel(x, h) if h in x.sheet_names else pd.DataFrame(columns=COLUMNAS[h])
            df.columns = [str(c).strip().lower() for c in df.columns]
            
            # Migración de columnas antiguas a las nuevas si existen
            if h == "CONTRATOS":
                if "sueldo" in df.columns: df.rename(columns={"sueldo": "remuneración básica"}, inplace=True)
                if "tipo colaborador" in df.columns: df.rename(columns={"tipo colaborador": "tipo de trabajador"}, inplace=True)
                if "tipo" in df.columns and "tipo de trabajador" not in df.columns: df.rename(columns={"tipo": "tipo de trabajador"}, inplace=True)

            if "dni" in df.columns:
                df["dni"] = df["dni"].astype(str).str.strip().replace(r'\.0$', '', regex=True)
            
            # Asegurar todas las columnas necesarias
            for req_col in COLUMNAS[h]:
                if req_col not in df.columns: df[req_col] = None
                
            dfs[h] = df
    return dfs

def save_data(dfs):
    with pd.ExcelWriter(DB) as w:
        for h, df in dfs.items():
            df_s = df.copy()
            df_s.columns = [c.upper() for c in df_s.columns]
            df_s.to_excel(w, sheet_name=h, index=False)

def get_consolidated_contracts(df_c):
    # Función inteligente para fusionar contratos consecutivos
    if df_c.empty: return df_c
    df_c = df_c.copy()
    df_c['f_inicio'] = pd.to_datetime(df_c['f_inicio'], errors='coerce')
    df_c['f_fin'] = pd.to_datetime(df_c['f_fin'], errors='coerce')
    df_c = df_c.sort_values('f_inicio').dropna(subset=['f_inicio'])
    
    merged = []
    for _, row in df_c.iterrows():
        if not merged:
            merged.append(row.to_dict())
        else:
            last = merged[-1]
            # Si la fecha de inicio del nuevo contrato es justo un día después del fin del anterior (o antes)
            if pd.notnull(last['f_fin']) and row['f_inicio'] <= last['f_fin'] + pd.Timedelta(days=1):
                # Ampliamos la fecha final
                last['f_fin'] = max(last['f_fin'], row['f_fin']) if pd.notnull(row['f_fin']) else row['f_fin']
                # Actualizamos al cargo más reciente
                last['cargo'] = row['cargo'] 
            else:
                merged.append(row.to_dict())
    return pd.DataFrame(merged)

def gen_word(nom, dni, df_c):
    doc = Document()
    section = doc.sections[0]
    section.page_height, section.page_width = Inches(11.69), Inches(8.27)
    section.top_margin, section.bottom_margin = Inches(1.6), Inches(1.2)

    if os.path.exists("header.png"):
        p_h = section.header.paragraphs[0]
        p_h.paragraph_format.left_indent = Inches(-1.0)
        p_h.add_run().add_picture("header.png", width=Inches(8.27))

    if os.path.exists("footer.png"):
        p_f = section.footer.paragraphs[0]
        p_f.paragraph_format.left_indent = Inches(-1.0)
        p_f.add_run().add_picture("footer.png", width=Inches(8.27))

    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_tit = p_tit.add_run("CERTIFICADO DE TRABAJO")
    r_tit.bold, r_tit.font.name, r_tit.font.size = True, 'Arial', Pt(18)

    doc.add_paragraph("\nLa oficina de Gestión de Talento Humano De La Universidad Privada De Huancayo “Franklin Roosevelt”, certifica que:").alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    p_inf = doc.add_paragraph()
    p_inf.add_run("El(la) TRABAJADOR(A) ").bold = False
    p_inf.add_run(nom).bold = True
    p_inf.add_run(f", identificado(a) con DNI N° {dni}, laboró bajo el siguiente detalle:")

    # Obtenemos los contratos fusionados automáticamente
    df_merged = get_consolidated_contracts(df_c)

    t = doc.add_table(rows=1, cols=3)
    t.style = 'Table Grid'
    for i, h in enumerate(["CARGO", "FECHA INICIO", "FECHA FIN"]):
        celda = t.rows[0].cells[i]
        celda.text = h
        celda.paragraphs[0].runs[0].font.bold = True

    for _, fila in df_merged.iterrows():
        celdas = t.add_row().cells
        celdas[0].text = str(fila.get('cargo', ''))
        celdas[1].text = pd.to_datetime(fila['f_inicio']).strftime('%d/%m/%Y') if pd.notnull(fila['f_inicio']) else ""
        celdas[2].text = pd.to_datetime(fila['f_fin']).strftime('%d/%m/%Y') if pd.notnull(fila['f_fin']) else ""

    doc.add_paragraph("\nSe expide el presente a solicitud del interesado para los fines que considere convenientes.").alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    doc.add_paragraph(f"\nHuancayo, {date.today().strftime('%d/%m/%Y')}").alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f = doc.add_paragraph()
    f.alignment = WD_ALIGN_PARAGRAPH.CENTER
    f.add_run("\n\n__________________________\n" + F_N + "\n" + F_C).bold = True

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# ==========================================
# 3. ESTILOS CSS
# ==========================================
st.markdown("""
<style>
    .stApp { background-color: #4a0000 !important; }
    [data-testid="stHeader"] { display: none !important; }
    
    .stApp p, .stMarkdown p { color: #FFFFFF; } 
    .stApp h1, .stApp h2, .stApp h3 { color: #FFD700 !important; }
    
    [data-testid="stSidebar"] { background-color: #4a0000 !important; }
    [data-testid="stSidebar"] h3 { color: #FFD700 !important; font-weight: bold !important; }
    [data-testid="stSidebar"] [data-testid="stImage"] { background-color: #FFF9C4 !important; border: 4px solid #FFD700 !important; border-radius: 15px !important; padding: 10px !important; }
    div[role="radiogroup"] label { background-color: transparent !important; }
    div[role="radiogroup"] label p { color: #FFFFFF !important; font-weight: bold !important; font-size: 16px !important; }
    
    div.stButton > button, [data-testid="stFormSubmitButton"] > button { background-color: #FFD700 !important; border: 2px solid #FFFFFF !important; border-radius: 10px !important; }
    div.stButton > button p, [data-testid="stFormSubmitButton"] > button p { color: #4a0000 !important; font-weight: bold !important; font-size: 16px !important; }
    div.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover { background-color: #ffffff !important; border-color: #FFD700 !important; }

    [data-testid="stTabs"] button p { color: #FFFFFF !important; font-weight: bold !important; font-size: 16px !important; }
    [data-testid="stTabs"] button[aria-selected="true"] p { color: #FFD700 !important; }
    [data-testid="stTabs"] button[aria-selected="true"] { border-bottom-color: #FFD700 !important; }

    [data-testid="stExpander"] details { background-color: #FFF9C4 !important; border: 2px solid #FFD700 !important; border-radius: 10px !important; overflow: hidden !important; }
    [data-testid="stExpander"] summary { background-color: #FFD700 !important; padding: 10px !important; }
    [data-testid="stExpander"] summary p { color: #4a0000 !important; font-weight: bold !important; }
    
    /* Textos oscuros dentro de los formularios crema */
    [data-testid="stExpander"] label p { color: #4a0000 !important; font-weight: bold !important; }
    [data-testid="stExpander"] div[data-baseweb="input"], [data-testid="stExpander"] div[data-baseweb="select"] { border: 1px solid #4a0000 !important; }

    /* Fix para los mensajes de advertencia (Ej: Activa la casilla) */
    [data-testid="stNotification"] { background-color: #FFD700 !important; border: 1px solid #4a0000; }
    [data-testid="stNotification"] p { color: #4a0000 !important; font-weight: bold !important; font-size: 15px !important; }

    /* TABLAS INTERACTIVAS */
    [data-testid="stDataEditor"], [data-testid="stTable"], .stTable { background-color: white !important; border-radius: 10px !important; overflow: hidden !important; }
    [data-testid="stDataEditor"] .react-grid-HeaderCell span { color: #4a0000 !important; font-weight: 900 !important; font-size: 14px !important; text-transform: uppercase !important; }
    thead tr th { background-color: #FFF9C4 !important; color: #4a0000 !important; font-weight: bold !important; text-transform: uppercase !important; border: 1px solid #f0f0f0 !important; }
    
    .stApp label p { color: #FFD700 !important; font-weight: bold !important; } 
    .stApp input { color: #4a0000 !important; font-weight: bold !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 4. LÓGICA DE DATOS Y SESIÓN
# ==========================================
if "rol" not in st.session_state: st.session_state.rol = None

if st.session_state.rol is None:
    st.markdown("<h3 style='text-align: center; color: #FFD700;'>¡Tu talento es importante! :)</h3>", unsafe_allow_html=True)

    col_logo1, col_logo2, col_logo3 = st.columns([1, 1.2, 1])
    with col_logo2:
        if os.path.exists("Logo_amarillo.png"): st.image("Logo_amarillo.png", use_container_width=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        u = st.text_input("USUARIO").lower().strip()
        p = st.text_input("CONTRASEÑA", type="password")
        st.markdown('<p style="color:white; text-align:center; font-weight:bold; margin-top:15px;">Bienvenido (a) al sistema de gestión de datos de los colaboradores</p>', unsafe_allow_html=True)

        if st.button("INGRESAR"):
            if u == "admin": st.session_state.rol = "Admin"
            elif u == "supervisor" and p == "123": st.session_state.rol = "Supervisor"
            elif u == "lector" and p == "123": st.session_state.rol = "Lector"
            else: st.error("Credenciales incorrectas")

            if st.session_state.rol: st.rerun()

else:
    dfs = load_data()
    es_lector = st.session_state.rol == "Lector"

    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        col_logo_1, col_logo_2, col_logo_3 = st.columns([1, 2, 1]) 
        with col_logo_2:
            if os.path.exists("Logo_guindo.png"): st.image("Logo_guindo.png", use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("### 🛠️ MENÚ PRINCIPAL")
        m = st.radio("", ["🔍 Consulta", "➕ Registro", "📊 Nómina General"], key="menu_p_unico")
        st.markdown("### 📈 REPORTES")
        r = st.radio("", ["Vencimientos", "Vacaciones", "Estadísticas"], key="menu_r_unico")
        st.markdown("---")
        if st.button("🚪 Cerrar Sesión", key="btn_logout"):
            st.session_state.rol = None
            st.rerun()

    # --- SECCIÓN CONSULTA ---
    if m == "🔍 Consulta":
        st.markdown("<h2 style='color: #FFD700;'>Búsqueda de Colaborador</h2>", unsafe_allow_html=True)
        dni_b = st.text_input("Ingrese DNI para consultar:").strip()

        if dni_b:
            pers = dfs["PERSONAL"][dfs["PERSONAL"]["dni"] == dni_b]
            if not pers.empty:
                nom_c = pers.iloc[0]["apellidos y nombres"]
                
                # --- CABECERA Y BOTÓN DE CERTIFICADO ---
                col_n1, col_n2 = st.columns([2, 1])
                with col_n1:
                    st.markdown(f"""
                        <div style='border-bottom: 2px solid #FFD700; padding-bottom: 10px; margin-bottom: 20px;'>
                            <h1 style='color: white; margin: 0;'>👤 {nom_c}</h1>
                        </div>
                    """, unsafe_allow_html=True)
                with col_n2:
                    df_contratos = dfs["CONTRATOS"][dfs["CONTRATOS"]["dni"] == dni_b]
                    if not df_contratos.empty:
                        word_file = gen_word(nom_c, dni_b, df_contratos)
                        st.download_button("📄 Generar Certificado de Trabajo", data=word_file, file_name=f"Certificado_{dni_b}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

                t_noms = ["Datos Generales", "Exp. Laboral", "Form. Académica", "Investigación", "Datos Familiares", "Contratos", "Vacaciones", "Otros Beneficios", "Méritos/Demer.", "Evaluación", "Liquidaciones"]
                h_keys = ["DATOS GENERALES", "EXP. LABORAL", "FORM. ACADEMICA", "INVESTIGACION", "DATOS FAMILIARES", "CONTRATOS", "VACACIONES", "OTROS BENEFICIOS", "MERITOS Y DEMERITOS", "EVALUACION DEL DESEMPEÑO", "LIQUIDACIONES"]

                tabs = st.tabs(t_noms)

                for i, tab in enumerate(tabs):
                    h_name = h_keys[i]
                    with tab:
                        if "dni" in dfs[h_name].columns:
                            c_df = dfs[h_name][dfs[h_name]["dni"] == dni_b]
                        else:
                            c_df = pd.DataFrame(columns=COLUMNAS.get(h_name, []))

                        # ==========================================
                        # PANEL DE RESUMEN AUTOMÁTICO PARA VACACIONES
                        # ==========================================
                        if h_name == "VACACIONES":
                            df_tc = df_contratos[df_contratos["tipo contrato"].astype(str).str.strip().str.lower() == "planilla completo"]
                            
                            detalles = []
                            dias_generados_totales = 0
                            dias_gozados_totales = pd.to_numeric(c_df["días gozados"], errors='coerce').sum()

                            if not df_tc.empty:
                                df_tc_calc = df_tc.copy()
                                
                                start_global = pd.to_datetime(df_tc_calc['f_inicio'].min()).date()
                                
                                if pd.notnull(start_global):
                                    curr_start = start_global
                                    
                                    while curr_start <= date.today():
                                        # Calcular fin del periodo (1 año exacto menos 1 día) de forma segura
                                        curr_end = (pd.to_datetime(curr_start) + pd.DateOffset(years=1) - pd.Timedelta(days=1)).date()
                                        days_in_p = 0
                                        
                                        for _, r in df_tc_calc.iterrows():
                                            c_start = pd.to_datetime(r['f_inicio']).date() if pd.notnull(r['f_inicio']) else None
                                            c_end = pd.to_datetime(r['f_fin']).date() if pd.notnull(r['f_fin']) else None
                                            if c_start and c_end:
                                                o_start = max(curr_start, c_start)
                                                o_end = min(curr_end, c_end, date.today())
                                                if o_start <= o_end: 
                                                    days_in_p += (o_end - o_start).days + 1
                                                
                                        gen_p = round((days_in_p / 30) * 2.5, 2)
                                        p_name = f"{curr_start.year}-{curr_start.year+1}"
                                        
                                        # Días gozados en este periodo
                                        goz_df = c_df[c_df["periodo"].astype(str).str.strip() == p_name]
                                        goz_p = pd.to_numeric(goz_df["días gozados"], errors='coerce').sum()
                                        
                                        # Agregamos a la tabla si hay días generados o gozados en este año
                                        if gen_p > 0 or goz_p > 0:
                                            detalles.append({
                                                "Periodo": p_name, 
                                                "Del": curr_start.strftime("%d/%m/%Y"), 
                                                "Al": curr_end.strftime("%d/%m/%Y"), 
                                                "Días Generados": gen_p, 
                                                "Días Gozados": goz_p, 
                                                "Saldo": round(gen_p - goz_p, 2)
                                            })
                                        
                                        dias_generados_totales += gen_p
                                        # Avanzar al siguiente año
                                        curr_start = (pd.to_datetime(curr_start) + pd.DateOffset(years=1)).date()

                            saldo_v = round(dias_generados_totales - dias_gozados_totales, 2)

                            # PANEL SUPERIOR
                            st.markdown(f"""
                            <div style='display: flex; justify-content: space-between; background-color: #FFF9C4; padding: 15px; border-radius: 10px; border: 2px solid #FFD700; margin-bottom: 15px;'>
                                <div style='text-align: center; width: 33%;'><h2 style='color: #4a0000; margin:0;'>{round(dias_generados_totales,2)}</h2><p style='color: #4a0000; margin:0; font-weight: bold;'>Días Generados Totales</p></div>
                                <div style='text-align: center; width: 33%; border-left: 2px solid #FFD700; border-right: 2px solid #FFD700;'><h2 style='color: #4a0000; margin:0;'>{round(dias_gozados_totales,2)}</h2><p style='color: #4a0000; margin:0; font-weight: bold;'>Días Gozados</p></div>
                                <div style='text-align: center; width: 33%;'><h2 style='color: #4a0000; margin:0;'>{saldo_v}</h2><p style='color: #4a0000; margin:0; font-weight: bold;'>Saldo Disponible</p></div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # TABLA DETALLADA
                            if detalles:
                                st.markdown("<h4 style='color: #FFD700;'>Desglose por Periodos</h4>", unsafe_allow_html=True)
                                # Aplicamos formato visual a la tabla
                                st.table(pd.DataFrame(detalles).style.format({"Días Generados": "{:.2f}", "Días Gozados": "{:.2f}", "Saldo": "{:.2f}"}))
                                st.markdown("<br>", unsafe_allow_html=True)

                        # ==========================================
                        # VISTA DE TABLA EDITABLE (Formato Fecha sin Horas)
                        # ==========================================
                        vst = c_df.copy()
                        col_conf = {}
                        
                        for col in vst.columns:
                            if "fecha" in col.lower() or "f_" in col.lower():
                                vst[col] = pd.to_datetime(vst[col], errors='coerce').dt.date
                                col_conf[str(col).upper()] = st.column_config.DateColumn(format="DD/MM/YYYY")

                        vst.columns = [str(col).upper() for col in vst.columns] 
                        vst.insert(0, "SEL", False)

                        st.markdown("""<style>[data-testid="stDataEditor"] { border: 2px solid #FFD700 !important; border-radius: 10px !important; }</style>""", unsafe_allow_html=True)
                        
                        ed = st.data_editor(vst, hide_index=True, use_container_width=True, column_config=col_conf, key=f"ed_{h_name}")
                        sel = ed[ed["SEL"] == True]

                        if not es_lector:
                            col_a, col_b = st.columns(2)
                            cols_reales = [c for c in dfs[h_name].columns if c.lower() not in ["id", "dni", "apellidos y nombres"]]

                            with col_a:
                                with st.expander("➕ Nuevo Registro"):
                                    with st.form(f"f_add_{h_name}", clear_on_submit=True):
                                        if h_name == "CONTRATOS":
                                            car = st.text_input("Cargo")
                                            rem_b = st.number_input("Remuneración básica", 0.0)
                                            bono = st.text_input("Bonificación")
                                            cond = st.text_input("Condición de trabajo")
                                            ini = st.date_input("Inicio")
                                            fin = st.date_input("Fin")
                                            
                                            # COMBOS ACTUALIZADOS
                                            t_trab = st.selectbox("Tipo de trabajador", ["Administrativo", "Docente", "Externo"])
                                            mod = st.selectbox("Modalidad", ["Presencial", "Semipresencial", "Virtual"])
                                            temp = st.selectbox("Temporalidad", ["Plazo fijo", "Plazo indeterminado", "Ordinarizado"])
                                            lnk = st.text_input("Link")
                                            tcont = st.selectbox("Tipo Contrato", ["Planilla completo", "Tiempo Parcial", "Recibo por Honorarios", "Otro"])
                                            
                                            est_a = "ACTIVO" if fin >= date.today() else "CESADO"
                                            mot_a = st.selectbox("Motivo Cese", ["Vigente"] + MOTIVOS_CESE) if est_a == "CESADO" else "Vigente"

                                            if st.form_submit_button("Guardar Contrato"):
                                                nid = dfs[h_name]["id"].max() + 1 if not dfs[h_name].empty else 1
                                                new = {"id": nid, "dni": dni_b, "cargo": car, "remuneración básica": rem_b, "bonificación": bono, "condición de trabajo": cond,
                                                       "f_inicio": ini, "f_fin": fin, "tipo de trabajador": t_trab, "modalidad": mod, "temporalidad": temp, "link": lnk, 
                                                       "tipo contrato": tcont, "estado": est_a, "motivo cese": mot_a}
                                                dfs[h_name] = pd.concat([dfs[h_name], pd.DataFrame([new])], ignore_index=True)
                                                save_data(dfs)
                                                st.rerun()
                                        else:
                                            new_row = {"dni": dni_b}
                                            for col in cols_reales:
                                                if "fecha" in col.lower() or "f_" in col.lower():
                                                    new_row[col] = st.date_input(col.title())
                                                elif col.lower() in ["remuneración", "bonificación", "sueldo", "días generados", "días gozados", "saldo", "edad", "monto"]:
                                                    new_row[col] = st.number_input(col.title(), 0.0)
                                                else:
                                                    new_row[col] = st.text_input(col.title())

                                            if st.form_submit_button("Guardar Registro"):
                                                if not dfs[h_name].empty and "id" in dfs[h_name].columns: new_row["id"] = dfs[h_name]["id"].max() + 1
                                                elif "id" in dfs[h_name].columns: new_row["id"] = 1
                                                dfs[h_name] = pd.concat([dfs[h_name], pd.DataFrame([new_row])], ignore_index=True)
                                                save_data(dfs)
                                                st.rerun()

                            with col_b:
                                with st.expander("📝 Editar / Eliminar"):
                                    if not sel.empty:
                                        idx = sel.index[0]
                                        with st.form(f"f_edit_{h_name}"):
                                            if h_name == "CONTRATOS":
                                                n_car = st.text_input("Cargo", value=str(sel.iloc[0].get("CARGO", "")))
                                                
                                                try: val_rem = float(sel.iloc[0].get("REMUNERACIÓN BÁSICA", 0.0))
                                                except: val_rem = 0.0
                                                n_rem = st.number_input("Remuneración básica", value=val_rem)
                                                
                                                n_bon = st.text_input("Bonificación", value=str(sel.iloc[0].get("BONIFICACIÓN", "")))
                                                n_cond = st.text_input("Condición de trabajo", value=str(sel.iloc[0].get("CONDICIÓN DE TRABAJO", "")))
                                                
                                                try: ini_val = pd.to_datetime(sel.iloc[0].get("F_INICIO")).date()
                                                except: ini_val = date.today()
                                                n_ini = st.date_input("Inicio", value=ini_val)
                                                
                                                try: fin_val = pd.to_datetime(sel.iloc[0].get("F_FIN")).date()
                                                except: fin_val = date.today()
                                                n_fin = st.date_input("Fin", value=fin_val)
                                                
                                                # Combos Seguros para Edición
                                                v_ttrab = str(sel.iloc[0].get("TIPO DE TRABAJADOR", "Administrativo"))
                                                opts_tt = ["Administrativo", "Docente", "Externo"]
                                                if v_ttrab not in opts_tt: opts_tt.append(v_ttrab)
                                                n_ttrab = st.selectbox("Tipo de trabajador", opts_tt, index=opts_tt.index(v_ttrab))
                                                
                                                v_mod = str(sel.iloc[0].get("MODALIDAD", "Presencial"))
                                                opts_mod = ["Presencial", "Semipresencial", "Virtual"]
                                                if v_mod not in opts_mod: opts_mod.append(v_mod)
                                                n_mod = st.selectbox("Modalidad", opts_mod, index=opts_mod.index(v_mod))
                                                
                                                v_tem = str(sel.iloc[0].get("TEMPORALIDAD", "Plazo fijo"))
                                                opts_tem = ["Plazo fijo", "Plazo indeterminado", "Ordinarizado"]
                                                if v_tem not in opts_tem: opts_tem.append(v_tem)
                                                n_tem = st.selectbox("Temporalidad", opts_tem, index=opts_tem.index(v_tem))
                                                
                                                n_lnk = st.text_input("Link", value=str(sel.iloc[0].get("LINK", "")))
                                                
                                                v_tcont = str(sel.iloc[0].get("TIPO CONTRATO", "Planilla completo"))
                                                opts_tcon = ["Planilla completo", "Tiempo Parcial", "Recibo por Honorarios", "Otro"]
                                                if v_tcont not in opts_tcon: opts_tcon.append(v_tcont)
                                                n_tcont = st.selectbox("Tipo Contrato", opts_tcon, index=opts_tcon.index(v_tcont))

                                                est_e = "ACTIVO" if n_fin >= date.today() else "CESADO"
                                                
                                                v_mot = str(sel.iloc[0].get("MOTIVO CESE", "Vigente"))
                                                opts_mot = ["Vigente"] + MOTIVOS_CESE
                                                if v_mot not in opts_mot: opts_mot.append(v_mot)
                                                mot_e = st.selectbox("Motivo Cese", opts_mot, index=opts_mot.index(v_mot)) if est_e == "CESADO" else "Vigente"

                                                if st.form_submit_button("Actualizar"):
                                                    dfs[h_name].at[idx, "cargo"] = n_car
                                                    dfs[h_name].at[idx, "remuneración básica"] = n_rem
                                                    dfs[h_name].at[idx, "bonificación"] = n_bon
                                                    dfs[h_name].at[idx, "condición de trabajo"] = n_cond
                                                    dfs[h_name].at[idx, "f_inicio"] = n_ini
                                                    dfs[h_name].at[idx, "f_fin"] = n_fin
                                                    dfs[h_name].at[idx, "tipo de trabajador"] = n_ttrab
                                                    dfs[h_name].at[idx, "modalidad"] = n_mod
                                                    dfs[h_name].at[idx, "temporalidad"] = n_tem
                                                    dfs[h_name].at[idx, "link"] = n_lnk
                                                    dfs[h_name].at[idx, "tipo contrato"] = n_tcont
                                                    dfs[h_name].at[idx, "estado"] = est_e
                                                    dfs[h_name].at[idx, "motivo cese"] = mot_e
                                                    save_data(dfs)
                                                    st.rerun()
                                            else:
                                                edit_row = {}
                                                for col in cols_reales:
                                                    val = sel.iloc[0][col.upper()]
                                                    if "fecha" in col.lower() or "f_" in col.lower():
                                                        try: parsed_date = pd.to_datetime(val).date()
                                                        except: parsed_date = date.today()
                                                        edit_row[col] = st.date_input(col.title(), value=parsed_date)
                                                    elif col.lower() in ["remuneración", "bonificación", "sueldo", "días generados", "días gozados", "saldo", "edad", "monto"]:
                                                        try: num_val = float(val) if pd.notnull(val) else 0.0
                                                        except: num_val = 0.0
                                                        edit_row[col] = st.number_input(col.title(), value=num_val)
                                                    else:
                                                        edit_row[col] = st.text_input(col.title(), value=str(val) if pd.notnull(val) else "")
                                                        
                                                if st.form_submit_button("Actualizar Registro"):
                                                    for col in cols_reales:
                                                        dfs[h_name].at[idx, col] = edit_row[col]
                                                    save_data(dfs)
                                                    st.rerun()
                                        
                                        if st.button("🚨 Eliminar Fila Seleccionada", key=f"del_{h_name}"):
                                            dfs[h_name] = dfs[h_name].drop(sel.index)
                                            save_data(dfs)
                                            st.rerun()
                                    else:
                                        st.info("Activa la casilla (SEL) en la tabla superior para editar o eliminar el registro.")
            else:
                st.error("DNI no encontrado en la base de datos.")

    # --- SECCIÓN REGISTRO Y NÓMINA (Sin cambios) ---
    elif m == "➕ Registro" and not es_lector:
        with st.form("reg_p"):
            st.write("### Alta de Nuevo Trabajador")
            d = st.text_input("DNI")
            n = st.text_input("Nombres").upper()
            l = st.text_input("Link File")

            if st.form_submit_button("Registrar"):
                if d and n:
                    dfs["PERSONAL"] = pd.concat([dfs["PERSONAL"], pd.DataFrame([{"dni": d, "apellidos y nombres": n, "link": l}])], ignore_index=True)
                    save_data(dfs)
                    st.success("Registrado correctamente")

    elif m == "📊 Nómina General":
        st.markdown("<h2 style='color: #FFD700;'>👥 Trabajadores registrados en el sistema</h2>", unsafe_allow_html=True)
        busqueda = st.text_input("🔍 Buscar por nombre o DNI:").strip().lower()
        df_nom = dfs["PERSONAL"].copy()
        
        if busqueda: df_nom = df_nom[df_nom['apellidos y nombres'].str.lower().str.contains(busqueda, na=False) | df_nom['dni'].astype(str).str.contains(busqueda, na=False)]

        df_ver = df_nom.copy()
        df_ver.columns = [col.upper() for col in df_ver.columns]
        df_ver.insert(0, "SEL", False)
        
        ed_nom = st.data_editor(df_ver, hide_index=True, use_container_width=True, key="nomina_v3_blanco")
        filas_sel = ed_nom[ed_nom["SEL"] == True]
        
        if not filas_sel.empty:
            st.markdown("---")
            if st.button(f"🚨 ELIMINAR {len(filas_sel)} REGISTRO(S)", type="secondary", use_container_width=True):
                dnis = filas_sel["DNI"].astype(str).tolist()
                for h in dfs:
                    if 'dni' in dfs[h].columns: dfs[h] = dfs[h][~dfs[h]['dni'].astype(str).isin(dnis)]
                save_data(dfs)
                st.success("Registros eliminados correctamente.")
                st.rerun()








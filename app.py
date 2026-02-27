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
TEXTO_CERT = "LA OFICINA DE GESTIÓN DE TALENTO HUMANO DE LA UNIVERSIDAD PRIVADA DE HUANCAYO “FRANKLIN ROOSEVELT”, CERTIFICA QUE:"

MOTIVOS_CESE = ["Término de contrato", "Renuncia", "Despido", "Mutuo acuerdo", "Fallecimiento", "Otros"]

COLUMNAS = {
    "PERSONAL": ["dni", "apellidos y nombres", "link"],
    "DATOS GENERALES": ["apellidos y nombres", "dni", "dirección", "link de dirección", "estado civil", "fecha de nacimiento", "edad"],
    "DATOS FAMILIARES": ["parentesco", "apellidos y nombres", "dni", "fecha de nacimiento", "edad", "estudios", "telefono"],
    "EXP. LABORAL": ["tipo de experiencia", "lugar", "puesto", "fecha inicio", "fecha de fin", "motivo cese"],
    "FORM. ACADEMICA": ["grado, titulo o especialización", "descripcion", "universidad", "año"],
    "INVESTIGACION": ["año publicación", "autor, coautor o asesor", "tipo de investigación publicada", "nivel de publicación", "lugar de publicación"],
    "CONTRATOS": ["id", "dni", "cargo", "sueldo", "f_inicio", "f_fin", "tipo", "estado", "motivo cese"],
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
            if "dni" in df.columns:
                df["dni"] = df["dni"].astype(str).str.strip().replace(r'\.0$', '', regex=True)
            dfs[h] = df
    return dfs

def save_data(dfs):
    with pd.ExcelWriter(DB) as w:
        for h, df in dfs.items():
            df_s = df.copy()
            df_s.columns = [c.upper() for c in df_s.columns]
            df_s.to_excel(w, sheet_name=h, index=False)

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
    r_tit.bold, r_tit.font.name, r_tit.font.size = True, 'Arial', Pt(24)

    doc.add_paragraph("\n" + TEXTO_CERT).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    p_inf = doc.add_paragraph()
    p_inf.add_run("El TRABAJADOR ").bold = False
    p_inf.add_run(nom).bold = True
    p_inf.add_run(f", identificado con DNI N° {dni}, laboró bajo el siguiente detalle:")

    t = doc.add_table(rows=1, cols=3)
    t.style = 'Table Grid'
    for i, h in enumerate(["CARGO", "FECHA INICIO", "FECHA FIN"]):
        t.rows[0].cells[i].text = h

    for _, fila in df_c.iterrows():
        celdas = t.add_row().cells
        celdas[0].text = str(fila.get('cargo', ''))
        celdas[1].text = pd.to_datetime(fila.get('f_inicio')).strftime('%d/%m/%Y') if pd.notnull(fila.get('f_inicio')) else ""
        celdas[2].text = pd.to_datetime(fila.get('f_fin')).strftime('%d/%m/%Y') if pd.notnull(fila.get('f_fin')) else ""

    doc.add_paragraph("\n\nHuancayo, " + date.today().strftime("%d/%m/%Y")).alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f = doc.add_paragraph()
    f.alignment = WD_ALIGN_PARAGRAPH.CENTER
    f.add_run("\n\n__________________________\n" + F_N + "\n" + F_C).bold = True

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# ==========================================
# 3. ESTILOS CSS CORREGIDOS
# ==========================================
st.markdown("""
<style>
    /* 1. Fondo general y ocultar la franja blanca superior de Streamlit */
    .stApp { background-color: #4a0000 !important; }
    [data-testid="stHeader"] { display: none !important; }
    
    /* 2. Recuperar textos (Tu talento, Bienvenido, etc.) */
    /* Lo dejamos sin !important para que respete tus colores originales (amarillo/blanco) */
    .stApp p, .stMarkdown p { color: #FFFFFF; } 
    .stApp h1, .stApp h2, .stApp h3 { color: #FFD700 !important; }
    
    /* 3. SIDEBAR (Menú lateral y opciones) */
    [data-testid="stSidebar"] { background-color: #4a0000 !important; }
    [data-testid="stSidebar"] h3 { color: #FFD700 !important; font-weight: bold !important; }
    
    /* Logo con recuadro amarillo */
    [data-testid="stSidebar"] [data-testid="stImage"] {
        background-color: #FFF9C4 !important;
        border: 4px solid #FFD700 !important;
        border-radius: 15px !important;
        padding: 10px !important;
    }
    
    /* Solución a las letras invisibles del menú lateral (Radio Buttons) */
    div[role="radiogroup"] label { background-color: transparent !important; }
    div[role="radiogroup"] label p { color: #FFFFFF !important; font-weight: bold !important; font-size: 16px !important; }
    
    /* 4. BOTONES (Soluciona el problema de letras invisibles) */
    div.stButton > button, [data-testid="stFormSubmitButton"] > button {
        background-color: #FFD700 !important;
        border: 2px solid #FFFFFF !important;
        border-radius: 10px !important;
    }
    /* Letra guinda dentro de todos los botones */
    div.stButton > button p, [data-testid="stFormSubmitButton"] > button p {
        color: #4a0000 !important; 
        font-weight: bold !important;
        font-size: 16px !important;
    }
    div.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
        background-color: #ffffff !important;
        border-color: #FFD700 !important;
    }

    /* 5. Pestañas (Tabs) */
    [data-testid="stTabs"] button p { color: #FFFFFF !important; font-weight: bold !important; font-size: 16px !important; }
    [data-testid="stTabs"] button[aria-selected="true"] p { color: #FFD700 !important; }
    [data-testid="stTabs"] button[aria-selected="true"] { border-bottom-color: #FFD700 !important; }

    /* 6. Expanders (Cajas de Agregar / Editar) */
    [data-testid="stExpander"] details { background-color: #FFF9C4 !important; border: 2px solid #FFD700 !important; border-radius: 10px !important; overflow: hidden !important; }
    [data-testid="stExpander"] summary { background-color: #FFD700 !important; padding: 10px !important; }
    [data-testid="stExpander"] summary p { color: #4a0000 !important; font-weight: bold !important; }

    /* 7. TABLAS (Solución definitiva para encabezado amarillo) */
    [data-testid="stDataEditor"], [data-testid="stTable"], .stTable { 
        background-color: white !important; 
        border-radius: 10px !important; 
        overflow: hidden !important; 
    }
    /* Selector agresivo para pintar la cabecera interactiva */
    div[role="columnheader"], .react-grid-HeaderCell, [data-testid="stDataEditorColumnHeader"] { 
        background-color: #FFF9C4 !important; 
    }
    div[role="columnheader"] *, .react-grid-HeaderCell *, /* Cabecera interactiva en SÚPER NEGRITA */
    [data-testid="stDataEditor"] .react-grid-HeaderCell span { 
        color: #4a0000 !important; 
        font-weight: 900 !important; /* Extra negrita */
        font-size: 15px !important; /* Letra más grande */
        text-transform: uppercase !important; 
    }
    }
    /* Tablas estáticas (st.table) */
    thead tr th { background-color: #FFF9C4 !important; color: #4a0000 !important; font-weight: bold !important; text-transform: uppercase !important; border: 1px solid #f0f0f0 !important; }
    
    /* 8. Formularios e Inputs */
    /* Textos amarillos para el fondo guindo general */
    .stApp label p { color: #FFD700 !important; font-weight: bold !important; } 
    
    /* 🔥 NUEVO: Textos guindos EXCLUSIVOS para dentro de las cajas cremas (Agregar/Editar) */
    [data-testid="stExpander"] label p { color: #4a0000 !important; font-weight: bold !important; }
    [data-testid="stExpander"] div[data-baseweb="input"] { background-color: #ffffff !important; border: 2px solid #4a0000 !important; }
    
    /* Inputs generales */
    .stApp div[data-baseweb="input"] { background-color: #ffffff !important; border: 2px solid #FFD700 !important; }
    .stApp input { color: #4a0000 !important; font-weight: bold !important; }
</style>
""", unsafe_allow_html=True)
# ==========================================
# 4. LÓGICA DE DATOS Y SESIÓN
# ==========================================
if "rol" not in st.session_state:
    st.session_state.rol = None

# --- LOGIN ---
if st.session_state.rol is None:
    st.markdown("<h4 style='text-align: center; color: #FFD700;'>¡Tu talento es importante! :)</h4>", unsafe_allow_html=True)

    col_logo1, col_logo2, col_logo3 = st.columns([1, 1.2, 1])
    with col_logo2:
        if os.path.exists("Logo_amarillo.png"):
            st.image("Logo_amarillo.png", use_container_width=True)
        else:
            st.warning("No se encontró el archivo Logo_amarillo.png")

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        u = st.text_input("USUARIO")
        p = st.text_input("CONTRASEÑA", type="password")

        st.markdown('<p class="login-welcome">Bienvenido (a) al sistema de gestión de datos de los colaboradores</p>', unsafe_allow_html=True)

        if st.button("INGRESAR"):
            u_low = u.lower().strip()
            if u_low == "admin":
                st.session_state.rol = "Admin"
            elif u_low == "supervisor" and p == "123":
                st.session_state.rol = "Supervisor"
            elif u_low == "lector" and p == "123":
                st.session_state.rol = "Lector"
            else:
                st.error("Credenciales incorrectas")

            if st.session_state.rol:
                st.rerun()

# --- SISTEMA PRINCIPAL ---
else:
    dfs = load_data()
    es_lector = st.session_state.rol == "Lector"

    with st.sidebar:
        # 1. Logo superior con st.image nativo (más seguro) y tamaño reducido
        st.markdown("<br>", unsafe_allow_html=True)
        col_logo_1, col_logo_2, col_logo_3 = st.columns([1, 2, 1]) # Columnas ajustadas para hacerlo más pequeño
        with col_logo_2:
            if os.path.exists("Logo_guindo.png"):
                st.image("Logo_guindo.png", use_container_width=True)
            else:
                st.warning("Sin Logo")
        st.markdown("<br>", unsafe_allow_html=True)

        # 2. Opciones de menú
        st.markdown("### 🛠️ MENÚ PRINCIPAL")
        m = st.radio("", ["🔍 Consulta", "➕ Registro", "📊 Nómina General"], key="menu_p_unico")

        st.markdown("### 📈 REPORTES")
        r = st.radio("", ["Vencimientos", "Vacaciones", "Estadísticas"], key="menu_r_unico")
        
        st.markdown("---")

        # 3. Botón inferior
        if st.button("🚪 Cerrar Sesión", key="btn_logout"):
            st.session_state.rol = None
            st.rerun()

    col_m1, col_m2, col_m3 = st.columns([1.5, 1, 1.5])
    with col_m2:
        if os.path.exists("Logo_amarillo.png"):
            st.image("Logo_amarillo.png", use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- SECCIÓN CONSULTA ---
    if m == "🔍 Consulta":
        st.markdown("<h2 style='color: #FFD700;'>Búsqueda de Colaborador</h2>", unsafe_allow_html=True)
        dni_b = st.text_input("Ingrese DNI para consultar:").strip()

        if dni_b:
            pers = dfs["PERSONAL"][dfs["PERSONAL"]["dni"] == dni_b]
            if not pers.empty:
                nom_c = pers.iloc[0]["apellidos y nombres"]
                
                st.markdown(f"""
                    <div style='border-bottom: 2px solid #FFD700; padding-bottom: 10px; margin-bottom: 20px;'>
                        <h1 style='color: white; margin: 0;'>👤 {nom_c}</h1>
                    </div>
                """, unsafe_allow_html=True)

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
                            df_contratos = dfs["CONTRATOS"][dfs["CONTRATOS"]["dni"] == dni_b]
                            
                            # CORRECCIÓN: Filtramos por 'tipo contrato' == 'planilla completo'
                            if "tipo contrato" in df_contratos.columns:
                                df_tc = df_contratos[df_contratos["tipo contrato"].astype(str).str.strip().str.lower() == "planilla completo"]
                            else:
                                df_tc = pd.DataFrame()

                            dias_trabajados = 0
                            for _, row in df_tc.iterrows():
                                try:
                                    f_i = pd.to_datetime(row["f_inicio"]).date()
                                    f_f = pd.to_datetime(row["f_fin"]).date()
                                    if pd.notnull(f_i) and pd.notnull(f_f):
                                        f_f_calc = min(f_f, date.today())
                                        if f_f_calc >= f_i:
                                            dias_trabajados += (f_f_calc - f_i).days + 1
                                except: pass

                            dias_generados = round((dias_trabajados / 30) * 2.5, 2)
                            dias_gozados = pd.to_numeric(c_df["días gozados"], errors='coerce').sum()
                            saldo_v = round(dias_generados - dias_gozados, 2)

                            st.markdown(f"""
                            <div style='display: flex; justify-content: space-between; background-color: #FFF9C4; padding: 15px; border-radius: 10px; border: 2px solid #FFD700; margin-bottom: 15px;'>
                                <div style='text-align: center; width: 33%;'><h2 style='color: #4a0000; margin:0;'>{dias_generados}</h2><p style='color: #4a0000; margin:0; font-weight: bold;'>Días Generados Totales</p></div>
                                <div style='text-align: center; width: 33%; border-left: 2px solid #FFD700; border-right: 2px solid #FFD700;'><h2 style='color: #4a0000; margin:0;'>{dias_gozados}</h2><p style='color: #4a0000; margin:0; font-weight: bold;'>Días Gozados</p></div>
                                <div style='text-align: center; width: 33%;'><h2 style='color: #4a0000; margin:0;'>{saldo_v}</h2><p style='color: #4a0000; margin:0; font-weight: bold;'>Saldo Disponible</p></div>
                            </div>
                            """, unsafe_allow_html=True)

                        # VISTA DE TABLA EDITABLE
                        vst = c_df.copy()
                        vst.columns = [str(col).upper() for col in vst.columns] 
                        vst.insert(0, "SEL", False)

                        st.markdown("""<style>[data-testid="stDataEditor"] { border: 2px solid #FFD700 !important; border-radius: 10px !important; }</style>""", unsafe_allow_html=True)
                        
                        ed = st.data_editor(vst, hide_index=True, use_container_width=True, key=f"ed_{h_name}")
                        sel = ed[ed["SEL"] == True]

                        if not es_lector:
                            col_a, col_b = st.columns(2)
                            cols_reales = [c for c in dfs[h_name].columns if c.lower() not in ["id", "dni", "apellidos y nombres"]]

                            # ==========================================
                            # 1. AGREGAR NUEVO DATO
                            # ==========================================
                            with col_a:
                                with st.expander("➕ Nuevo Registro"):
                                    with st.form(f"f_add_{h_name}", clear_on_submit=True):
                                        
                                        if h_name == "CONTRATOS":
                                            # CORRECCIÓN: Agregados TODOS los campos para un nuevo contrato
                                            car = st.text_input("Cargo")
                                            sue = st.number_input("Sueldo", 0.0)
                                            ini = st.date_input("Inicio")
                                            fin = st.date_input("Fin")
                                            tip = st.text_input("Tipo")
                                            mod = st.text_input("Modalidad")
                                            tem = st.text_input("Temporalidad")
                                            lnk = st.text_input("Link")
                                            tcolab = st.text_input("Tipo Colaborador")
                                            tcont = st.selectbox("Tipo Contrato", ["Planilla completo", "Tiempo Parcial", "Recibo por Honorarios", "Otro"])
                                            
                                            est_a = "ACTIVO" if fin >= date.today() else "CESADO"
                                            mot_a = st.selectbox("Motivo Cese", ["Vigente"] + MOTIVOS_CESE) if est_a == "CESADO" else "Vigente"

                                            if st.form_submit_button("Guardar Contrato"):
                                                nid = dfs[h_name]["id"].max() + 1 if not dfs[h_name].empty else 1
                                                new = {"id": nid, "dni": dni_b, "cargo": car, "sueldo": sue, "f_inicio": ini, "f_fin": fin, 
                                                       "tipo": tip, "modalidad": mod, "temporalidad": tem, "link": lnk, 
                                                       "tipo colaborador": tcolab, "tipo contrato": tcont, "estado": est_a, "motivo cese": mot_a}
                                                dfs[h_name] = pd.concat([dfs[h_name], pd.DataFrame([new])], ignore_index=True)
                                                save_data(dfs)
                                                st.rerun()
                                                
                                        elif h_name == "VACACIONES":
                                            per = st.text_input("Periodo (Ej. 2024-2025)")
                                            ini_v = st.date_input("Fecha de Inicio")
                                            fin_v = st.date_input("Fecha de Fin")
                                            lnk = st.text_input("Link de sustento")
                                            
                                            if st.form_submit_button("Registrar Vacaciones"):
                                                d_goz = (fin_v - ini_v).days + 1
                                                if d_goz < 0: d_goz = 0
                                                new_v = {"dni": dni_b, "periodo": per, "fecha de inicio": ini_v, "fecha de fin": fin_v, 
                                                         "días generados": 0, "días gozados": d_goz, "saldo": saldo_v - d_goz, "link": lnk}
                                                dfs[h_name] = pd.concat([dfs[h_name], pd.DataFrame([new_v])], ignore_index=True)
                                                save_data(dfs)
                                                st.rerun()
                                                
                                        else:
                                            new_row = {"dni": dni_b}
                                            for col in cols_reales:
                                                if "fecha" in col.lower() or "f_" in col.lower():
                                                    new_row[col] = st.date_input(col.title())
                                                elif col.lower() in ["sueldo", "días generados", "días gozados", "saldo", "edad", "monto"]:
                                                    new_row[col] = st.number_input(col.title(), 0.0)
                                                else:
                                                    new_row[col] = st.text_input(col.title())

                                            if st.form_submit_button("Guardar Registro"):
                                                if not dfs[h_name].empty and "id" in dfs[h_name].columns:
                                                    new_row["id"] = dfs[h_name]["id"].max() + 1
                                                elif "id" in dfs[h_name].columns:
                                                    new_row["id"] = 1
                                                    
                                                dfs[h_name] = pd.concat([dfs[h_name], pd.DataFrame([new_row])], ignore_index=True)
                                                save_data(dfs)
                                                st.rerun()

                            # ==========================================
                            # 2. EDITAR / ELIMINAR DATO SELECCIONADO
                            # ==========================================
                            with col_b:
                                with st.expander("📝 Editar / Eliminar"):
                                    if not sel.empty:
                                        idx = sel.index[0]
                                        with st.form(f"f_edit_{h_name}"):
                                            if h_name == "CONTRATOS":
                                                # CORRECCIÓN: Ahora jalamos TODOS los datos de la tabla para editarlos
                                                n_car = st.text_input("Cargo", value=str(sel.iloc[0].get("CARGO", "")))
                                                
                                                try: val_sue = float(sel.iloc[0].get("SUELDO", 0.0))
                                                except: val_sue = 0.0
                                                n_sue = st.number_input("Sueldo", value=val_sue)
                                                
                                                try: ini_val = pd.to_datetime(sel.iloc[0].get("F_INICIO")).date()
                                                except: ini_val = date.today()
                                                n_ini = st.date_input("Inicio", value=ini_val)
                                                
                                                try: fin_val = pd.to_datetime(sel.iloc[0].get("F_FIN")).date()
                                                except: fin_val = date.today()
                                                n_fin = st.date_input("Fin", value=fin_val)
                                                
                                                n_tip = st.text_input("Tipo", value=str(sel.iloc[0].get("TIPO", "")))
                                                n_mod = st.text_input("Modalidad", value=str(sel.iloc[0].get("MODALIDAD", "")))
                                                n_tem = st.text_input("Temporalidad", value=str(sel.iloc[0].get("TEMPORALIDAD", "")))
                                                n_lnk = st.text_input("Link", value=str(sel.iloc[0].get("LINK", "")))
                                                n_tcolab = st.text_input("Tipo Colaborador", value=str(sel.iloc[0].get("TIPO COLABORADOR", "")))
                                                
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
                                                    dfs[h_name].at[idx, "sueldo"] = n_sue
                                                    dfs[h_name].at[idx, "f_inicio"] = n_ini
                                                    dfs[h_name].at[idx, "f_fin"] = n_fin
                                                    dfs[h_name].at[idx, "tipo"] = n_tip
                                                    dfs[h_name].at[idx, "modalidad"] = n_mod
                                                    dfs[h_name].at[idx, "temporalidad"] = n_tem
                                                    dfs[h_name].at[idx, "link"] = n_lnk
                                                    dfs[h_name].at[idx, "tipo colaborador"] = n_tcolab
                                                    dfs[h_name].at[idx, "tipo contrato"] = n_tcont
                                                    dfs[h_name].at[idx, "estado"] = est_e
                                                    dfs[h_name].at[idx, "motivo cese"] = mot_e
                                                    save_data(dfs)
                                                    st.rerun()
                                                    
                                            elif h_name == "VACACIONES":
                                                per_e = st.text_input("Periodo", value=str(sel.iloc[0].get("PERIODO", "")))
                                                try: i_v = pd.to_datetime(sel.iloc[0].get("FECHA DE INICIO")).date()
                                                except: i_v = date.today()
                                                try: f_v = pd.to_datetime(sel.iloc[0].get("FECHA DE FIN")).date()
                                                except: f_v = date.today()
                                                
                                                ini_v = st.date_input("Fecha de Inicio", value=i_v)
                                                fin_v = st.date_input("Fecha de Fin", value=f_v)
                                                lnk_e = st.text_input("Link de sustento", value=str(sel.iloc[0].get("LINK", "")))
                                                
                                                if st.form_submit_button("Actualizar Vacaciones"):
                                                    d_goz = (fin_v - ini_v).days + 1
                                                    if d_goz < 0: d_goz = 0
                                                    
                                                    dfs[h_name].at[idx, "periodo"] = per_e
                                                    dfs[h_name].at[idx, "fecha de inicio"] = ini_v
                                                    dfs[h_name].at[idx, "fecha de fin"] = fin_v
                                                    dfs[h_name].at[idx, "días gozados"] = d_goz
                                                    dfs[h_name].at[idx, "link"] = lnk_e
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
                                                    elif col.lower() in ["sueldo", "días generados", "días gozados", "saldo", "edad", "monto"]:
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
                                        st.info("Activa la casilla en la tabla para editar o eliminar.")
            else:
                st.error("DNI no encontrado en la base de datos.")

    elif m == "➕ Registro" and not es_lector:
        with st.form("reg_p"):
            st.write("### Alta de Nuevo Trabajador")
            d = st.text_input("DNI")
            n = st.text_input("Nombres").upper()
            l = st.text_input("Link File")

            if st.form_submit_button("Registrar"):
                if d and n:
                    dfs["PERSONAL"] = pd.concat(
                        [dfs["PERSONAL"], pd.DataFrame([{"dni": d, "apellidos y nombres": n, "link": l}])], ignore_index=True
                    )
                    save_data(dfs)
                    st.success("Registrado correctamente")

    elif m == "📊 Nómina General":
        st.markdown("<h2 style='color: #FFD700;'>👥 Trabajadores registrados en el sistema</h2>", unsafe_allow_html=True)
        
        busqueda = st.text_input("🔍 Buscar por nombre o DNI:").strip().lower()
        df_nom = dfs["PERSONAL"].copy()
        
        if busqueda:
            df_nom = df_nom[df_nom['apellidos y nombres'].str.lower().str.contains(busqueda, na=False) | df_nom['dni'].astype(str).str.contains(busqueda, na=False)]

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
                    if 'dni' in dfs[h].columns:
                        dfs[h] = dfs[h][~dfs[h]['dni'].astype(str).isin(dnis)]
                
                save_data(dfs)
                st.success("Registros eliminados correctamente del sistema y del Excel.")
                st.rerun()












# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import date
from io import BytesIO
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. CONFIGURACIÓN Y CONSTANTES ---
DB = "DB_SISTEMA_GTH.xlsx"
F_N = "MG. ARTURO JAVIER GALINDO MARTINEZ"
F_C = "JEFE DE GESTIÓN DEL TALENTO HUMANO"
TEXTO_CERT = "LA OFICINA DE GESTIÓN DE TALENTO HUMANO DE LA UNIVERSIDAD PRIVADA DE HUANCAYO “FRANKLIN ROOSEVELT”, CERTIFICA QUE:"
MOTIVOS_CESE = ["Término de contrato", "Renuncia", "Despido", "Mutuo acuerdo", "Fallecimiento", "Otros"]

# Diccionario maestro de columnas para asegurar que nunca falten
COLUMNAS = {
    "PERSONAL": ["dni", "apellidos y nombres", "link"],
    "DATOS GENERALES": ["apellidos y nombres", "dni", "dirección", "link de dirección", "estado civil", "fecha de nacimiento", "edad"],
    "DATOS FAMILIARES": ["parentesco", "apellidos y nombres", "dni", "fecha de nacimiento", "edad", "estudios", "telefono"],
    "EXP. LABORAL": ["tipo de experiencia", "lugar", "puesto", "fecha inicio", "fecha de fin", "motivo cese"],
    "FORM. ACADEMICA": ["grado, titulo o especialización", "descripcion", "universidad", "año"],
    "INVESTIGACION": ["año publicación", "autor, coautor o asesor", "tipo de investigación publicada", "nivel de publicación", "lugar de publicación"],
    "CONTRATOS": ["id", "dni", "cargo", "sueldo", "f_inicio", "f_fin", "tipo", "tipo contrato", "temporalidad", "link", "estado", "motivo cese"],
    "VACACIONES": ["periodo", "fecha de inicio", "fecha de fin", "días generados", "días gozados", "saldo", "fecha de goce inicial", "fecha de goce final", "link"],
    "OTROS BENEFICIOS": ["periodo", "tipo de beneficio", "link"],
    "MERITOS Y DEMERITOS": ["periodo", "merito o demerito", "motivo", "link"],
    "EVALUACION DEL DESEMPEÑO": ["periodo", "merito o demerito", "motivo", "link"],
    "LIQUIDACIONES": ["periodo", "firmo", "link"]
}

# --- 2. FUNCIONES DE DATOS ---
def load_data():
    if not os.path.exists(DB):
        with pd.ExcelWriter(DB) as w:
            for h, cols in COLUMNAS.items(): pd.DataFrame(columns=cols).to_excel(w, sheet_name=h, index=False)
    
    dfs = {}
    with pd.ExcelFile(DB) as x:
        for h in COLUMNAS.keys():
            df = pd.read_excel(x, h) if h in x.sheet_names else pd.DataFrame(columns=COLUMNAS[h])
            # Normalizar columnas a minúsculas y sin espacios para evitar el KeyError
            df.columns = [str(c).strip().lower() for c in df.columns]
            # Asegurar que la columna 'dni' exista en el DataFrame cargado
            if "dni" not in df.columns and h != "PERSONAL":
                df["dni"] = None
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
    
    # --- AÑADIR LOGO AL INICIO ---
    if os.path.exists("logo_universidad.png"):
        # Esto inserta el logo centrado al inicio del documento
        section = doc.sections[0]
        header = section.header
        p_logo = header.paragraphs[0]
        p_logo.alignment = 1 # Centrado
        r_logo = p_logo.add_run()
        r_logo.add_picture("logo_universidad.png", width=Inches(1.5)) 
    # -----------------------------

    p = doc.add_paragraph(); p.alignment = 1
    r = p.add_run("CERTIFICADO DE TRABAJO"); r.bold = True; r.font.name = 'Arial'; r.font.size = Pt(24)
    doc.add_paragraph("\n" + TEXTO_CERT)
    p2 = doc.add_paragraph(); p2.add_run("El TRABAJADOR "); p2.add_run(nom).bold = True
    p2.add_run(f", identificado con DNI N° {dni}, laboró en nuestra Institución bajo el siguiente detalle:")
    t = doc.add_table(rows=1, cols=3); t.style = 'Table Grid'
    for i, h in enumerate(["CARGO", "FECHA INICIO", "FECHA FIN"]): t.rows[0].cells[i].text = h
    for _, row in df_c.iterrows():
        c = t.add_row().cells
        c[0].text = str(row.get('cargo', ''))
        c[1].text = pd.to_datetime(row.get('f_inicio')).strftime('%d/%m/%Y') if pd.notnull(row.get('f_inicio')) else ""
        c[2].text = pd.to_datetime(row.get('f_fin')).strftime('%d/%m/%Y') if pd.notnull(row.get('f_fin')) else ""
    doc.add_paragraph("\n\nHuancayo, " + date.today().strftime("%d/%m/%Y")).alignment = 2
    f = doc.add_paragraph(); f.alignment = 1; f.add_run("\n\n\n__________________________\n" + F_N + "\n" + F_C).bold = True
    b = BytesIO(); doc.save(b); b.seek(0); return b

# --- 3. LOGIN ---
st.set_page_config(page_title="GTH Roosevelt", layout="wide")
if "rol" not in st.session_state: st.session_state.rol = None

if st.session_state.rol is None:
    st.markdown("<h2 style='text-align:center;'>UNIVERSIDAD ROOSEVELT - SISTEMA GTH</h2>", unsafe_allow_html=True)
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if u.lower() == "admin": st.session_state.rol = "Admin"
        elif u.lower() == "supervisor" and p == "123": st.session_state.rol = "Supervisor"
        elif u.lower() == "lector" and p == "123": st.session_state.rol = "Lector"
        else: st.error("Acceso denegado")
        if st.session_state.rol: st.rerun()
else:
    dfs = load_data()
    es_lector = st.session_state.rol == "Lector"
    
    m = st.sidebar.radio("MENÚ", ["🔍 Consulta", "➕ Registro", "📊 Nómina General"])
    if st.sidebar.button("Cerrar Sesión"): st.session_state.rol = None; st.rerun()

    if m == "🔍 Consulta":
        dni_b = st.text_input("DNI del colaborador:").strip()
        if dni_b:
            # Buscar en PERSONAL
            pers = dfs["PERSONAL"][dfs["PERSONAL"]["dni"] == dni_b]
            if not pers.empty:
                nom_c = pers.iloc[0]["apellidos y nombres"]
                st.header(f"👤 {nom_c}")
                
                # GRUPO 1: Presentados por el trabajador
                st.subheader("📁 Documentos presentados por el trabajador")
                t_trab = st.tabs(["Datos Generales", "Exp. Laboral", "Form. Académica", "Investigación", "Datos Familiares"])
                h_trab = ["DATOS GENERALES", "EXP. LABORAL", "FORM. ACADEMICA", "INVESTIGACION", "DATOS FAMILIARES"]
                
                # GRUPO 2: Documentos internos
                st.subheader("📂 Documentos internos / Gestión")
                t_int = st.tabs(["Contratos", "Vacaciones", "Otros Beneficios", "Méritos/Demer.", "Evaluación", "Liquidaciones"])
                h_int = ["CONTRATOS", "VACACIONES", "OTROS BENEFICIOS", "MERITOS Y DEMERITOS", "EVALUACION DEL DESEMPEÑO", "LIQUIDACIONES"]
                
                all_t = t_trab + t_int
                all_h = h_trab + h_int

                for i, tab in enumerate(all_t):
                    h_name = all_h[i]
                    with tab:
                        # Filtrado seguro
                        if "dni" in dfs[h_name].columns:
                            c_df = dfs[h_name][dfs[h_name]["dni"] == dni_b]
                        else:
                            c_df = pd.DataFrame(columns=COLUMNAS[h_name])
                        
                        if h_name == "CONTRATOS":
                            if not c_df.empty:
                                st.download_button("📄 Generar Word Certificado", gen_word(nom_c, dni_b, c_df), f"Cert_{dni_b}.docx")
                            
                            vst = c_df.copy()
                            vst.insert(0, "Sel", False)
                            ed = st.data_editor(vst, hide_index=True, use_container_width=True, key=f"ed_{h_name}", disabled=es_lector)
                            sel = ed[ed["Sel"] == True]

                            if not es_lector:
                                c1, c2 = st.columns(2)
                                with c1:
                                    with st.expander("➕ Añadir Contrato"):
                                        with st.form("f_add_cont"):
                                            car = st.text_input("Cargo"); sue = st.number_input("Sueldo", 0.0)
                                            ini = st.date_input("Inicio"); fin = st.date_input("Fin")
                                            tip = st.selectbox("Tipo", ["Docente", "Administrativo"])
                                            est = "ACTIVO" if fin >= date.today() else "CESADO"
                                            mot = st.selectbox("Motivo Cese", ["Vigente"] + MOTIVOS_CESE) if est == "CESADO" else "Vigente"
                                            if st.form_submit_button("Guardar"):
                                                nid = dfs[h_name]["id"].max() + 1 if not dfs[h_name].empty else 1
                                                new = {"id":nid, "dni":dni_b, "cargo":car, "sueldo":sue, "f_inicio":ini, "f_fin":fin, "tipo":tip, "estado":est, "motivo cese":mot}
                                                dfs[h_name] = pd.concat([dfs[h_name], pd.DataFrame([new])], ignore_index=True); save_data(dfs); st.rerun()
                                with c2:
                                    if not sel.empty and st.button("🚨 Eliminar Contrato"):
                                        dfs[h_name] = dfs[h_name][dfs[h_name]["id"] != sel.iloc[0]["id"]]; save_data(dfs); st.rerun()
                        else:
                            st.dataframe(c_df, use_container_width=True, hide_index=True)
                            if not es_lector:
                                with st.expander(f"➕ Registrar en {h_name}"):
                                    with st.form(f"f_{h_name}"):
                                        new_row = {"dni": dni_b}
                                        cols_fill = [c for c in COLUMNAS[h_name] if c not in ["dni", "apellidos y nombres", "edad"]]
                                        for col in cols_fill:
                                            new_row[col] = st.text_input(col.title())
                                        if st.form_submit_button("Confirmar"):
                                            dfs[h_name] = pd.concat([dfs[h_name], pd.DataFrame([new_row])], ignore_index=True); save_data(dfs); st.rerun()
            else:
                st.error("DNI no registrado en el personal principal.")

    elif m == "➕ Registro":
        if es_lector: st.error("No autorizado")
        else:
            with st.form("reg_p"):
                st.write("### Alta de Nuevo Trabajador")
                d = st.text_input("DNI"); n = st.text_input("Apellidos y Nombres").upper(); l = st.text_input("Link File")
                if st.form_submit_button("Registrar"):
                    if d and n:
                        dfs["PERSONAL"] = pd.concat([dfs["PERSONAL"], pd.DataFrame([{"dni":d, "apellidos y nombres":n, "link":l}])], ignore_index=True)
                        save_data(dfs); st.success("Registrado correctamente")

    elif m == "📊 Nómina General":
        st.header("Base de Datos General de Personal")
        st.dataframe(dfs["PERSONAL"], use_container_width=True, hide_index=True)


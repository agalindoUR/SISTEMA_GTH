# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import date
from io import BytesIO
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. CONFIGURACIÓN Y CONSTANTES ---
DB = "DB_SISTEMA_GTH.xlsx"
F_N = "MG. ARTURO JAVIER GALINDO MARTINEZ"
F_C = "JEFE DE GESTIÓN DEL TALENTO HUMANO"
TEXTO_CERT = "LA OFICINA DE GESTIÓN DE TALENTO HUMANO DE LA UNIVERSIDAD PRIVADA DE HUANCAYO “FRANKLIN ROOSEVELT”, CERTIFICA QUE:"
MOTIVOS_CESE = ["Término de contrato", "Renuncia", "Despido", "Mutuo acuerdo", "Fallecimiento", "Otros"]

# Estructura de columnas según documento [cite: 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25]
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
def load_all_data():
    if not os.path.exists(DB):
        with pd.ExcelWriter(DB) as w:
            for hoja, cols in COLUMNAS.items():
                pd.DataFrame(columns=cols).to_excel(w, sheet_name=hoja, index=False)
    dfs = {}
    with pd.ExcelFile(DB) as x:
        for hoja in COLUMNAS.keys():
            df = pd.read_excel(x, hoja) if hoja in x.sheet_names else pd.DataFrame(columns=COLUMNAS[hoja])
            df.columns = [str(c).strip().lower() for c in df.columns]
            if "dni" in df.columns:
                df["dni"] = df["dni"].astype(str).str.strip().replace(r'\.0$', '', regex=True)
            dfs[hoja] = df
    return dfs

def save_all_data(dfs):
    with pd.ExcelWriter(DB) as w:
        for hoja, df in dfs.items():
            df_save = df.copy()
            df_save.columns = [c.upper() for c in df_save.columns]
            df_save.to_excel(w, sheet_name=hoja, index=False)

def gen_word_cert(nom, dni, df_c):
    doc = Document()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("CERTIFICADO DE TRABAJO")
    r.bold = True; r.font.name = 'Arial'; r.font.size = Pt(24) # [cite: 57]
    doc.add_paragraph("\n" + TEXTO_CERT).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY # [cite: 58]
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p2.add_run(f"El TRABAJADOR ").add_run(nom).bold = True
    p2.add_run(f", identificado con DNI N° {dni}, laboró en nuestra Institución bajo el siguiente detalle:") # [cite: 59]
    t = doc.add_table(rows=1, cols=3); t.style = 'Table Grid'
    for i, h in enumerate(["CARGO", "FECHA INICIO", "FECHA FIN"]): t.rows[0].cells[i].text = h # [cite: 60]
    for _, row in df_c.iterrows():
        c = t.add_row().cells
        c[0].text = str(row.get('cargo', ''))
        c[1].text = pd.to_datetime(row.get('f_inicio')).strftime('%d/%m/%Y') if pd.notnull(row.get('f_inicio')) else ""
        c[2].text = pd.to_datetime(row.get('f_fin')).strftime('%d/%m/%Y') if pd.notnull(row.get('f_fin')) else ""
    doc.add_paragraph("\n\nHuancayo, " + date.today().strftime("%d de %B de %Y")).alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f = doc.add_paragraph(); f.alignment = WD_ALIGN_PARAGRAPH.CENTER
    f.add_run("\n\n\n__________________________\n" + F_N + "\n" + F_C).bold = True # [cite: 61, 62]
    b = BytesIO(); doc.save(b); b.seek(0); return b

# --- 3. INTERFAZ Y LOGIN ---
st.set_page_config(page_title="GTH Roosevelt", layout="wide")
if "rol" not in st.session_state: st.session_state.rol = None

if st.session_state.rol is None:
    st.markdown("<h2 style='text-align:center;'>UNIVERSIDAD ROOSEVELT - SISTEMA GTH</h2>", unsafe_allow_html=True)
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"): # [cite: 28-32]
        if u.lower() == "admin": st.session_state.rol = "Admin"
        elif u.lower() == "supervisor" and p == "123": st.session_state.rol = "Supervisor"
        elif u.lower() == "lector" and p == "123": st.session_state.rol = "Lector"
        else: st.error("Acceso denegado")
        if st.session_state.rol: st.rerun()
else:
    dfs = load_all_data()
    es_lector = st.session_state.rol == "Lector"
    
    # Menú Lateral 
    m = st.sidebar.radio("MENÚ", ["🔍 Consulta", "➕ Registro", "📊 Verificar"])
    if st.sidebar.button("Cerrar Sesión"): st.session_state.rol = None; st.rerun()

    if m == "🔍 Consulta":
        dni_c = st.text_input("Consultar DNI del colaborador:").strip()
        if dni_c:
            p_data = dfs["PERSONAL"][dfs["PERSONAL"]["dni"] == dni_c]
            if not p_data.empty:
                nom_c = p_data.iloc[0]["apellidos y nombres"]
                st.header(f"👤 {nom_c}")
                
                # Organización por grupos [cite: 35, 42, 48]
                st.subheader("Presentados por el trabajador")
                pest_trab = ["Datos Generales", "Exp. Laboral", "Form. Académica", "Investigación", "Datos Familiares"]
                tabs_t = st.tabs(pest_trab)
                
                st.subheader("Documentos internos")
                pest_int = ["Contratos", "Vacaciones", "Otros Beneficios", "Méritos/Demer.", "Evaluación", "Liquidaciones"]
                tabs_i = st.tabs(pest_int)
                
                all_tabs = tabs_t + tabs_i
                all_hojas = ["DATOS GENERALES", "EXP. LABORAL", "FORM. ACADEMICA", "INVESTIGACION", "DATOS FAMILIARES", 
                             "CONTRATOS", "VACACIONES", "OTROS BENEFICIOS", "MERITOS Y DEMERITOS", "EVALUACION DEL DESEMPEÑO", "LIQUIDACIONES"]

                for i, tab in enumerate(all_tabs):
                    h = all_hojas[i]
                    with tab:
                        current_df = dfs[h][dfs[h]["dni"] == dni_c]
                        
                        if h == "CONTRATOS": # [cite: 49-55]
                            if not current_df.empty:
                                st.download_button("📄 Word: Certificado", gen_word_cert(nom_c, dni_c, current_df), f"Cert_{dni_c}.docx")
                            
                            v_df = current_df.copy()
                            v_df.insert(0, "Seleccionar", False)
                            ed = st.data_editor(v_df, hide_index=True, use_container_width=True, key=f"ed_{h}", disabled=es_lector)
                            sel = ed[ed["Seleccionar"] == True]

                            if not es_lector:
                                col1, col2 = st.columns(2)
                                with col1:
                                    with st.expander("➕ Nuevo Contrato", expanded=False):
                                        with st.form("f_add_c"):
                                            c_cargo = st.text_input("Cargo"); c_sueldo = st.number_input("Sueldo", 0.0)
                                            c_ini = st.date_input("F. Inicio"); c_fin = st.date_input("F. Fin")
                                            c_tipo = st.selectbox("Tipo", ["Docente", "Administrativo"])
                                            c_est = "ACTIVO" if c_fin >= date.today() else "CESADO"
                                            c_mot = st.selectbox("Motivo Cese", ["Vigente"] + MOTIVOS_CESE) if c_est == "CESADO" else "Vigente"
                                            if st.form_submit_button("Guardar Contrato"):
                                                nid = dfs[h]["id"].max() + 1 if not dfs[h].empty else 1
                                                n_row = {"id":nid, "dni":dni_c, "cargo":c_cargo, "sueldo":c_sueldo, "f_inicio":c_ini, "f_fin":c_fin, "tipo":c_tipo, "estado":c_est, "motivo cese":c_mot}
                                                dfs[h] = pd.concat([dfs[h], pd.DataFrame([n_row])], ignore_index=True); save_all_data(dfs); st.rerun()
                                with col2:
                                    if not sel.empty:
                                        if st.button("🚨 Eliminar Seleccionado"):
                                            dfs[h] = dfs[h][dfs[h]["id"] != sel.iloc[0]["id"]]; save_all_data(dfs); st.rerun()
                        else:
                            st.dataframe(current_df, use_container_width=True, hide_index=True)
                            if not es_lector:
                                with st.expander(f"➕ Añadir a {h}"):
                                    with st.form(f"f_add_{h}"):
                                        new_data = {"dni": dni_c}
                                        # Filtramos columnas que no se llenan manualmente
                                        cols_to_fill = [c for c in COLUMNAS[h] if c not in ["dni", "apellidos y nombres", "edad"]]
                                        for col in cols_to_fill:
                                            new_data[col] = st.text_input(col.title())
                                        if st.form_submit_button(f"Confirmar Registro en {h}"):
                                            # Calculo de edad si aplica [cite: 5, 7]
                                            if "fecha de nacimiento" in new_data:
                                                try:
                                                    f_n = pd.to_datetime(new_data["fecha de nacimiento"])
                                                    new_data["edad"] = date.today().year - f_n.year
                                                except: pass
                                            dfs[h] = pd.concat([dfs[h], pd.DataFrame([new_data])], ignore_index=True); save_all_data(dfs); st.rerun()
            else:
                st.error("DNI no encontrado en PERSONAL.")

    elif m == "➕ Registro": # [cite: 37]
        if es_lector: st.error("Sin permisos")
        else:
            with st.form("f_reg_p"):
                rd = st.text_input("DNI"); rn = st.text_input("Apellidos y Nombres").upper(); rl = st.text_input("Link Drive")
                if st.form_submit_button("Registrar Nuevo Colaborador"):
                    if rd and rn:
                        dfs["PERSONAL"] = pd.concat([dfs["PERSONAL"], pd.DataFrame([{"dni":rd, "apellidos y nombres":rn, "link":rl}])], ignore_index=True)
                        save_all_data(dfs); st.success(f"Registrado: {rn}")

    elif m == "📊 Verificar": # [cite: 38, 39]
        st.header("Nómina de Personal")
        busq = st.text_input("Buscar en nómina:")
        disp = dfs["PERSONAL"]
        if busq: disp = disp[disp.apply(lambda r: busq.lower() in r.astype(str).str.lower().values, axis=1)]
        st.dataframe(disp, use_container_width=True, hide_index=True)

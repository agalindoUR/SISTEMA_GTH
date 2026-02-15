# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import date
from io import BytesIO
from docx import Document
from docx.shared import Pt

# --- CONFIGURACIÓN ---
DB = "DB_SISTEMA_GTH.xlsx"
F_N = "MG. ARTURO J. GALINDO MARTINEZ"
F_C = "JEFE DE GESTIÓN DE TALENTO HUMANO"
CAB = "LA OFICINA DE GESTIÓN DE TALENTO HUMANO DE LA UNIVERSIDAD PRIVADA DE HUANCAYO “FRANKLIN ROOSEVELT”, CERTIFICA QUE:"

def load():
    if not os.path.exists(DB):
        p = pd.DataFrame(columns=["DNI", "Apellidos y nombres"])
        c = pd.DataFrame(columns=["ID", "DNI", "Cargo", "Sueldo", "F_Inicio", "F_Fin", "Tipo", "Modalidad", "Temporalidad", "Estado", "Tipo Colaborador", "Tipo Contrato", "Motivo Cese"])
        return p, c
    with pd.ExcelFile(DB) as x:
        p = pd.read_excel(x, "PERSONAL")
        c = pd.read_excel(x, "CONTRATOS")
    
    # Limpieza y normalización de columnas
    p["DNI"] = p["DNI"].astype(str).str.strip()
    c["DNI"] = c["DNI"].astype(str).str.strip()
    p.columns = [col.strip().lower() for col in p.columns]
    c.columns = [col.strip().lower() for col in c.columns]
    return p, c

def save(p, c):
    with pd.ExcelWriter(DB) as w:
        p.to_excel(w, "PERSONAL", index=False)
        c.to_excel(w, "CONTRATOS", index=False)

def gen_doc(nom, dni, df):
    doc = Document()
    t = doc.add_paragraph(); t.alignment = 1; r = t.add_run("CERTIFICADO DE TRABAJO"); r.bold = True; r.font.size = Pt(16)
    h = doc.add_paragraph(); h.alignment = 1; h.add_run(CAB).font.size = Pt(10)
    b = doc.add_paragraph(); b.alignment = 3
    b.add_run(f"\nEl TRABAJADOR {nom}, identificado con DNI {dni} laboró en nuestra Institución bajo el siguiente detalle:").font.size = Pt(11)
    
    tb = doc.add_table(rows=1, cols=3); tb.style = 'Table Grid'
    for i, v in enumerate(["Cargo", "Fecha Inicio", "Fecha Fin"]):
        ph = tb.rows[0].cells[i].paragraphs[0]; ph.alignment = 1; rn = ph.add_run(v); rn.bold = True
    
    for _, f in df.iterrows():
        rc = tb.add_row().cells
        rc[0].text, rc[1].text, rc[2].text = str(f.get('cargo','')), str(f.get('f_inicio','')), str(f.get('f_fin',''))
        
    f_p = doc.add_paragraph(f"\nHuancayo, {date.today().day} de febrero del 2026"); f_p.alignment = 2
    sig = doc.add_paragraph(f"\n\n\n{F_N}\n{F_C}"); sig.alignment = 1
    for run in sig.runs: run.bold = True
    buf = BytesIO(); doc.save(buf); buf.seek(0); return buf

# --- INTERFAZ ---
st.set_page_config(page_title="GTH Roosevelt", layout="wide")
dp, dc = load()

st.sidebar.title("SISTEMA GTH")
m = st.sidebar.radio("MENÚ", ["🔍 Consulta", "➕ Registro Personal", "📊 Nómina General"])

if m == "🔍 Consulta":
    dni_busq = st.text_input("Ingrese DNI:").strip()
    if dni_busq:
        u = dp[dp['dni'] == dni_busq]
        if not u.empty:
            nom = u.iloc[0]['apellidos y nombres']
            st.success(f"Trabajador: {nom}")
            cn = dc[dc['dni'] == dni_busq].reset_index(drop=True)
            
            st.write("### Historial de Contratos")
            st.dataframe(cn, use_container_width=True, hide_index=True)
            
            # --- ACCIONES DE CONTRATOS ---
            tab1, tab2, tab3 = st.tabs(["➕ Agregar", "📝 Modificar", "🗑️ Eliminar"])
            
            with tab1:
                with st.form("add_con"):
                    c1, c2, c3 = st.columns(3)
                    f_car = c1.text_input("Cargo")
                    f_sue = c2.number_input("Sueldo", min_value=0.0)
                    f_est = c3.selectbox("Estado", ["ACTIVO", "CESADO"])
                    f_ini = c1.date_input("Inicio")
                    f_fin = c2.date_input("Fin")
                    f_mod = c3.selectbox("Modalidad", ["Presencial", "Remoto", "Mixto"])
                    f_tem = c1.selectbox("Temporalidad", ["Plazo fijo", "Indeterminado"])
                    f_tip = c2.selectbox("Tipo", ["Administrativo", "Docente"])
                    f_mot = c3.text_input("Motivo Cese")
                    if st.form_submit_button("Guardar Nuevo"):
                        new_id = dc['id'].max() + 1 if not dc.empty else 1
                        new_row = {"id":new_id, "dni":dni_busq, "cargo":f_car, "sueldo":f_sue, "f_inicio":f_ini, "f_fin":f_fin, "estado":f_est, "modalidad":f_mod, "temporalidad":f_tem, "tipo":f_tip, "motivo cese":f_mot}
                        dc = pd.concat([dc, pd.DataFrame([new_row])], ignore_index=True)
                        save(dp, dc); st.rerun()

            with tab2:
                if not cn.empty:
                    sel_id = st.selectbox("ID a Modificar", cn['id'])
                    idx = dc[dc['id'] == sel_id].index[0]
                    with st.form

# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import date
from io import BytesIO
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

DB, F_N, F_C = "DB_SISTEMA_GTH.xlsx", "MG. ARTURO J. GALINDO MARTINEZ", "JEFE DE GESTIÓN DE TALENTO HUMANO"
CAB = "LA OFICINA DE GESTIÓN DE TALENTO HUMANO DE LA UNIVERSIDAD PRIVADA DE HUANCAYO “FRANKLIN ROOSEVELT”, CERTIFICA QUE:"

def load():
    if not os.path.exists(DB):
        p = pd.DataFrame(columns=["DNI", "Apellidos y nombres"])
        c = pd.DataFrame(columns=["DNI", "Cargo", "Sueldo", "F_Inicio", "F_Fin", "Tipo", "Modalidad", "Temporalidad", "Link", "Estado", "Tipo Colaborador", "Tipo Contrato", "Motivo Cese"])
        with pd.ExcelWriter(DB) as w:
            p.to_excel(w, "PERSONAL", index=False); c.to_excel(w, "CONTRATOS", index=False)
        return p, c
    with pd.ExcelFile(DB) as x:
        p, c = pd.read_excel(x, "PERSONAL"), pd.read_excel(x, "CONTRATOS")
    p["DNI"] = p["DNI"].astype(str).str.strip()
    c["DNI"] = c["DNI"].astype(str).str.strip()
    return p, c

def save(p, c):
    with pd.ExcelWriter(DB) as w:
        p.to_excel(w, "PERSONAL", index=False); c.to_excel(w, "CONTRATOS", index=False)

def gen_doc(nom, dni, df):
    doc = Document()
    t = doc.add_paragraph(); t.alignment = 1
    r = t.add_run("CERTIFICADO DE TRABAJO"); r.bold = True; r.font.size = Pt(16)
    h = doc.add_paragraph(); h.alignment = 1
    h.add_run(CAB).font.size = Pt(10)
    b = doc.add_paragraph(); b.alignment = 3
    # Redacción oficial solicitada
    b.add_run(f"\nEl TRABAJADOR {nom}, identificado con DNI {dni} laboró en nuestra Institución bajo el siguiente detalle:").font.size = Pt(11)
    tb = doc.add_table(rows=1, cols=3); tb.style = 'Table Grid'
    for i, v in enumerate(["Cargo", "Fecha Inicio", "Fecha Fin"]):
        ph = tb.rows[0].cells[i].paragraphs[0]; ph.alignment = 1; rn = ph.add_run(v); rn.bold = True
    for _, f in df.iterrows():
        rc = tb.add_row().cells
        rc[0].text, rc[1].text, rc[2].text = str(f.get('Cargo','')), str(f.get('F_Inicio','')), str(f.get('F_Fin',''))
        for cl in rc: cl.paragraphs[0].alignment = 1
    f_p = doc.add_paragraph(f"\nHuancayo, {date.today().day} de febrero del 2026"); f_p.alignment = 2
    sig = doc.add_paragraph(f"\n\n\n{F_N}\n{F_C}"); sig.alignment = 1
    for run in sig.runs: run.bold = True
    buf = BytesIO(); doc.save(buf); buf.seek(0)
    return buf

st.set_page_config(page_title="GTH Roosevelt", layout="wide")
dp, dc = load()
st.sidebar.title("SISTEMA GTH")
m = st.sidebar.radio("MENÚ", ["🔍 Consulta", "➕ Registro", "📊 Nómina"])

if m == "🔍 Consulta":
    dni = st.text_input("DNI:").strip()
    if dni:
        u = dp[dp['DNI'] == dni]
        if not u.empty:
            nom = u.iloc[0]['Apellidos y nombres']
            st.success(f"Trabajador: {nom}")
            cn = dc[dc['DNI'] == dni].reset_index(drop=True)
            # Tabla con todas las columnas
            st.dataframe(cn, use_container_width=True, hide_index=True)
            if st.button("➕ Nuevo Contrato"): st.session_state.f = True
            if st.session_state.get("f"):
                with st.form("n_c"):
                    c1, c2, c3 = st.columns(3)
                    f_car = c1.text_input("Cargo")
                    f_sue = c2.number_input("Sueldo", min_value=0)
                    f_tip = c3.selectbox("Tipo", ["Administrativo", "Docente"])
                    f_mod = c1.selectbox("Mod.", ["Presencial", "Remoto", "Mixto"])
                    f_tem = c2.selectbox("Temp.", ["Plazo fijo", "Indeterminado"])
                    f_est = c3.selectbox("Estado", ["ACTIVO", "CESADO"])
                    f_col = c1.text_input("Colaborador", value="Administrativo")
                    f_tcon = c2.text_input("Contrato", value="Planilla completo")
                    f_link = c3.text_input("Link", value="None")
                    f_ini = c1.date_input("Inicio")
                    f_fin = c2.date_input("Fin")
                    f_cese = c3.text_input("Motivo Cese", value="None")
                    if st.form_submit_button("Guardar"):
                        new = {"DNI":dni,"Cargo":f_car,"Sueldo":f_sue,"F_Inicio":f_ini,"F_Fin":f_fin,"Tipo":f_tip,"Modalidad":f_mod,"Temporalidad":f_tem,"Estado":f_est,"Link":f_link,"Tipo Colaborador":f_col,"Tipo Contrato":f_tcon,"Motivo Cese":f_cese}
                        dc = pd.concat([dc, pd.DataFrame([new])], ignore_index=True)
                        save(dp, dc); st.session_state.f = False; st.rerun()
            if not cn.empty:
                st.download_button("📄 Word", gen_doc(nom, dni, cn), f"Cert_{dni}.docx")
        else: st.error("No registrado.")

elif m == "➕ Registro":
    st.subheader("Nuevo Ingreso")
    with st.form("r_p"):
        d, n = st.text_input("DNI"), st.text_input("Nombres")
        if st.form_submit_button("Ok"):
            dp = pd.concat([dp, pd.DataFrame([{"DNI":d,"Apellidos y nombres":n.upper()}])], ignore_index=True)
            save(dp, dc); st.success("Ok")

elif m == "📊 Nómina":
    st.title("Nómina")
    st.info("Módulo para planillas.")
    st.dataframe(dp, use_container_width=True)
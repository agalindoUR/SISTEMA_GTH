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
        c = pd.DataFrame(columns=["DNI", "Cargo", "Sueldo", "F_Inicio", "F_Fin", "Tipo", "Modalidad", "Temporalidad", "Link", "Estado", "Tipo Colaborador", "Tipo Contrato", "Motivo Cese"])
        return p, c
    with pd.ExcelFile(DB) as x:
        p, c = pd.read_excel(x, "PERSONAL"), pd.read_excel(x, "CONTRATOS")
    
    # Limpieza de datos
    for df in [p, c]: 
        df["DNI"] = df["DNI"].astype(str).str.strip()
        df.columns = [col.strip() for col in df.columns] # Quita espacios en nombres de columnas
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
    # Redacción oficial solicitada
    b.add_run(f"\nEl TRABAJADOR {nom}, identificado con DNI {dni} laboró en nuestra Institución bajo el siguiente detalle:").font.size = Pt(11)
    
    tb = doc.add_table(rows=1, cols=3); tb.style = 'Table Grid'
    for i, v in enumerate(["Cargo", "Fecha Inicio", "Fecha Fin"]):
        ph = tb.rows[0].cells[i].paragraphs[0]; ph.alignment = 1; rn = ph.add_run(v); rn.bold = True
    
    for _, f in df.iterrows():
        rc = tb.add_row().cells
        rc[0].text = str(f.get('Cargo', f.get('cargo', '')))
        rc[1].text = str(f.get('F_Inicio', f.get('f_inicio', '')))
        rc[2].text = str(f.get('F_Fin', f.get('f_fin', '')))
        
    f_p = doc.add_paragraph(f"\nHuancayo, {date.today().day} de febrero del 2026"); f_p.alignment = 2
    sig = doc.add_paragraph(f"\n\n\n{F_N}\n{F_C}"); sig.alignment = 1
    for run in sig.runs: run.bold = True
    buf = BytesIO(); doc.save(buf); buf.seek(0); return buf

# --- INTERFAZ ---
st.set_page_config(page_title="GTH Roosevelt", layout="wide")
dp, dc = load()

# Normalización para evitar el KeyError
dp.columns = [c.lower() for c in dp.columns]
dc.columns = [c.lower() for c in dc.columns]

st.sidebar.title("SISTEMA GTH")
m = st.sidebar.radio("MENÚ", ["🔍 Consulta", "➕ Registro", "📊 Nómina"])

if m == "🔍 Consulta":
    dni_busq = st.text_input("Ingrese DNI para consultar:").strip()
    if dni_busq:
        # Buscamos en la hoja personal
        u = dp[dp['dni'] == dni_busq]
        if not u.empty:
            nom = u.iloc[0]['apellidos y nombres']
            st.success(f"Trabajador: {nom}")
            
            # Filtramos contratos
            cn = dc[dc['dni'] == dni_busq].reset_index(drop=True)
            st.write("### Historial de Contratos")
            st.dataframe(cn, use_container_width=True, hide_index=True)
            
            c1, c2 = st.columns(2)
            if c1.button("➕ Nuevo Contrato"): st.session_state.f = True
            
            if not cn.empty:
                idx_del = c2.selectbox("Seleccione fila para eliminar", cn.index)
                if c2.button("🗑️ Eliminar Seleccionado"):
                    real_idx = dc[dc['dni'] == dni_busq].index[idx_del]
                    dc = dc.drop(real_idx)
                    save(dp, dc); st.rerun()

            if st.session_state.get("f"):
                with st.form("n_c"):
                    col1, col2 = st.columns(2)
                    f_car = col1.text_input("Cargo")
                    f_sue = col2.number_input("Sueldo", min_value=0)
                    f_est = col1.selectbox("Estado", ["ACTIVO", "CESADO"])
                    f_ini = col2.date_input("Fecha Inicio")
                    f_fin = col1.date_input("Fecha Fin")
                    if st.form_submit_button("Guardar"):
                        new = {"dni":dni_busq, "cargo":f_car, "sueldo":f_sue, "f_inicio":f_ini, "f_fin":f_fin, "estado":f_est}
                        dc = pd.concat([dc, pd.DataFrame([new])], ignore_index=True)
                        save(dp, dc); st.session_state.f = False; st.rerun()
            
            if not cn.empty:
                st.download_button("📄 Generar Certificado Word", gen_doc(nom, dni_busq, cn), f"Cert_{dni_busq}.docx")
        else:
            st.error("DNI no encontrado en la base de datos de Personal.")

elif m == "➕ Registro":
    st.subheader("Registrar Nuevo Personal")
    with st.form("r_p"):
        d, n = st.text_input("DNI"), st.text_input("Apellidos y Nombres")
        if st.form_submit_button("Registrar"):
            new_p = pd.DataFrame([{"dni":d, "apellidos y nombres":n.upper()}])
            dp = pd.concat([dp, new_p], ignore_index=True)
            save(dp, dc)
            st.success("Personal registrado con éxito.")

elif m == "📊 Nómina":
    st.subheader("Lista General de Personal")
    st.dataframe(dp, use_container_width=True)

# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import date
from io import BytesIO
from docx import Document

# --- CONFIGURACIÓN ---
DB = "DB_SISTEMA_GTH.xlsx"
F_N, F_C = "MG. ARTURO J. GALINDO MARTINEZ", "JEFE DE GESTIÓN DE TALENTO HUMANO"
MOTIVOS = ["Termino de contrato", "Renuncia", "Despido", "Mutuo acuerdo", "Fallecimiento", "Otros"]
SHS = ["PERSONAL", "FAMILIA", "FORM_ACAD", "EXP_LABORAL", "CONTRATOS", "VACACIONES", "BENEFICIOS", "MERITOS", "LIQUIDACIONES"]

def load():
    if not os.path.exists(DB):
        with pd.ExcelWriter(DB) as w:
            for s in SHS: pd.DataFrame(columns=["dni"]).to_excel(w, sheet_name=s, index=False)
    dfs = {}
    with pd.ExcelFile(DB) as x:
        for s in SHS:
            df = pd.read_excel(x, s)
            df.columns = [c.strip().lower() for c in df.columns]
            if "dni" in df.columns: df["dni"] = df["dni"].astype(str).str.strip()
            dfs[s.lower()] = df
    return dfs

def save(dfs):
    with pd.ExcelWriter(DB) as w:
        for s in SHS: dfs[s.lower()].to_excel(w, sheet_name=s, index=False)

def gen_doc(nom, dni, df):
    doc = Document()
    doc.add_heading('CERTIFICADO DE TRABAJO', 0)
    doc.add_paragraph(f"El TRABAJADOR {nom}, DNI {dni} laboró según detalle:")
    tb = doc.add_table(rows=1, cols=3); tb.style = 'Table Grid'
    for i, v in enumerate(["Cargo", "Inicio", "Fin"]): tb.rows[0].cells[i].text = v
    for _, f in df.iterrows():
        r = tb.add_row().cells
        r[0].text, r[1].text, r[2].text = str(f.get('cargo','')), str(f.get('f_inicio','')), str(f.get('f_fin',''))
    doc.add_paragraph(f"\nHuancayo, {date.today()}\n\n{F_N}\n{F_C}")
    buf = BytesIO(); doc.save(buf); buf.seek(0); return buf

# --- INTERFAZ ---
st.set_page_config(page_title="GTH Roosevelt", layout="wide")
dfs = load()
st.sidebar.title("SISTEMA GTH")
m = st.sidebar.radio("MENÚ", ["🔍 Consulta", "➕ Registro", "📊 Nómina"])

if m == "🔍 Consulta":
    dni_b = st.text_input("DNI:").strip()
    if dni_b:
        u = dfs["personal"][dfs["personal"]['dni'] == dni_b]
        if not u.empty:
            nom = u.iloc[0]['apellidos y nombres']
            st.header(f"👤 {nom}")
            tbs = st.tabs(SHS)
            with tbs[4]: # CONTRATOS
                cn = dfs["contratos"][dfs["contratos"]['dni'] == dni_b].reset_index(drop=True)
                st.dataframe(cn.drop(columns=['id','tipo colaborador'], errors='ignore'), use_container_width=True, hide_index=True)
                c1, c2, c3 = st.columns(3)
                with c1:
                    with st.expander("➕ Agregar"):
                        with st.form("f1"):
                            car, sue = st.text_input("Cargo"), st.number_input("Sueldo", 0.0)
                            est = st.selectbox("Estado", ["VIGENTE", "CESADO"])
                            mot = st.selectbox("Motivo", MOTIVOS) if est == "CESADO" else "Vigente"
                            if st.form_submit_button("Guardar"):
                                nid = dfs["contratos"]['id'].max() + 1 if not dfs["contratos"].empty else 1
                                nr = {"id":nid, "dni":dni_b, "cargo":car, "sueldo":sue, "estado":est, "motivo cese":mot, "f_inicio": date.today()}
                                dfs["contratos"] = pd.concat([dfs["contratos"], pd.DataFrame([nr])], ignore_index=True)
                                save(dfs); st.rerun()
                with c2:
                    if not cn.empty:
                        with st.expander("📝 Editar"):
                            ops = {f"{r['cargo']} ({r['f_inicio']})": r['id'] for _, r in cn.iterrows()}
                            sid = ops[st.selectbox("Contrato:", list(ops.keys()))]
                            idx = dfs["contratos"][dfs["contratos"]['id'] == sid].index[0]
                            with st.form("f2"):
                                ns, ne = st.number_input("Sueldo", value=float(dfs["contratos"].at[idx, 'sueldo'])), st.selectbox("Estado", ["VIGENTE", "CESADO"])
                                if st.form_submit_button("Actualizar"):
                                    dfs["contratos"].at[idx, 'sueldo'], dfs["contratos"].at[idx, 'estado'] = ns, ne
                                    save(dfs); st.rerun()
                with c3:
                    if not cn.empty:
                        with st.expander("🗑️ Borrar"):
                            ops_d = {f"{r['cargo']} ({r['f_inicio']})": r['id'] for _, r in cn.iterrows()}
                            sd = ops_d[st.selectbox("Borrar:", list(ops_d.keys()))]
                            if st.button("Confirmar Eliminar"):
                                dfs["contratos"] = dfs["contratos"][dfs["contratos"]['id'] != sd]
                                save(dfs); st.rerun()
                if not cn.empty: st.download_button("📄 Word", gen_doc(nom, dni_b, cn), f"Cert_{dni_b}.docx")
            for i, s in enumerate(SHS):
                if i != 4:
                    with tbs[i]: st.dataframe(dfs[s.lower()][dfs[s.lower()]['dni'] == dni_b], use_container_width=True)
        else: st.error("No existe.")
elif m == "➕ Registro":
    with st.form("r"):
        d_in, n_in = st.text_input("DNI"), st.text_input("Nombres")
        if st.form_submit_button("Registrar"):
            new_p = pd.DataFrame([{"dni":d_in, "apellidos y nombres":n_in.upper()}])
            dfs["personal"] = pd.concat([dfs["personal"], new_p], ignore_index=True)
            save(dfs); st.success("Ok.")
elif m == "📊 Nómina":
    st.dataframe(dfs["contratos"].drop(columns=['id'], errors='ignore'), use_container_width=True)

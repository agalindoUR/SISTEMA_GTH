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
            df = pd.read_excel(x, s) if s in x.sheet_names else pd.DataFrame(columns=["dni"])
            df.columns = [c.strip().lower() for c in df.columns]
            if "dni" in df.columns: df["dni"] = df["dni"].astype(str).str.strip()
            dfs[s.lower()] = df
    return dfs

def save(dfs):
    with pd.ExcelWriter(DB) as w:
        for s in SHS: dfs[s.lower()].to_excel(w, sheet_name=s, index=False)

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
            # Títulos con primera letra Mayúscula
            tbs = st.tabs([s.replace("_"," ").title() for s in SHS])
            
            with tbs[4]: # PESTAÑA CONTRATOS
                st.write("### Gestión de Contratos")
                cn = dfs["contratos"][dfs["contratos"]['dni'] == dni_b].reset_index(drop=True)
                
                # Vista limpia para el usuario (Sin ID, Sin Modalidad)
                vista = cn.drop(columns=['id','modalidad','tipo colaborador'], errors='ignore')
                vista.columns = [c.title() for c in vista.columns]
                
                # Selección por Checkbox
                sel_row = st.dataframe(vista, use_container_width=True, hide_index=True, 
                                     on_select="rerun", selection_mode="single_row")
                
                sel_idx = sel_row.selection.rows
                
                c1, c2 = st.columns(2)
                with c1:
                    with st.expander("➕ Agregar Nuevo Contrato"):
                        with st.form("add_f"):
                            f_car = st.text_input("Cargo")
                            f_sue = st.number_input("Sueldo", 0.0)
                            f_tip = st.selectbox("Tipo", ["Administrativo", "Docente"])
                            f_tem = st.selectbox("Temporalidad", ["Plazo fijo", "Indeterminado"])
                            f_est = st.selectbox("Estado", ["VIGENTE", "CESADO"])
                            f_mot = st.selectbox("Motivo Cese", MOTIVOS) if f_est == "CESADO" else "Vigente"
                            if st.form_submit_button("Guardar Contrato"):
                                nid = dfs["contratos"]['id'].max() + 1 if not dfs["contratos"].empty else 1
                                nr = {"id":nid, "dni":dni_b, "cargo":f_car, "sueldo":f_sue, "tipo":f_tip, 
                                      "temporalidad":f_tem, "estado":f_est, "motivo cese":f_mot, "f_inicio": date.today()}
                                dfs["contratos"] = pd.concat([dfs["contratos"], pd.DataFrame([nr])], ignore_index=True)
                                save(dfs); st.rerun()

                if sel_idx:
                    idx_real = cn.index[sel_idx[0]]
                    idx_db = dfs["contratos"][(dfs["contratos"]['dni']==dni_b) & (dfs["contratos"]['id']==cn.at[idx_real, 'id'])].index[0]
                    
                    with c2:
                        with st.expander("📝 Editar / 🗑️ Eliminar Seleccionado", expanded=True):
                            with st.form("edit_f"):
                                st.warning(f"Editando: {cn.at[idx_real, 'cargo']}")
                                e_car = st.text_input("Cargo", value=str(cn.at[idx_real, 'cargo']))
                                e_sue = st.number_input("Sueldo", value=float(cn.at[idx_real, 'sueldo']))
                                e_tip = st.text_input("Tipo", value=str(cn.at[idx_real, 'tipo']))
                                e_tem = st.text_input("Temporalidad", value=str(cn.at[idx_real, 'temporalidad']))
                                e_est = st.selectbox("Estado", ["VIGENTE", "CESADO"], index=0 if cn.at[idx_real, 'estado']=="VIGENTE" else 1)
                                e_mot = st.selectbox("Motivo Cese", MOTIVOS, index=MOTIVOS.index(cn.at[idx_real, 'motivo cese']) if cn.at[idx_real, 'motivo cese'] in MOTIVOS else 0) if e_est == "CESADO" else "Vigente"
                                
                                col_b1, col_b2 = st.columns(2)
                                if col_b1.form_submit_button("Actualizar Todo"):
                                    dfs["contratos"].at[idx_db, 'cargo'] = e_car
                                    dfs["contratos"].at[idx_db, 'sueldo'] = e_sue
                                    dfs["contratos"].at[idx_db, 'tipo'] = e_tip
                                    dfs["contratos"].at[idx_db, 'temporalidad'] = e_tem
                                    dfs["contratos"].at[idx_db, 'estado'] = e_est
                                    dfs["contratos"].at[idx_db, 'motivo cese'] = e_mot
                                    save(dfs); st.rerun()
                                
                                if col_b2.form_submit_button("🚨 Eliminar Registro"):
                                    dfs["contratos"] = dfs["contratos"].drop(idx_db)
                                    save(dfs); st.rerun()

            # Otras pestañas
            for i, s in enumerate(SHS):
                if i != 4:
                    with tbs[i]:
                        df_vista = dfs[s.lower()][dfs[s.lower()]['dni'] == dni_b]
                        df_vista.columns = [c.title() for c in df_vista.columns]
                        st.dataframe(df_vista, use_container_width=True, hide_index=True)
        else: st.error("No registrado.")

elif m == "➕ Registro":
    with st.form("r"):
        d_in, n_in = st.text_input("DNI"), st.text_input("Nombres")
        if st.form_submit_button("Registrar"):
            new_p = pd.DataFrame([{"dni":d_in, "apellidos y nombres":n_in.upper()}])
            dfs["personal"] = pd.concat([dfs["personal"], new_p], ignore_index=True)
            save(dfs); st.success("Ok.")

elif m == "📊 Nómina":
    st.subheader("Contratos Globales")
    nom_v = dfs["contratos"].drop(columns=['id','modalidad'], errors='ignore')
    nom_v.columns = [c.title() for c in nom_v.columns]
    st.dataframe(nom_v, use_container_width=True, hide_index=True)

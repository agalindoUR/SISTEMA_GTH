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
            tbs = st.tabs([s.replace("_"," ").title() for s in SHS])
            
            with tbs[4]: # PESTAÑA CONTRATOS
                st.write("### Historial de Contratos")
                cn = dfs["contratos"][dfs["contratos"]['dni'] == dni_b].reset_index(drop=True)
                
                # Vista con Check de Selección
                vst = cn.drop(columns=['id','modalidad','tipo colaborador'], errors='ignore')
                vst.columns = [c.title() for c in vst.columns]
                vst.insert(0, "Seleccionar", False)
                
                ed_df = st.data_editor(vst, use_container_width=True, hide_index=True, key="editor_v1")
                sel_rows = ed_df[ed_df["Seleccionar"] == True]
                
                # BOTÓN ELIMINAR INDEPENDIENTE (Aparece si hay selección)
                if not sel_rows.empty:
                    idx_sel = sel_rows.index[0]
                    id_db = cn.at[idx_sel, 'id']
                    idx_db = dfs["contratos"][(dfs["contratos"]['dni']==dni_b) & (dfs["contratos"]['id']==id_db)].index[0]
                    
                    if st.button("🚨 Eliminar Contrato Seleccionado"):
                        dfs["contratos"] = dfs["contratos"].drop(idx_db)
                        save(dfs); st.rerun()

                st.divider()
                
                c1, c2 = st.columns([1, 1.5])
                with c1:
                    with st.expander("➕ Agregar Nuevo Contrato"):
                        with st.form("add_f"):
                            f_car, f_sue = st.text_input("Cargo"), st.number_input("Sueldo", 0.0)
                            f_ini, f_fin = st.date_input("Inicio"), st.date_input("Fin")
                            f_est = st.selectbox("Estado", ["ACTIVO", "CESADO"])
                            if st.form_submit_button("Guardar"):
                                nid = dfs["contratos"]['id'].max() + 1 if not dfs["contratos"].empty else 1
                                nr = {"id":nid, "dni":dni_b, "cargo":f_car, "sueldo":f_sue, "f_inicio":f_ini, "f_fin":f_fin, "estado":f_est}
                                dfs["contratos"] = pd.concat([dfs["contratos"], pd.DataFrame([nr])], ignore_index=True)
                                save(dfs); st.rerun()
                
                with c2:
                    if not sel_rows.empty:
                        with st.expander("📝 Editar Información Completa", expanded=True):
                            with st.form("form_edit_full"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    e_ca = st.text_input("Cargo", value=str(cn.at[idx_sel, 'cargo']))
                                    e_su = st.number_input("Sueldo", value=float(cn.at[idx_sel, 'sueldo']))
                                    e_fi = st.date_input("Fecha Inicio", value=pd.to_datetime(cn.at[idx_sel, 'f_inicio']))
                                    e_ff = st.date_input("Fecha Fin", value=pd.to_datetime(cn.at[idx_sel, 'f_fin']))
                                with col2:
                                    e_ti = st.text_input("Tipo", value=str(cn.at[idx_sel].get('tipo', '')))
                                    e_te = st.text_input("Temporalidad", value=str(cn.at[idx_sel].get('temporalidad', '')))
                                    e_li = st.text_input("Link", value=str(cn.at[idx_sel].get('link', '')))
                                    e_tc = st.text_input("Tipo Contrato", value=str(cn.at[idx_sel].get('tipo contrato', '')))
                                
                                e_es = st.selectbox("Estado", ["ACTIVO", "CESADO"], index=0 if cn.at[idx_sel, 'estado']=="ACTIVO" else 1)
                                e_mo = st.selectbox("Motivo", MOTIVOS, index=MOTIVOS.index(cn.at[idx_sel, 'motivo cese']) if cn.at[idx_sel].get('motivo cese') in MOTIVOS else 0) if e_es == "CESADO" else "Vigente"
                                
                                if st.form_submit_button("✅ Actualizar Todos los Campos"):
                                    upd = {'cargo':e_ca, 'sueldo':e_su, 'f_inicio':e_fi, 'f_fin':e_ff, 'tipo':e_ti, 
                                           'temporalidad':e_te, 'link':e_li, 'tipo contrato':e_tc, 'estado':e_es, 'motivo cese':e_mo}
                                    for k, v in upd.items(): dfs["contratos"].at[idx_db, k] = v
                                    save(dfs); st.rerun()
                    else:
                        st.info("Seleccione un contrato arriba 👆 para editar sus datos.")

            for i, s in enumerate(SHS):
                if i != 4:
                    with tbs[i]:
                        df_v = dfs[s.lower()][dfs[s.lower()]['dni'] == dni_b]
                        df_v.columns = [col.title() for col in df_v.columns]
                        st.dataframe(df_v, use_container_width=True, hide_index=True)
        else: st.error("No registrado.")

elif m == "➕ Registro":
    with st.form("r"):
        d_in, n_in = st.text_input("DNI"), st.text_input("Nombres")
        if st.form_submit_button("Registrar"):
            new_p = pd.DataFrame([{"dni":d_in, "apellidos y nombres":n_in.upper()}])
            dfs["personal"] = pd.concat([dfs["personal"], new_p], ignore_index=True)
            save

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
                
                # Preparamos la tabla con selección (Check)
                vst = cn.drop(columns=['id','modalidad','tipo colaborador'], errors='ignore')
                vst.columns = [c.title() for c in vst.columns]
                vst.insert(0, "Seleccionar", False)
                
                # Usamos data_editor para permitir el check
                ed_df = st.data_editor(vst, use_container_width=True, hide_index=True, key="df_ed")
                
                # Identificar cuál fila tiene el check marcado
                sel_rows = ed_df[ed_df["Seleccionar"] == True]
                
                c1, c2 = st.columns(2)
                with c1:
                    with st.expander("➕ Agregar"):
                        with st.form("add_f"):
                            f_car, f_sue = st.text_input("Cargo"), st.number_input("Sueldo", 0.0)
                            f_tip = st.selectbox("Tipo", ["Administrativo", "Docente"])
                            f_est = st.selectbox("Estado", ["VIGENTE", "CESADO"])
                            f_mot = st.selectbox("Motivo", MOTIVOS) if f_est == "CESADO" else "Vigente"
                            if st.form_submit_button("Guardar"):
                                nid = dfs["contratos"]['id'].max() + 1 if not dfs["contratos"].empty else 1
                                nr = {"id":nid, "dni":dni_b, "cargo":f_car, "sueldo":f_sue, "tipo":f_tip, "estado":f_est, "motivo cese":f_mot, "f_inicio": date.today()}
                                dfs["contratos"] = pd.concat([dfs["contratos"], pd.DataFrame([nr])], ignore_index=True)
                                save(dfs); st.rerun()
                
                with c2:
                    if not sel_rows.empty:
                        # Obtenemos la info de la fila marcada
                        idx_sel = sel_rows.index[0]
                        id_db = cn.at[idx_sel, 'id']
                        idx_db = dfs["contratos"][(dfs["contratos"]['dni']==dni_b) & (dfs["contratos"]['id']==id_db)].index[0]
                        
                        with st.expander("📝 Editar / Eliminar Seleccionado", expanded=True):
                            with st.form("form_edit_ok"):
                                e_ca = st.text_input("Cargo", value=str(cn.at[idx_sel, 'cargo']))
                                e_su = st.number_input("Sueldo", value=float(cn.at[idx_sel, 'sueldo']))
                                e_es = st.selectbox("Estado", ["VIGENTE", "CESADO"], index=0 if cn.at[idx_sel, 'estado']=="VIGENTE" else 1)
                                e_mo = st.selectbox("Motivo", MOTIVOS, index=MOTIVOS.index(cn.at[idx_sel, 'motivo cese']) if cn.at[idx_sel, 'motivo cese'] in MOTIVOS else 0) if e_es == "CESADO" else "Vigente"
                                
                                # BOTONES DE ENVÍO (Cada uno debe ser submit_button)
                                col_a, col_b = st.columns(2)
                                if col_a.form_submit_button("✅ Actualizar"):
                                    dfs["contratos"].at[idx_db, 'cargo'] = e_ca
                                    dfs["contratos"].at[idx_db, 'sueldo'] = e_su
                                    dfs["contratos"].at[idx_db, 'estado'] = e_es
                                    dfs["contratos"].at[idx_db, 'motivo cese'] = e_mo
                                    save(dfs); st.rerun()
                                if col_b.form_submit_button("🚨 Eliminar"):
                                    dfs["contratos"] = dfs["contratos"].drop(idx_db)
                                    save(dfs); st.rerun()
                    else:
                        st.info("Seleccione un contrato con el check de la tabla para editar.")

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
            save(dfs); st.success("Ok.")

elif m == "📊 Nómina":
    st.subheader("Nómina Global")
    nv = dfs["contratos"].drop(columns=['id','modalidad'], errors='ignore')
    nv.columns = [c.title() for c in nv.columns]
    st.dataframe(nv, use_container_width=True, hide_index=True)

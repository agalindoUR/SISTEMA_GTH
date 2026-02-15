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
MOTIVOS_CESE = ["Termino de contrato", "Renuncia", "Despido", "Mutuo acuerdo", "Fallecimiento", "Otros"]

def load():
    # Creamos las pestañas si el archivo no existe
    sheets = ["PERSONAL", "FAMILIA", "FORM_ACAD", "EXP_LABORAL", "CONTRATOS", "VACACIONES", "BENEFICIOS", "MERITOS", "LIQUIDACIONES"]
    if not os.path.exists(DB):
        with pd.ExcelWriter(DB) as w:
            for s in sheets: pd.DataFrame().to_excel(w, sheet_name=s, index=False)
        return {s: pd.DataFrame() for s in sheets}
    
    dict_dfs = {}
    with pd.ExcelFile(DB) as x:
        for s in sheets:
            df = pd.read_excel(x, s)
            if "DNI" in df.columns: df["DNI"] = df["DNI"].astype(str).str.strip()
            df.columns = [col.strip().lower() for col in df.columns]
            dict_dfs[s] = df
    return dict_dfs

def save_all(dict_dfs):
    with pd.ExcelWriter(DB) as w:
        for s, df in dict_dfs.items():
            df.to_excel(w, sheet_name=s, index=False)

# --- INTERFAZ ---
st.set_page_config(page_title="GTH Roosevelt - Legajo", layout="wide")
dfs = load()

st.sidebar.title("SISTEMA GTH")
m = st.sidebar.radio("MENÚ PRINCIPAL", ["🔍 Consulta de Legajo", "➕ Registro Nuevo Personal", "📊 Nómina General"])

if m == "🔍 Consulta de Legajo":
    dni_busq = st.text_input("Ingrese DNI del Colaborador:").strip()
    if dni_busq:
        u = dfs["PERSONAL"][dfs["PERSONAL"]['dni'] == dni_busq]
        if not u.empty:
            nom = u.iloc[0]['apellidos y nombres']
            st.header(f"👤 Colaborador: {nom}")
            
            # LAS 9 PESTAÑAS SOLICITADAS
            t1, t2, t3, t4, t5, t6, t7, t8, t9 = st.tabs([
                "Datos Generales", "Familia", "Form. Acad.", "Exp. Laboral", 
                "Contratos", "Vacaciones", "Otros Beneficios", "Mérit. y Demer.", "Liquidaciones"
            ])

            with t1: st.write("### Información Personal"); st.table(u.drop(columns=['id'], errors='ignore'))
            
            with t2: st.info("Información de derechohabientes"); st.dataframe(dfs["FAMILIA"][dfs["FAMILIA"]['dni'] == dni_busq])
            
            with t3: st.info("Grados y títulos"); st.dataframe(dfs["FORM_ACAD"][dfs["FORM_ACAD"]['dni'] == dni_busq])
            
            with t4: st.info("Experiencia previa"); st.dataframe(dfs["EXP_LABORAL"][dfs["EXP_LABORAL"]['dni'] == dni_busq])

            with t5:
                st.write("### Gestión de Contratos")
                cn = dfs["CONTRATOS"][dfs["CONTRATOS"]['dni'] == dni_busq].reset_index(drop=True)
                # Ocultar ID y Tipo Colaborador
                vista_c = cn.drop(columns=['id', 'tipo colaborador'], errors='ignore')
                st.dataframe(vista_c, use_container_width=True, hide_index=True)
                
                c_acc1, c_acc2, c_acc3 = st.columns(3)
                
                with c_acc1: # AGREGAR
                    with st.expander("➕ Nuevo Contrato"):
                        with st.form("add_c"):
                            f_car = st.text_input("Cargo")
                            f_sue = st.number_input("Sueldo", min_value=0.0)
                            f_est = st.selectbox("Estado", ["VIGENTE", "CESADO"])
                            f_mot = "Vigente"
                            if f_est == "CESADO": f_mot = st.selectbox("Motivo de Cese", MOTIVOS_CESE)
                            if st.form_submit_button("Guardar"):
                                nid = dfs["CONTRATOS"]['id'].max() + 1 if not dfs["CONTRATOS"].empty else 1
                                nr = {"id":nid, "dni":dni_busq, "cargo":f_car, "sueldo":f_sue, "estado":f_est, "motivo cese":f_mot, "f_inicio": date.today()}
                                dfs["CONTRATOS"] = pd.concat([dfs["CONTRATOS"], pd.DataFrame([nr])], ignore_index=True)
                                save_all(dfs); st.rerun()

                with c_acc2: # MODIFICAR
                    if not cn.empty:
                        with st.expander("📝 Editar Contrato"):
                            opc = {f"{r['cargo']} ({r['f_inicio']})": r['id'] for _, r in cn.iterrows()}
                            sel_id = opc[st.selectbox("Contrato a editar", list(opc.keys()))]
                            idx = dfs["CONTRATOS"][dfs["CONTRATOS"]['id'] == sel_id].index[0]
                            with st.form("mod_c"):
                                m_sue = st.number_input("Nuevo Sueldo", value=float(dfs["CONTRATOS"].at[idx, 'sueldo']))
                                m_est = st.selectbox("Estado", ["VIGENTE", "CESADO"])
                                m_mot = "Vigente"
                                if m_est == "CESADO": m_mot = st.selectbox("Motivo de Cese", MOTIVOS_CESE)
                                if st.form_submit_button("Actualizar"):
                                    dfs["CONTRATOS"].at[idx, 'sueldo'] = m_sue
                                    dfs["CONTRATOS"].at[idx, 'estado'] = m_est
                                    dfs["CONTRATOS"].at[idx, 'motivo cese'] = m_mot
                                    save_all(dfs); st.rerun()

                with c_acc3: # ELIMINAR UNO POR UNO
                    if not cn.empty:
                        with st.expander("🗑️ Eliminar"):
                            opc_del = {f"{r['cargo']} ({r['f_inicio']})": r['id'] for _, r in cn.iterrows()}
                            sel_del = st.selectbox("Contrato a borrar", list(opc_del.keys()))
                            if st.button("Confirmar Borrado"):
                                dfs["CONTRATOS"] = dfs["CONTRATOS"][dfs["CONTRATOS"]['id'] != opc_del[sel_del]]
                                save_all(dfs); st.rerun()

            with t6: st.info("Control de días de descanso"); st.dataframe(dfs["VACACIONES"][dfs["VACACIONES"]['dni'] == dni_busq])
            with t7: st.info("Seguros, bonos y otros"); st.dataframe(dfs["BENEFICIOS"][dfs["BENEFICIOS"]['dni'] == dni_busq])
            with t8: st.info("Historial disciplinario y premios"); st.dataframe(dfs["MERITOS"][dfs["MERITOS"]['dni'] == dni_busq])
            with t9: st.info("Cálculos de cese"); st.dataframe(dfs["

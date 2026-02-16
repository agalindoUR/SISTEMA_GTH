# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import date
from io import BytesIO
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. CONFIGURACIÓN Y CONSTANTES ---
DB = "DB_SISTEMA_GTH.xlsx"
F_N = "MG. ARTURO JAVIER GALINDO MARTINEZ"
F_C = "JEFE DE GESTIÓN DEL TALENTO HUMANO"
TEXTO_CERT = "LA OFICINA DE GESTIÓN DE TALENTO HUMANO DE LA UNIVERSIDAD PRIVADA DE HUANCAYO “FRANKLIN ROOSEVELT”, CERTIFICA QUE:"
MOTIVOS_CESE = ["Término de contrato", "Renuncia", "Despido", "Mutuo acuerdo", "Fallecimiento", "Otros"]

COLUMNAS = {
    "PERSONAL": ["dni", "apellidos y nombres", "link"],
    "DATOS GENERALES": ["apellidos y nombres", "dni", "dirección", "link de dirección", "estado civil", "fecha de nacimiento", "edad"],
    "DATOS FAMILIARES": ["parentesco", "apellidos y nombres", "dni", "fecha de nacimiento", "edad", "estudios", "telefono"],
    "EXP. LABORAL": ["tipo de experiencia", "lugar", "puesto", "fecha inicio", "fecha de fin", "motivo cese"],
    "FORM. ACADEMICA": ["grado, titulo o especialización", "descripcion", "universidad", "año"],
    "INVESTIGACION": ["año publicación", "autor, coautor o asesor", "tipo de investigación publicada", "nivel de publicación", "lugar de publicación"],
    "CONTRATOS": ["id", "dni", "cargo", "sueldo", "f_inicio", "f_fin", "tipo", "estado", "motivo cese"],
    "VACACIONES": ["periodo", "fecha de inicio", "fecha de fin", "días generados", "días gozados", "saldo", "link"],
    "OTROS BENEFICIOS": ["periodo", "tipo de beneficio", "link"],
    "MERITOS Y DEMERITOS": ["periodo", "merito o demerito", "motivo", "link"],
    "EVALUACION DEL DESEMPEÑO": ["periodo", "merito o demerito", "motivo", "link"],
    "LIQUIDACIONES": ["periodo", "firmo", "link"]
}
# =========================================================
# --- PARTE 2: DISEÑO VISUAL, LOGIN Y FUNCIONES ---
# =========================================================

# 1. Configuración de página y Estilos CSS
st.set_page_config(page_title="GTH Roosevelt", layout="wide")

st.markdown("""
    <style>
    /* Fondo guindo institucional */
    .stApp { 
        background: linear-gradient(135deg, #4a0000 0%, #800000 100%); 
    }
    
    /* Título principal arriba */
    .login-header { 
        color: white; 
        text-align: center; 
        font-size: 42px; 
        font-weight: bold; 
        text-shadow: 2px 2px 4px #000; 
        margin-top: 40px;
        margin-bottom: 40px;
    }
    
    /* Mensaje de bienvenida amarillo (ahora para usar debajo) */
    .login-welcome { 
        color: #FFD700; 
        text-align: center; 
        font-size: 20px; 
        margin-top: 20px;
        margin-bottom: 20px;
        font-style: italic;
    }
    
    /* Texto de etiquetas */
    label { 
        color: white !important; 
        font-size: 22px !important; 
        font-weight: bold !important; 
    }
    
    /* Botón INGRESAR grande y llamativo */
    div.stButton > button { 
        background-color: #FFD700 !important; 
        color: #4a0000 !important; 
        font-size: 24px !important; 
        font-weight: bold !important; 
        width: 100%; 
        height: 55px;
        border-radius: 12px; 
        border: 2px solid #b8860b;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        transform: scale(1.02);
        background-color: #fceabb !important;
    }
    </style>
""", unsafe_allow_html=True)

# 2. Funciones de Gestión de Datos (Excel)
def load_data():
    if not os.path.exists(DB):
        with pd.ExcelWriter(DB) as w:
            for h, cols in COLUMNAS.items(): 
                pd.DataFrame(columns=cols).to_excel(w, sheet_name=h, index=False)
    dfs = {}
    with pd.ExcelFile(DB) as x:
        for h in COLUMNAS.keys():
            df = pd.read_excel(x, h) if h in x.sheet_names else pd.DataFrame(columns=COLUMNAS[h])
            df.columns = [str(c).strip().lower() for c in df.columns]
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

# 3. Lógica de Control de Sesión y Pantalla de Login
if "rol" not in st.session_state:
    st.session_state.rol = None

else:
    dfs = load_data()
    es_lector = st.session_state.rol == "Lector"
    
    m = st.sidebar.radio("MENÚ", ["🔍 Consulta", "➕ Registro", "📊 Nómina General"])
    if st.sidebar.button("Cerrar Sesión"): st.session_state.rol = None; st.rerun()

    if m == "🔍 Consulta":
        dni_b = st.text_input("DNI del colaborador:").strip()
        if dni_b:
            pers = dfs["PERSONAL"][dfs["PERSONAL"]["dni"] == dni_b]
            if not pers.empty:
                nom_c = pers.iloc[0]["apellidos y nombres"]
                st.header(f"👤 {nom_c}")
                st.subheader("📁 Gestión de Información")
                t_noms = ["Datos Generales", "Exp. Laboral", "Form. Académica", "Investigación", "Datos Familiares", "Contratos", "Vacaciones", "Otros Beneficios", "Méritos/Demer.", "Evaluación", "Liquidaciones"]
                h_keys = ["DATOS GENERALES", "EXP. LABORAL", "FORM. ACADEMICA", "INVESTIGACION", "DATOS FAMILIARES", "CONTRATOS", "VACACIONES", "OTROS BENEFICIOS", "MERITOS Y DEMERITOS", "EVALUACION DEL DESEMPEÑO", "LIQUIDACIONES"]
                tabs = st.tabs(t_noms)

                for i, tab in enumerate(tabs):
                    h_name = h_keys[i]
                    with tab:
                        c_df = dfs[h_name][dfs[h_name]["dni"] == dni_b] if "dni" in dfs[h_name].columns else pd.DataFrame(columns=COLUMNAS[h_name])
                        
                        if h_name == "CONTRATOS":
                            if not c_df.empty:
                                st.download_button("📄 Certificado Word", gen_word(nom_c, dni_b, c_df), f"Cert_{dni_b}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                            
                            vst = c_df.copy()
                            vst.insert(0, "Sel", False)
                            ed = st.data_editor(vst, hide_index=True, use_container_width=True, key=f"ed_{h_name}")
                            sel = ed[ed["Sel"] == True]

                            if not es_lector:
                                c1, c2 = st.columns(2)
                                with c1:
                                    with st.expander("➕ Nuevo Contrato"):
                                        with st.form("f_add"):
                                            car = st.text_input("Cargo"); sue = st.number_input("Sueldo", 0.0)
                                            ini = st.date_input("Inicio"); fin = st.date_input("Fin")
                                            est_a = "ACTIVO" if fin >= date.today() else "CESADO"
                                            mot_a = st.selectbox("Motivo Cese", ["Vigente"] + MOTIVOS_CESE) if est_a == "CESADO" else "Vigente"
                                            if st.form_submit_button("Guardar"):
                                                nid = dfs[h_name]["id"].max() + 1 if not dfs[h_name].empty else 1
                                                new = {"id":nid, "dni":dni_b, "cargo":car, "sueldo":sue, "f_inicio":ini, "f_fin":fin, "estado":est_a, "motivo cese":mot_a}
                                                dfs[h_name] = pd.concat([dfs[h_name], pd.DataFrame([new])], ignore_index=True)
                                                save_data(dfs); st.rerun()
                                with c2:
                                    with st.expander("📝 Editar/Eliminar Seleccionado"):
                                        if not sel.empty:
                                            with st.form("f_edit"):
                                                n_car = st.text_input("Cargo", value=sel.iloc[0]["cargo"])
                                                n_fin = st.date_input("Fin", value=pd.to_datetime(sel.iloc[0]["f_fin"]))
                                                est_e = "ACTIVO" if n_fin >= date.today() else "CESADO"
                                                mot_e = st.selectbox("Motivo Cese", MOTIVOS_CESE) if est_e == "CESADO" else "Vigente"
                                                if st.form_submit_button("Actualizar"):
                                                    idx = sel.index[0]
                                                    dfs[h_name].at[idx, "cargo"] = n_car
                                                    dfs[h_name].at[idx, "f_fin"] = n_fin
                                                    dfs[h_name].at[idx, "estado"] = est_e
                                                    dfs[h_name].at[idx, "motivo cese"] = mot_e
                                                    save_data(dfs); st.rerun()
                                            if st.button("🚨 Eliminar Fila"):
                                                dfs[h_name] = dfs[h_name].drop(sel.index)
                                                save_data(dfs); st.rerun()
                                        else: st.info("Selecciona una fila arriba")
                        else:
                            st.dataframe(c_df, use_container_width=True, hide_index=True)
                            if not es_lector:
                                with st.expander(f"➕ Registrar en {h_name}"):
                                    with st.form(f"f_{h_name}"):
                                        new_row = {"dni": dni_b}
                                        cols_f = [c for c in COLUMNAS[h_name] if c not in ["dni", "apellidos y nombres", "edad", "id"]]
                                        for col in cols_f: new_row[col] = st.text_input(col.title())
                                        if st.form_submit_button("Confirmar"):
                                            dfs[h_name] = pd.concat([dfs[h_name], pd.DataFrame([new_row])], ignore_index=True)
                                            save_data(dfs); st.rerun()
            else:
                st.error("Trabajador no encontrado.")

    elif m == "➕ Registro":
        if es_lector: st.error("No autorizado")
        else:
            with st.form("reg_p"):
                st.write("### Alta de Nuevo Trabajador")
                d = st.text_input("DNI"); n = st.text_input("Nombres").upper(); l = st.text_input("Link File")
                if st.form_submit_button("Registrar"):
                    if d and n:
                        dfs["PERSONAL"] = pd.concat([dfs["PERSONAL"], pd.DataFrame([{"dni":d, "apellidos y nombres":n, "link":l}])], ignore_index=True)
                        save_data(dfs); st.success("Registrado correctamente")

    elif m == "📊 Nómina General":
        st.header("Base de Datos General")
        st.dataframe(dfs["PERSONAL"], use_container_width=True, hide_index=True)





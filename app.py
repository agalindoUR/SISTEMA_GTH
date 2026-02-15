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
# Nombres de hojas exactos
SHS = ["PERSONAL", "FAMILIA", "FORM_ACAD", "EXP_LABORAL", "CONTRATOS", "VACACIONES", "BENEFICIOS", "MERITOS", "LIQUIDACIONES"]

# --- FUNCIONES ---
def load():
    if not os.path.exists(DB):
        with pd.ExcelWriter(DB) as w:
            for s in SHS: pd.DataFrame(columns=["dni", "nombres"]).to_excel(w, sheet_name=s, index=False)
    
    dfs = {}
    with pd.ExcelFile(DB) as x:
        for s in SHS:
            if s in x.sheet_names:
                df = pd.read_excel(x, s)
                # Estandarización agresiva de columnas: todo a minúsculas y sin espacios
                df.columns = [str(c).strip().lower() for c in df.columns]
                
                # Limpieza específica de DNI para evitar errores de búsqueda
                if "dni" in df.columns:
                    df["dni"] = df["dni"].astype(str).str.strip().replace(r'\.0$', '', regex=True)
                
                dfs[s.lower()] = df
            else:
                dfs[s.lower()] = pd.DataFrame(columns=["dni"])
    return dfs

def save(dfs):
    with pd.ExcelWriter(DB) as w:
        for s in SHS:
            df_save = dfs[s.lower()].copy()
            # Guardamos con primera letra mayúscula para que se vea bien en Excel
            df_save.columns = [c.title() for c in df_save.columns]
            df_save.to_excel(w, sheet_name=s, index=False)

def gen_doc(nom, dni, df):
    doc = Document()
    doc.add_heading('CERTIFICADO DE TRABAJO', 0)
    doc.add_paragraph(f"El TRABAJADOR {nom}, DNI {dni} laboró según detalle:")
    tb = doc.add_table(rows=1, cols=3); tb.style = 'Table Grid'
    hdr = tb.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text = "Cargo", "Fecha Inicio", "Fecha Fin"
    for _, f in df.iterrows():
        r = tb.add_row().cells
        r[0].text = str(f.get('cargo',''))
        r[1].text = str(f.get('f_inicio',''))[:10]
        r[2].text = str(f.get('f_fin',''))[:10]
    doc.add_paragraph(f"\nHuancayo, {date.today()}\n\n{F_N}\n{F_C}")
    buf = BytesIO(); doc.save(buf); buf.seek(0); return buf

# --- INTERFAZ ---
st.set_page_config(page_title="GTH Roosevelt", layout="wide")
dfs = load()

st.sidebar.title("SISTEMA GTH")
m = st.sidebar.radio("MENÚ", ["🔍 Consulta", "➕ Registro", "📊 Nómina"])

if m == "🔍 Consulta":
    st.subheader("Búsqueda de Personal")
    dni_b = st.text_input("Ingrese DNI:", placeholder="Ej: 43076279").strip()
    
    if dni_b:
        # Búsqueda robusta
        p_df = dfs["personal"]
        # Intentamos encontrar la columna de nombres (puede ser 'nombres', 'apellidos y nombres', etc.)
        col_nom = next((c for c in p_df.columns if "nombre" in c), None)
        
        user_match = p_df[p_df['dni'] == dni_b]
        
        if not user_match.empty and col_nom:
            nom = user_match.iloc[0][col_nom]
            st.success(f"Trabajador: {nom}")
            
            # PESTAÑAS
            mis_tabs = st.tabs([s.replace("_"," ").title() for s in SHS])
            
            # --- PESTAÑA CONTRATOS (Índice 4) ---
            with mis_tabs[4]:
                st.write("### Gestión de Contratos")
                
                # Filtramos contratos del usuario
                cn = dfs["contratos"][dfs["contratos"]['dni'] == dni_b].reset_index(drop=True)
                
                # Preparar tabla para el Editor
                vst = cn.copy()
                cols_ocultas = ['id', 'modalidad']
                vst = vst.drop(columns=[c for c in cols_ocultas if c in vst.columns], errors='ignore')
                
                # Insertar columna Checkbox al inicio
                if "seleccionar" not in vst.columns:
                    vst.insert(0, "seleccionar", False)
                
                # MOSTRAR TABLA EDITABLE (CHECKBOX)
                ed_df = st.data_editor(
                    vst, 
                    use_container_width=True, 
                    hide_index=True, 
                    key="editor_contratos",
                    column_config={"seleccionar": st.column_config.CheckboxColumn("Seleccionar", help="Marcar para editar/borrar")}
                )
                
                # Lógica de Selección
                sel_rows = ed_df[ed_df["seleccionar"] == True]
                
                # --- BOTONERA DE ACCIONES (SI HAY SELECCIÓN) ---
                if not sel_rows.empty:
                    idx_sel = sel_rows.index[0] # Índice en la tabla visual
                    id_unico = cn.at[idx_sel, 'id'] # ID real en la base de datos
                    # Buscamos el índice real en el dataframe global para editar
                    idx_global = dfs["contratos"][dfs["contratos"]['id'] == id_unico].index[0]
                    
                    st.divider()
                    st.markdown(f"#### 🛠️ Gestionando contrato: **{cn.at[idx_sel, 'cargo']}**")
                    
                    c_btn1, c_btn2 = st.columns(2)
                    with c_btn1:
                        # Botón Word
                        st.download_button(
                            "📄 Descargar Certificado Word", 
                            data=gen_doc(nom, dni_b, cn), 
                            file_name=f"Certificado_{dni_b}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                    with c_btn2:
                         # Botón Eliminar fuera del form para seguridad
                        if st.button("🚨 Eliminar este Contrato", type="primary"):
                            dfs["contratos"] = dfs["contratos"].drop(idx_global)
                            save(dfs); st.rerun()

                    # --- FORMULARIO DE EDICIÓN ---
                    with st.form("form_editar"):
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            e_car = st.text_input("Cargo", value=str(cn.at[idx_sel, 'cargo']))
                            e_sue = st.number_input("Sueldo", value=float(cn.at[idx_sel, 'sueldo']))
                            val_ini = pd.to_datetime(cn.at[idx_sel, 'f_inicio']) if pd.notnull(cn.at[idx_sel, 'f_inicio']) else date.today()
                            e_ini = st.date_input("Fecha Inicio", value=val_ini)
                        with c2:
                            e_tip = st.text_input("Tipo", value=str(cn.at[idx_sel].get('tipo', '')))
                            e_tem = st.text_input("Temporalidad", value=str(cn.at[idx_sel].get('temporalidad', '')))
                            val_fin = pd.to_datetime(cn.at[idx_sel, 'f_fin']) if pd.notnull(cn.at[idx_sel, 'f_fin']) else date.today()
                            e_fin = st.date_input("Fecha Fin", value=val_fin)
                        with c3:
                            e_lnk = st.text_input("Link", value=str(cn.at[idx_sel].get('link', '')))
                            e_tco = st.text_input("Tipo Contrato", value=str(cn.at[idx_sel].get('tipo contrato', '')))
                            e_est = st.selectbox("Estado", ["ACTIVO", "CESADO"], index=0 if cn.at[idx_sel, 'estado']=="ACTIVO" else 1)
                            
                        # Motivo Cese (solo si cesado)
                        e_mot = st.selectbox("Motivo Cese", MOTIVOS) if e_est == "CESADO" else "Vigente"

                        if st.form_submit_button("✅ Guardar Cambios"):
                            dfs["contratos"].at[idx_global, 'cargo'] = e_car
                            dfs["contratos"].at[idx_global, 'sueldo'] = e_sue
                            dfs["contratos"].at[idx_global, 'f_inicio'] = e_ini
                            dfs["contratos"].at[idx_global, 'f_fin'] = e_fin
                            dfs["contratos"].at[idx_global, 'tipo'] = e_tip
                            dfs["contratos"].at[idx_global, 'temporalidad'] = e_tem
                            dfs["contratos"].at[idx_global, 'link'] = e_lnk
                            dfs["contratos"].at[idx_global, 'tipo contrato'] = e_tco
                            dfs["contratos"].at[idx_global, 'estado'] = e_est

# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import date
from io import BytesIO
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- CONFIGURACIÓN ---
DB = "DB_SISTEMA_GTH.xlsx"
F_N = "MG. ARTURO J. GALINDO MARTINEZ"
F_C = "JEFE DE GESTIÓN DE TALENTO HUMANO"
TEXTO_CERT = "LA OFICINA DE GESTIÓN DE TALENTO HUMANO DE LA UNIVERSIDAD PRIVADA DE HUANCAYO “FRANKLIN ROOSEVELT”, CERTIFICA QUE:"
MOTIVOS = ["Termino de contrato", "Renuncia", "Despido", "Mutuo acuerdo", "Fallecimiento", "Otros"]
SHS = ["PERSONAL", "FAMILIA", "FORM_ACAD", "EXP_LABORAL", "CONTRATOS", "VACACIONES", "BENEFICIOS", "MERITOS", "LIQUIDACIONES"]

# --- FUNCIONES ---
def normalize_cols(df):
    # Limpia nombres de columnas: espacios y mayúsculas fuera
    df.columns = [str(c).strip().lower() for c in df.columns]
    # Busca columnas clave y las renombra para estandarizar
    for c in df.columns:
        if "dni" in c: df.rename(columns={c: "dni"}, inplace=True)
        if "nombre" in c: df.rename(columns={c: "nombres"}, inplace=True)
        if "apellido" in c: df.rename(columns={c: "nombres"}, inplace=True) # Por si dice "Apellidos y Nombres"
    return df

def load():
    if not os.path.exists(DB):
        with pd.ExcelWriter(DB) as w:
            for s in SHS: pd.DataFrame(columns=["dni", "nombres"]).to_excel(w, sheet_name=s, index=False)
    
    dfs = {}
    with pd.ExcelFile(DB) as x:
        for s in SHS:
            if s in x.sheet_names:
                df = pd.read_excel(x, s)
                df = normalize_cols(df)
                # Limpieza segura de DNI (quita .0 y espacios)
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
            df_save.columns = [c.upper() for c in df_save.columns] # Guardar en mayúsculas para Excel
            df_save.to_excel(w, sheet_name=s, index=False)

def gen_doc(nom, dni, df_contratos):
    doc = Document()
    
    # Título
    t = doc.add_paragraph("CERTIFICADO DE TRABAJO")
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.runs[0].bold = True
    t.runs[0].font.size = Pt(16)
    
    # Cuerpo texto
    p = doc.add_paragraph(TEXTO_CERT)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    p2 = doc.add_paragraph(f"\nEl TRABAJADOR {nom}, identificado con DNI N° {dni}, laboró en nuestra Institución bajo el siguiente detalle:")
    p2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    # Tabla
    table = doc.add_table(rows=1, cols=3)
    table.style = 'Table Grid'
    hdr = table.rows[0].cells
    hdr[0].text = "CARGO"
    hdr[1].text = "FECHA INICIO"
    hdr[2].text = "FECHA FIN"
    
    # Llenar con TODOS los contratos
    for _, row in df_contratos.iterrows():
        cells = table.add_row().cells
        cells[0].text = str(row.get('cargo', ''))
        # Formato fecha corto
        fi = pd.to_datetime(row.get('f_inicio')).strftime('%d/%m/%Y') if pd.notnull(row.get('f_inicio')) else ""
        ff = pd.to_datetime(row.get('f_fin')).strftime('%d/%m/%Y') if pd.notnull(row.get('f_fin')) else ""
        cells[1].text = fi
        cells[2].text = ff

    # Fecha y Firma
    meses = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
    hoy = date.today()
    fecha_txt = f"\n\nHuancayo, {hoy.day} de {meses[hoy.month-1]} del {hoy.year}"
    
    p3 = doc.add_paragraph(fecha_txt)
    p3.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    firma = doc.add_paragraph(f"\n\n\n__________________________\n{F_N}\n{F_C}")
    firma.alignment = WD_ALIGN_PARAGRAPH.CENTER
    firma.runs[0].bold = True

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- INTERFAZ ---
st.set_page_config(page_title="GTH Roosevelt", layout="wide")
dfs = load()

st.sidebar.title("SISTEMA GTH")
m = st.sidebar.radio("MENÚ", ["🔍 Consulta", "➕ Registro", "📊 Nómina"])

if m == "🔍 Consulta":
    st.title("Consulta de Legajo")
    dni_b = st.text_input("Ingrese DNI:", placeholder="Ej: 43076279").strip()
    
    if dni_b:
        p_df = dfs["personal"]
        # Buscar el usuario exacto
        user = p_df[p_df['dni'] == dni_b]
        
        if not user.empty:
            nom = user.iloc[0]['nombres']
            st.header(f"👤 {nom}")
            
            tabs = st.tabs([s.replace("_"," ").title() for s in SHS])
            
            # --- PESTAÑA CONTRATOS (Index 4) ---
            with tabs[4]:
                st.subheader("Historial de Contratos")
                
                # Datos del usuario actual
                cn = dfs["contratos"][dfs["contratos"]['dni'] == dni_b].reset_index(drop=True)
                
                # Botón WORD (Arriba, siempre visible si hay datos)
                if not cn.empty:
                    st.download_button(
                        "📄 Descargar Certificado (Word)",
                        data=gen_doc(nom, dni_b, cn),
                        file_name=f"Certificado_{dni_b}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                
                # Tabla interactiva
                vst = cn.copy()
                # Ocultar columnas internas para la vista
                if 'id' in vst.columns: vst = vst.drop(columns=['id'])
                if 'modalidad' in vst.columns: vst = vst.drop(columns=['modalidad'])
                
                # Columna checkbox para seleccionar
                vst.insert(0, "Sel", False)
                
                edited_df = st.data_editor(
                    vst,
                    use_container_width=True,
                    hide_index=True,
                    column_config={"Sel": st.column_config.CheckboxColumn(required=True)}
                )
                
                # Lógica selección
                sel_rows = edited_df[edited_df["Sel"] == True]
                
                col_a, col_b = st.columns([1, 1])
                
                # SECCIÓN 1: AGREGAR (Siempre visible)
                with col_a:
                    with st.expander("➕ Crear Nuevo Contrato", expanded=True):
                        with st.form("new_c"):
                            n_car = st.text_input("Cargo")
                            n_sue = st.number_input("Sueldo", 0.0)
                            n_ini = st.date_input("Fecha Inicio")
                            n_fin = st.date_input("Fecha Fin")
                            n_tip = st.text_input("Tipo (Docente/Admin)")
                            n_tem = st.text_input("Temporalidad (Plazo fijo...)")
                            n_lnk = st.text_input("Link Contrato")
                            n_tco = st.text_input("Tipo Contrato")
                            n_est = st.selectbox("Estado", ["ACTIVO", "CESADO"])
                            
                            if st.form_submit_button("Guardar Nuevo"):
                                new_id = dfs["contratos"]['id'].max() + 1 if not dfs["contratos"].empty and 'id' in dfs["contratos"] else 1
                                nr = {
                                    "id": new_id, "dni": dni_b, "cargo": n_car, "sueldo": n_sue,
                                    "f_inicio": n_ini, "f_fin": n_fin, "tipo": n_tip, "temporalidad": n_tem,
                                    "link": n_lnk, "tipo contrato": n_tco, "estado": n_est, "motivo cese": "Vigente"
                                }
                                dfs["contratos"] = pd.concat([dfs["contratos"], pd.DataFrame([nr])], ignore_index=True)
                                save(dfs); st.rerun()

                # SECCIÓN 2: EDITAR (Solo si hay check)
                with col_b:
                    if not sel_rows.empty:
                        idx_vis = sel_rows.index[0]
                        id_real = cn.at[idx_vis, 'id'] # ID unico
                        # Buscar indice en dataframe global
                        idx_gl = dfs["contratos"][dfs["contratos"]['id'] == id_real].index[0]
                        
                        with st.expander("📝 Editar / Eliminar Seleccionado", expanded=True):
                            st.info(f"Editando: {cn.at[idx_vis, 'cargo']}")
                            with st.form("edit_c"):
                                e_car = st.text_input("Cargo", value=str(cn.at[idx_vis, 'cargo']))
                                e_sue = st.number_input("Sueldo", value=float(cn.at[idx_vis, 'sueldo']))
                                
                                # Fechas seguras
                                fi_val = pd.to_datetime(cn.at[idx_vis, 'f_inicio']) if pd.notnull(cn.at[idx_vis, 'f_inicio']) else date.today()
                                ff_val = pd.to_datetime(cn.at[idx_vis, 'f_fin']) if pd.notnull(cn.at[idx_vis, 'f_fin']) else date.today()
                                e_ini = st.date_input("Inicio", value=fi_val)
                                e_fin = st.date_input("Fin", value=ff_val)
                                
                                e_tip = st.text_input("Tipo", value=str(cn.at[idx_vis].get('tipo','')))
                                e_tem = st.text_input("Temporalidad", value=str(cn.at[idx_vis].get('temporalidad','')))
                                e_lnk = st.text_input("Link", value=str(cn.at[idx_vis].get('link','')))
                                e_tco = st.text_input("Tipo Contrato", value=str(cn.at[idx_vis].get('tipo contrato','')))
                                e_est = st.selectbox("Estado", ["ACTIVO", "CESADO"], index=0 if cn.at[idx_vis, 'estado']=="ACTIVO" else 1)
                                e_mot = st.selectbox("Motivo Cese", MOTIVOS) if e_est == "CESADO" else "Vigente"
                                
                                c_ok, c_del = st.columns(2)
                                if c_ok.form_submit_button("✅ Actualizar"):
                                    dfs["contratos"].at[idx_gl, 'cargo'] = e_car
                                    dfs["contratos"].at[idx_gl, 'sueldo'] = e_sue
                                    dfs["contratos"].at[idx_gl, 'f_inicio'] = e_ini
                                    dfs["contratos"].at[idx_gl, 'f_fin'] = e_fin
                                    dfs["contratos"].at[idx_gl, 'tipo'] = e_tip
                                    dfs["contratos"].at[idx_gl, 'temporalidad'] = e_tem
                                    dfs["contratos"].at[idx_gl, 'link'] = e_lnk
                                    dfs["contratos"].at[idx_gl, 'tipo contrato'] = e_tco
                                    dfs["contratos"].at[idx_gl, 'estado'] = e_est
                                    dfs["contratos"].at[idx_gl, 'motivo cese'] = e_mot
                                    save(dfs); st.rerun()
                                
                                if c_del.form_submit_button("🚨 Eliminar"):
                                    dfs["contratos"] = dfs["contratos"].drop(idx_gl)
                                    save(dfs); st.rerun()
            
            # Rest

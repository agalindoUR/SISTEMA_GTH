# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import date
from io import BytesIO
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. CONFIGURACIÓN Y CONSTANTES [cite: 1] ---
DB = "DB_SISTEMA_GTH.xlsx"
F_N = "MG. ARTURO JAVIER GALINDO MARTINEZ" # [cite: 61]
F_C = "JEFE DE GESTIÓN DEL TALENTO HUMANO" # [cite: 61]
# Texto exacto solicitado en el documento [cite: 58]
TEXTO_CERT = "LA OFICINA DE GESTIÓN DE TALENTO HUMANO DE LA UNIVERSIDAD PRIVADA DE HUANCAYO “FRANKLIN ROOSEVELT”, CERTIFICA QUE:"
MOTIVOS = ["Termino de contrato", "Renuncia", "Despido", "Mutuo acuerdo", "Fallecimiento", "Otros"] # [cite: 51]
# Hojas exactas según documento [cite: 42, 48]
SHS = ["PERSONAL", "DATOS GENERALES", "DATOS FAMILIARES", "EXP. LABORAL", "FORM. ACADEMICA", 
       "INVESTIGACION", "CONTRATOS", "VACACIONES", "OTROS BENEFICIOS", "MERITOS Y DEMERITOS", 
       "EVALUACION DEL DESEMPEÑO", "LIQUIDACIONES"]

# --- 2. FUNCIONES DE CARGA Y GUARDADO ---
def normalize_cols(df):
    """Estandariza columnas para evitar errores de búsqueda"""
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df

def load():
    """Carga la base de datos y maneja errores de columnas o dtypes"""
    if not os.path.exists(DB):
        with pd.ExcelWriter(DB) as w:
            for s in SHS: pd.DataFrame(columns=["dni", "apellidos y nombres"]).to_excel(w, sheet_name=s, index=False)
    
    dfs = {}
    with pd.ExcelFile(DB) as x:
        for s in SHS:
            if s in x.sheet_names:
                # Forzar lectura de DNI como texto para evitar '43076279.0'
                try:
                    df = pd.read_excel(x, s, dtype={'DNI': str, 'dni': str})
                except:
                    df = pd.read_excel(x, s)
                
                df = normalize_cols(df)
                
                # Limpieza adicional de DNI
                if "dni" in df.columns:
                    df["dni"] = df["dni"].astype(str).str.strip().replace(r'\.0$', '', regex=True)
                
                dfs[s] = df
            else:
                dfs[s] = pd.DataFrame(columns=["dni"])
    return dfs

def save(dfs):
    """Guarda respetando los nombres de hojas originales"""
    with pd.ExcelWriter(DB) as w:
        for s in SHS:
            df_save = dfs[s].copy()
            # Convertimos encabezados a Título para estética en Excel
            df_save.columns = [c.upper() for c in df_save.columns]
            df_save.to_excel(w, sheet_name=s, index=False)

# --- 3. GENERADOR DE WORD EXACTO [cite: 56-63] ---
def gen_doc(nom, dni, df_contratos):
    doc = Document()
    
    # TITULO: CERTIFICADO DE TRABAJO (Negrita, ARIAL, Tamaño: 24) [cite: 57]
    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_tit = p_tit.add_run("CERTIFICADO DE TRABAJO")
    run_tit.bold = True
    run_tit.font.name = 'Arial'
    run_tit.font.size = Pt(24)
    
    doc.add_paragraph("\n") # Espacio
    
    # Primer párrafo [cite: 58]
    p1 = doc.add_paragraph(TEXTO_CERT)
    p1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    doc.add_paragraph("\n") # Espacio
    
    # Segundo párrafo [cite: 59]
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p2.add_run("El TRABAJADOR ")
    p2.add_run(f"{nom}").bold = True
    p2.add_run(f", identificado con DNI N° {dni}, laboró en nuestra Institución bajo el siguiente detalle:")
    
    doc.add_paragraph("\n")
    
    # Cuadro: Tabla de contratos [cite: 60]
    table = doc.add_table(rows=1, cols=3)
    table.style = 'Table Grid'
    hdr = table.rows[0].cells
    hdr[0].text = "CARGO"
    hdr[1].text = "FECHA INICIO"
    hdr[2].text = "FECHA FIN"
    
    # Llenar tabla con historial
    for _, row in df_contratos.iterrows():
        cells = table.add_row().cells
        cells[0].text = str(row.get('cargo', ''))
        # Formato fecha dd/mm/yyyy
        fi = pd.to_datetime(row.get('f_inicio')).strftime('%d/%m/%Y') if pd.notnull(row.get('f_inicio')) else ""
        ff = pd.to_datetime(row.get('f_fin')).strftime('%d/%m/%Y') if pd.notnull(row.get('f_fin')) else ""
        cells[1].text = fi
        cells[2].text = ff

    doc.add_paragraph("\n\n")
    
    # Fecha (Huancayo...)
    meses = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
    hoy = date.today()
    fecha_txt = f"Huancayo, {hoy.day} de {meses[hoy.month-1]} del {hoy.year}"
    p_fecha = doc.add_paragraph(fecha_txt)
    p_fecha.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    doc.add_paragraph("\n\n\n")
    
    # Firma [cite: 61]
    p_firma = doc.add_paragraph()
    p_firma.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_f1 = p_firma.add_run("__________________________\n")
    run_f2 = p_firma.add_run(f"{F_N}\n")
    run_f2.bold = True
    run_f3 = p_firma.add_run(F_C)
    run_f3.bold = True

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- 4. INTERFAZ GRÁFICA ---
st.set_page_config(page_title="GTH Roosevelt", layout="wide")
dfs = load()

# -- LOGIN SIMULADO (Por ahora libre para Admin) [cite: 30] --
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c8/Logo_Universidad_Privada_de_Huancayo_Franklin_Roosevelt.png/320px-Logo_Universidad_Privada_de_Huancayo_Franklin_Roosevelt.png", width=150) # Logo placeholder
st.sidebar.title("SISTEMA GTH")
m = st.sidebar.radio("MENÚ", ["🔍 Consulta", "➕ Registro", "📊 Nómina"]) # [cite: 35]

# === MÓDULO DE CONSULTA ===
if m == "🔍 Consulta":
    st.title("Bienvenido al sistema de gestión GTH") # [cite: 33]
    st.subheader("Consulta de Colaborador")
    
    dni_b = st.text_input("Ingrese DNI del colaborador:", placeholder="Ej: 43076279").strip() # [cite: 36]
    
    if dni_b:
        # Lógica de búsqueda flexible
        df_p = dfs["PERSONAL"]
        # Buscar columna que parezca 'nombre'
        col_nom = next((c for c in df_p.columns if "nombre" in c), None)
        col_dni = next((c for c in df_p.columns if "dni" in c), None)
        
        if col_dni and not df_p[df_p[col_dni] == dni_b].empty:
            fila_usuario = df_p[df_p[col_dni] == dni_b].iloc[0]
            nom_usuario = fila_usuario[col_nom] if col_nom else "Colaborador"
            
            st.success(f"✅ Colaborador encontrado: **{nom_usuario}**")
            
            # PESTAÑAS SEGÚN DOCUMENTO [cite: 41]
            tabs = st.tabs([
                "Datos Generales", "Exp. Laboral", "Form. Académica", "Investigación", "Datos Familiares", # Presentados por trabajador
                "Contratos", "Vacaciones", "Otros Beneficios", "Méritos", "Liquidaciones" # Documentos internos
            ])
            
            # --- PESTAÑA CONTRATOS (Índice 5) ---
            with tabs[5]:
                st.markdown("### 📄 Gestión de Contratos")
                
                # Cargar contratos del DNI
                df_c = dfs["CONTRATOS"]
                mis_contratos = df_c[df_c['dni'] == dni_b].reset_index(drop=True)
                
                # 1. VISUALIZACIÓN TABLA SUPERIOR [cite: 50]
                # Preparamos vista con Checkbox
                vst = mis_contratos.copy()
                cols_ocultas = ['id', 'modalidad'] # Ocultamos ID interno
                vst = vst.drop(columns=[c for c in cols_ocultas if c in vst.columns], errors='ignore')
                
                if not vst.empty:
                    # Insertar columna para check
                    vst.insert(0, "Seleccionar", False)
                    # Editor de datos para seleccionar
                    ed_df = st.data_editor(
                        vst,
                        column_config={"Seleccionar": st.column_config.CheckboxColumn(required=True)},
                        hide_index=True,
                        use_container_width=True,
                        key="tabla_contratos"
                    )
                    sel_rows = ed_df[ed_df["Seleccionar"] == True]
                else:
                    st.info("No hay contratos registrados.")
                    sel_rows = pd.DataFrame()

                st.divider()

                # 2. ACCIONES (BOTONES)
                col_izq, col_der = st.columns([1, 1])
                
                # -- COLUMNA IZQUIERDA: AGREGAR (Siempre visible) [cite: 51] --
                with col_izq:
                    with st.expander("➕ Agregar Nuevo Contrato", expanded=True):
                        with st.form("form_add"):
                            c1, c2 = st.columns(2)
                            n_car = c1.text_input("Cargo")
                            n_sue = c2.number_input("Sueldo", 0.0)
                            n_ini = c1.date_input("Fecha Inicio")
                            n_fin = c2.date_input("Fecha Fin")
                            n_tip = c1.selectbox("Tipo", ["Docente", "Administrativo"])
                            n_tco = c2.text_input("Tipo Contrato (Ej: Plazo Fijo)")
                            n_tem = c1.text_input("Temporalidad")
                            n_lnk = c2.text_input("Link Contrato")
                            # Lógica estado automático [cite: 51]
                            n_est = st.selectbox("Estado", ["ACTIVO", "CESADO"])
                            n_mot = "Vigente"
                            if n_est == "CESADO":
                                n_mot = st.selectbox("Motivo Cese", MOTIVOS)

                            if st.form_submit_button("💾 Guardar Contrato"):
                                new_id = df_c['id'].max() + 1 if not df_c.empty and 'id' in df_c else 1
                                nuevo_reg = {
                                    "id": new_id, "dni": dni_b, "cargo": n_car, "sueldo": n_sue,
                                    "f_inicio": n_ini, "f_fin": n_fin, "tipo": n_tip, "tipo contrato": n_tco,
                                    "temporalidad": n_tem, "link": n_lnk, "estado": n_est, "motivo cese": n_mot
                                }
                                dfs["CONTRATOS"] = pd.concat([dfs["CONTRATOS"], pd.DataFrame([nuevo_reg])], ignore_index=True)
                                save(dfs); st.rerun()

                # -- COLUMNA DERECHA: ACCIONES SOBRE SELECCIÓN --
                with col_der:
                    # Botón Generar Word (Visible si hay contratos) [cite: 56]
                    if not mis_contratos.empty:
                        st.download_button(
                            "📄 Descargar Certificado (Word)",
                            data=gen_doc(nom_usuario, dni_b, mis_contratos),
                            file_name=f"Certificado_{dni_b}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True
                        )
                    
                    # Editar / Eliminar (Solo si hay selección)
                    if not sel_rows.empty:
                        idx_sel = sel_rows.index[0]
                        id_real = mis_contratos.at[idx_sel, 'id'] # ID único
                        idx_global = dfs["CONTRATOS"][dfs["CONTRATOS"]['id'] == id_real].index[0]

                        st.write("---")
                        # BOTÓN ELIMINAR (APARTE) [cite: 55]
                        if st.button("🚨 Eliminar Contrato Seleccionado", type="primary", use_container_width=True):
                            dfs["CONTRATOS"] = dfs["CONTRATOS"].drop(idx_global)
                            save(dfs); st.rerun()
                        
                        # FORMULARIO EDITAR [cite: 53]
                        with st.expander("📝 Editar Contrato Seleccionado", expanded=True):
                            with st.form("form_edit"):
                                # Cargar valores existentes
                                e_car = st.text_input("Cargo", value=str(mis_contratos.at[idx_sel, 'cargo']))
                                e_sue = st.number_input("Sueldo", value=float(mis_contratos.at[idx_sel, 'sueldo']))
                                
                                val_ini = pd.to_datetime(mis_contratos.at[idx_sel, 'f_inicio']) if pd.notnull(mis_contratos.at[idx_sel, 'f_inicio']) else date.today()
                                val_fin = pd.to_datetime(mis_contratos.at[idx_sel, 'f_fin']) if pd.notnull(mis_contratos.at[idx_sel, 'f_fin']) else date.today()
                                e_ini = st.date_input("Inicio", value=val_ini)
                                e_fin = st.date_input("Fin", value=val_fin)
                                
                                e_tip = st.selectbox("Tipo", ["Docente", "Administrativo"], index=0 if "Docente" in str(mis_contratos.at[idx_sel, 'tipo']) else 1)
                                e_tco = st.text_input("Tipo Contrato", value=str(mis_contratos.at[idx_sel].get('tipo contrato','')))
                                e_tem = st.text_input("Temporalidad", value=str(mis_contratos.at[idx_sel].get('temporalidad','')))
                                e_lnk = st.text_input("Link", value=str(mis_contratos.at[idx_sel].get('link','')))
                                
                                idx_est = 0 if mis_contratos.at[idx_sel, 'estado'] == "ACTIVO" else 1
                                e_est = st.selectbox("Estado", ["ACTIVO", "CESADO"], index=idx_est)
                                
                                e_mot = "Vigente"
                                if e_est == "CESADO":
                                    val_mot = str(mis_contratos.at[idx_sel].get('motivo cese', 'Otros'))
                                    idx_mot = MOTIVOS.index(val_mot) if val_mot in MOTIVOS else 5
                                    e_mot = st.selectbox("Motivo Cese", MOTIVOS, index=idx_mot)

                                if st.form_submit_button("✅ Actualizar Cambios"):
                                    # Actualizar en DataFrame Global
                                    dfs["CONTRATOS"].at[idx_global, 'cargo'] = e_car
                                    dfs["CONTRATOS"].at[idx_global, 'sueldo'] = e_sue
                                    dfs["CONTRATOS"].at[idx_global, 'f_inicio'] = e_ini
                                    dfs["CONTRATOS"].at[idx_global, 'f_fin'] = e_fin
                                    dfs["CONTRATOS"].at[idx_global, 'tipo'] = e_tip
                                    dfs["CONTRATOS"].at[idx_global, 'tipo contrato'] = e_tco
                                    dfs["CONTRATOS"].at[idx_global, 'temporalidad'] = e_tem
                                    dfs["CONTRATOS"].at[idx_global, 'link'] = e_lnk
                                    dfs["CONTRATOS"].at[idx_global, 'estado'] = e_est
                                    dfs["CONTRATOS"].at[idx_global, 'motivo cese'] = e_mot
                                    save(dfs); st.rerun()

            # --- OTRAS PESTAÑAS (Lectura/Edición simple) ---
            for i, s_name in enumerate(SHS):
                # Saltamos Personal (no es pestaña) y Contratos (ya hecho)
                if s_name not in ["PERSONAL", "CONTRATOS"]:
                    # Mapeo de índices a nombres
                    idx_tab = -1
                    if s_name == "DATOS GENERALES": idx_tab = 0
                    elif s_name == "EXP. LABORAL": idx_tab = 1
                    elif s_name == "FORM. ACADEMICA": idx_tab = 2
                    elif s_name == "INVESTIGACION": idx_tab = 3
                    elif s_name == "DATOS FAMILIARES": idx_tab = 4
                    elif s_name == "VACACIONES": idx_tab = 6
                    elif s_name == "OTROS BENEFICIOS": idx_tab = 7
                    elif s_name == "MERITOS Y DEMERITOS": idx_tab = 8
                    elif s_name == "LIQUIDACIONES": idx_tab = 9
                    
                    if idx_tab != -1:
                        with tabs[idx_tab]:
                            st.write(f"Datos de: {s_name}")
                            df_v = dfs[s_name]
                            if 'dni' in df_v.columns:
                                st.dataframe(df_v[df_v['dni'] == dni_b], use_container_width=True)
                            else:
                                st.dataframe(df_v, use_container_width=True)
                            
        else:
            st.error("❌ DNI no encontrado. Por favor registre al trabajador primero.")
            st.info("Vaya a la opción 'Registro' en el menú lateral.")

# === MÓDULO DE REGISTRO [cite: 37] ===
elif m == "➕ Registro":
    st.header("Registro de Nuevo Colaborador")
    st.markdown("Ingrese los datos para dar de alta en la hoja **PERSONAL**.")
    
    with st.form("form_registro"):
        d_in = st.text_input("DNI").strip()
        n_in = st.text_input("Apellidos y Nombres").upper()
        l_in = st.text_input("Link Drive (Opcional)")
        
        if st.form_submit_button("Registrar Colaborador"):
            if d_in and n_in:
                df_p = dfs["PERSONAL"]
                if "dni" in df_p.columns and d_in in df_p["dni"].values:
                    st.error("¡Este DNI ya existe en la base de datos!")
                else:
                    nuevo = {"dni": d_in, "apellidos y nombres": n_in, "link": l_in}
                    dfs["PERSONAL"] = pd.concat([dfs["PERSONAL"], pd.DataFrame([nuevo])], ignore_index=True)
                    save(dfs)
                    st.success(f"✅ Registrado correctamente: {n_in}")
            else:
                st.warning("El DNI y Nombre son obligatorios.")

# === MÓDULO DE NÓMINA (Verificar) [cite: 38] ===
elif m == "📊 Nómina":
    st.header("Verificar Trabajadores (PERSONAL)")
    st.dataframe(dfs["PERSONAL"], use_container_width=True)
    st.write("---")
    st.subheader("Base Global de Contratos")
    st.dataframe(dfs["CONTRATOS"], use_container_width=True)

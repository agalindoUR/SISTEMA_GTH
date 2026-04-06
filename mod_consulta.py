import streamlit as st
import pandas as pd
from datetime import date
import mod_calculos_consulta
import mod_documentos

def mostrar(dfs, save_data, obtener_link_directo_drive, COLUMNAS, gen_word):
    st.markdown("<h2 style='color: #FFD700;'>Búsqueda de Colaborador</h2>", unsafe_allow_html=True)

    df_per_consulta = dfs["PERSONAL"].copy()
    
    df_per_consulta["dni_str"] = df_per_consulta.get("dni", pd.Series([""]*len(df_per_consulta))).astype(str).str.strip()
    apellidos_col = df_per_consulta.get("apellidos", pd.Series([""]*len(df_per_consulta))).fillna("").astype(str).str.strip()
    nombres_col = df_per_consulta.get("nombres", pd.Series([""]*len(df_per_consulta))).fillna("").astype(str).str.strip()
    
    df_per_consulta["nom_str"] = (apellidos_col + " " + nombres_col).str.strip()
    df_per_consulta["search_str"] = df_per_consulta["dni_str"] + " - " + df_per_consulta["nom_str"]
    
    opciones_buscador = [""] + [x for x in df_per_consulta["search_str"].tolist() if x != " - "]

    selected_search = st.selectbox("🔍 Escriba el DNI o Apellidos y Nombres:", opciones_buscador)

    if selected_search:
        dni_buscado = selected_search.split(" - ")[0].strip()
        fila_pers = df_per_consulta[df_per_consulta["dni_str"] == dni_buscado]
        
        if not fila_pers.empty:
            nom_c = fila_pers.iloc[0]["nom_str"]
            ape_c = str(fila_pers.iloc[0].get("apellidos", "")).strip()
            nom_p_c = str(fila_pers.iloc[0].get("nombres", "")).strip()

            # --- LÓGICA DE FOTO ---
            link_foto_raw = fila_pers.iloc[0].get("foto", fila_pers.iloc[0].get("FOTO", ""))
            foto_directa = None
            if pd.notnull(link_foto_raw) and str(link_foto_raw).strip() != "":
                if obtener_link_directo_drive:
                    foto_directa = obtener_link_directo_drive(str(link_foto_raw).strip())
                else:
                    foto_directa = str(link_foto_raw).strip()

            if foto_directa:
                st.markdown(f"""
                    <style>
                    .foto-perfil-large {{ width: 110px; height: 110px; border-radius: 50%; object-fit: cover; object-position: center; border: 4px solid #FFD700; margin-right: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); transition: transform 0.2s ease-in-out; }}
                    .foto-perfil-large:hover {{ transform: scale(1.08); }}
                    </style>
                    <div style='border-bottom: 2px solid #FFD700; padding-bottom: 15px; margin-bottom: 25px; display: flex; align-items: center;'>
                        <img src='{foto_directa}' class='foto-perfil-large' onerror="this.style.display='none'; document.getElementById('avatar-{dni_buscado}').style.display='block';">
                        <h1 id='avatar-{dni_buscado}' style='color: white; margin: 0; margin-right: 15px; font-size: 3em; display: none;'>👤</h1>
                        <h1 style='color: #FFD700; margin: 0; font-size: 2.5em;'>{nom_c}</h1>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div style='border-bottom: 2px solid #FFD700; padding-bottom: 10px; margin-bottom: 20px; display: flex; align-items: center;'>
                        <h1 style='color: white; margin: 0; margin-right: 15px; font-size: 3em;'>👤</h1>
                        <h1 style='color: #FFD700; margin: 0; font-size: 2.5em;'>{nom_c}</h1>
                    </div>
                """, unsafe_allow_html=True)
                                
            t_noms = ["Datos Generales", "Exp. Laboral", "Form. Académica", "Investigación", "Datos Familiares", "Contratos", "Vacaciones", "Otros Beneficios", "Méritos/Demer.", "Evaluación", "Liquidaciones"]
            h_keys = ["DATOS GENERALES", "EXP. LABORAL", "FORM. ACADEMICA", "INVESTIGACION", "DATOS FAMILIARES", "CONTRATOS", "VACACIONES", "OTROS BENEFICIOS", "MERITOS Y DEMERITOS", "EVALUACION DEL DESEMPEÑO", "LIQUIDACIONES"]

            tabs = st.tabs(t_noms)

            for i, tab in enumerate(tabs):
                h_name = h_keys[i]
                with tab:
                    if h_name in dfs and "dni" in dfs[h_name].columns:
                        c_df = dfs[h_name][dfs[h_name]["dni"] == dni_buscado]
                    else:
                        c_df = pd.DataFrame(columns=COLUMNAS.get(h_name, []) if COLUMNAS else [])

                    # --- DELEGAMOS LA CREACIÓN DE DOCUMENTOS (CONTRATOS) ---
                    if h_name == "CONTRATOS":
                        df_contratos = dfs["CONTRATOS"][dfs["CONTRATOS"]["dni"] == dni_buscado]
                        mod_documentos.generar_boton_certificado(nom_c, dni_buscado, df_contratos)

                    # --- DELEGAMOS EL CÁLCULO COMPLEJO (VACACIONES Y EXPERIENCIA) ---
                    if h_name == "VACACIONES":
                        df_contratos = dfs.get("CONTRATOS", pd.DataFrame())
                        df_c_filtro = df_contratos[df_contratos["dni"] == dni_buscado] if not df_contratos.empty else pd.DataFrame()
                        mod_calculos_consulta.calcular_vacaciones(c_df, df_c_filtro)

                    if h_name == "EXP. LABORAL":
                        df_contratos = dfs.get("CONTRATOS", pd.DataFrame())
                        sel = mod_calculos_consulta.mostrar_experiencia(c_df, df_contratos, dni_buscado)
                        
                    # --- CONFIGURACIÓN DE TABLAS ESTÁNDAR ---
                    vst = c_df.copy()
                    sel = pd.DataFrame() 
                    
                    cols_ocultar = [c for c in vst.columns if c.lower() in ["apellidos y nombres", "apellidos", "nombres"]]
                    vst = vst.drop(columns=cols_ocultar, errors='ignore')

                    col_conf = {}
                    for col in vst.columns:
                        if "fecha" in col.lower() or "f_" in col.lower():
                            vst[col] = pd.to_datetime(vst[col], errors='coerce').dt.date
                            col_conf[str(col).upper()] = st.column_config.DateColumn(format="DD/MM/YYYY", min_value=date(1950, 1, 1), max_value=date(2100, 12, 31))
                        elif col.lower().strip() == "periodo":
                            vst[col] = vst[col].astype(str)
                            col_conf[str(col).upper()] = st.column_config.TextColumn()

                    vst.columns = [str(col).upper() for col in vst.columns]
                    vst = vst.loc[:, ~vst.columns.duplicated()]
            
                    # =========================================================
                    # DISEÑO TIPO FICHA PARA "DATOS GENERALES"
                    # =========================================================
                    if h_name == "DATOS GENERALES" and not vst.empty:
                        ficha = vst.iloc[0]
                        def get_val(names):
                            ficha_clean = {str(k).lower().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('_',' '): v for k, v in ficha.to_dict().items()}
                            for name in names:
                                clean_name = name.lower().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('_',' ')
                                val = ficha_clean.get(clean_name)
                                if pd.notnull(val) and str(val).strip() not in ["", "-", "0", "nan"]: return str(val)
                            return "-"

                        sede = get_val(['SEDE'])
                        sexo = get_val(['SEXO'])
                        est_civil = get_val(['ESTADO CIVIL', 'ESTADO_CIVIL'])
                        f_nac = get_val(['FECHA DE NACIMIENTO', 'NACIMIENTO'])
                        edad = get_val(['EDAD'])
                        telefono = get_val(['CELULAR', 'TELEFONO', 'TELÉFONO'])
                        correo = get_val(['CORREO', 'EMAIL', 'CORREO ELECTRONICO'])
                        direccion = get_val(['DIRECCION', 'DIRECCIÓN', 'DOMICILIO'])
                        
                        dir_display = "-"
                        if direccion != "-":
                            query_map = direccion.replace(" ", "+")
                            link_mapa = f"https://www.google.com/maps/search/?api=1&query={query_map}"
                            dir_display = f'<a href="{link_mapa}" target="_blank" style="color: #4da3ff; text-decoration: none; font-weight: bold;">📍 {direccion} (Ver en Google Maps 🗺️)</a>'

                        st.markdown(f"""
                        <div style="background-color: rgba(255, 215, 0, 0.05); padding: 25px; border-radius: 15px; border: 2px solid #FFD700; color: inherit; font-family: sans-serif;">
                            <h2 style="margin-top:0; color: #FFD700; border-bottom: 1px solid rgba(255,215,0,0.3); padding-bottom:10px;">🪪 Expediente del Personal</h2>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 20px; margin-top: 15px;">
                                <div><p style="margin:0; font-size: 0.85em; opacity: 0.7;">📍 SEDE</p><p style="margin:0; font-weight: bold; font-size: 1.1em;">{sede}</p></div>
                                <div><p style="margin:0; font-size: 0.85em; opacity: 0.7;">🚻 SEXO</p><p style="margin:0; font-weight: bold; font-size: 1.1em;">{sexo}</p></div>
                                <div><p style="margin:0; font-size: 0.85em; opacity: 0.7;">💍 ESTADO CIVIL</p><p style="margin:0; font-weight: bold; font-size: 1.1em;">{est_civil}</p></div>
                                <div><p style="margin:0; font-size: 0.85em; opacity: 0.7;">🎂 F. NACIMIENTO</p><p style="margin:0; font-weight: bold; font-size: 1.1em;">{f_nac}</p></div>
                                <div><p style="margin:0; font-size: 0.85em; opacity: 0.7;">🔢 EDAD ACTUAL</p><p style="margin:0; font-weight: bold; font-size: 1.1em;">{edad} años</p></div>
                                <div><p style="margin:0; font-size: 0.85em; opacity: 0.7;">📱 TELÉFONO / CELULAR</p><p style="margin:0; font-weight: bold; font-size: 1.1em;">{telefono}</p></div>
                            </div>
                            <div style="margin-top: 25px; padding-top: 15px; border-top: 1px dashed rgba(255,215,0,0.3);">
                                <div style="margin-bottom: 15px;">
                                    <p style="margin:0; font-size: 0.85em; opacity: 0.7;">📧 CORREO ELECTRÓNICO</p>
                                    <p style="margin:0; font-weight: bold; font-size: 1.1em;">{correo}</p>
                                </div>
                                <div>
                                    <p style="margin:0; font-size: 0.85em; opacity: 0.7;">🏠 DIRECCIÓN DE DOMICILIO</p>
                                    <p style="margin:0; font-size: 1.1em;">{dir_display}</p>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.write("")
                        sel = vst.head(1)

                    # =========================================================
                    # DISEÑO DE TABLA NORMAL Y EDICIÓN
                    # =========================================================
                    else:
                        if "SEL" not in vst.columns:
                            vst.insert(0, "SEL", False)
                            
                        # Limpieza visual
                        columnas_basura = ["DNI", "FECHA DE INICIO", "FECHA DE FIN", "DIAS GENERADOS", "SALDO"]
                        for col in columnas_basura:
                            if col in vst.columns: col_conf[col] = None
                                
                        cols_importantes = ["SEL", "PERIODO", "F_INICIO", "F_FIN", "DIAS GOZADOS"]
                        cols_finales = [c for c in cols_importantes if c in vst.columns] + [c for c in vst.columns if c not in cols_importantes]
                        vst = vst[list(dict.fromkeys(cols_finales))]

                        st.markdown("<br>", unsafe_allow_html=True)
                        with st.expander(f"⚙️ Clic aquí para Editar o Eliminar registros en {h_name.title()}"):
                            st.markdown("""<style>[data-testid="stDataEditor"] { border: 2px solid #FFD700 !important; border-radius: 10px !important; }</style>""", unsafe_allow_html=True)
                            ed = st.data_editor(vst, hide_index=True, use_container_width=True, column_config=col_conf, key=f"ed_{h_name}_oculta")
                            for col in ed.columns:
                                if "fecha" in col.lower() or "f_" in col.lower():
                                    ed[col] = ed[col].astype(str).replace(["NaT", "None"], "")
                            sel = ed[ed["SEL"] == True]

                    # LOGICA DE GUARDADO COMPARTIDA
                    if h_name != "DATOS GENERALES":
                        if not sel.empty:
                            st.markdown("---")
                            st.markdown("### ✍️ Modificar / Eliminar Registro")
                            for i, (_, row) in enumerate(sel.iterrows()):
                                # Obtenemos el índice real en el dataframe original
                                df_temp = dfs[h_name][dfs[h_name]["dni"] == dni_buscado]
                                if not df_temp.empty:
                                    idx = df_temp.index[0] # Simplificación: toma el primero. Si manejas IDs únicos, úsalos aquí.
                                    
                                    with st.form(f"form_edit_{h_name}_{idx}_{i}"):
                                        edit_row = {}
                                        cols_display = st.columns(3)
                                        col_idx = 0
                                        for col in dfs[h_name].columns:
                                            if col.lower() not in ["dni", "id", "sel"]:
                                                val = dfs[h_name].at[idx, col]
                                                with cols_display[col_idx % 3]:
                                                    edit_row[col] = st.text_input(col.title(), value=str(val) if pd.notnull(val) else "", key=f"t_{h_name}_{col}_{idx}_{i}")
                                                col_idx += 1

                                        c1, c2 = st.columns(2)
                                        with c1:
                                            if st.form_submit_button("Actualizar Registro"):
                                                for k, v in edit_row.items(): 
                                                    dfs[h_name].at[idx, k] = v
                                                save_data(dfs)
                                                st.rerun()
                                        with c2:
                                            if st.form_submit_button("🗑️ Eliminar Registro", type="primary"):
                                                dfs[h_name] = dfs[h_name].drop(idx)
                                                save_data(dfs)
                                                st.rerun()
                        else:
                            st.info("Activa la casilla (SEL) en la tabla superior para editar o eliminar el registro.")
        else:
            st.error("DNI no encontrado en la base de datos.")

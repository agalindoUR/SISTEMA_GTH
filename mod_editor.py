import streamlit as st
import pandas as pd
from datetime import date, datetime

def mostrar_editor(dfs, save_data, h_name, sel, cols_reales):
    with st.expander("📝 Editar / Eliminar"):
        
        # --- INICIO DE LA CORRECCIÓN (BLINDAJE CONTRA NAMEERROR) ---
        try:
            hay_seleccion = not sel.empty
        except (NameError, AttributeError):
            hay_seleccion = False
        # --- FIN DE LA CORRECCIÓN ---
        
        if hay_seleccion:
            idx = sel.index[0]
            
            # --- CARGA DINÁMICA HOMOGÉNEA DE PARÁMETROS DESDE EXCEL ---
            df_para = dfs.get("PARAMETROS", pd.DataFrame())
            temp_para = pd.DataFrame()
            if not df_para.empty:
                temp_para = df_para.copy()
                temp_para.columns = temp_para.columns.str.strip().str.replace(" ", "_").str.upper()

            # Función de búsqueda flexible
            def obtener_lista(columna_name, default):
                target = columna_name.strip().replace(" ", "_").upper()
                if not temp_para.empty:
                    for col in temp_para.columns:
                        if col == target or col.replace("_", "") == target.replace("_", ""):
                            lista = temp_para[col].dropna().astype(str).str.strip().unique().tolist()
                            lista = [item for item in lista if item and item.lower() != "nan"]
                            if lista: return lista
                return default

            with st.form(f"f_edit_{h_name}"):
                if h_name == "CONTRATOS":
                    # ---> CARGO Y ÁREA COMO LISTAS DESPLEGABLES <---
                    v_car = str(sel.iloc[0].get("CARGO", "")).strip()
                    lista_car = obtener_lista("CARGO", ["Docente", "Administrativo"])
                    if v_car and v_car not in lista_car: lista_car.append(v_car)
                    n_car = st.selectbox("Cargo", lista_car, index=lista_car.index(v_car) if v_car in lista_car else 0)

                    v_area = str(sel.iloc[0].get("AREA", "")).strip()
                    lista_area = obtener_lista("AREA", ["Recursos Humanos", "Dirección Académica"])
                    if v_area and v_area not in lista_area: lista_area.append(v_area)
                    n_area = st.selectbox("Área", lista_area, index=lista_area.index(v_area) if v_area in lista_area else 0)
                    
                    try:
                        val_rem = float(sel.iloc[0].get("REMUNERACION BASICA", 0.0))
                    except:
                        val_rem = 0.0
                    n_rem = st.number_input("Remuneración básica", value=val_rem)
                    
                    n_bon = st.text_input("Bonificación", value=str(sel.iloc[0].get("BONIFICACION", "")))
                    n_cond = st.text_input("Condición de trabajo", value=str(sel.iloc[0].get("CONDICION DE TRABAJO", "")))
                    
                    try:
                        val_ini = sel.iloc[0].get("F_INICIO")
                        ini_val = pd.to_datetime(val_ini).date() if pd.notnull(val_ini) else date.today()
                    except:
                        ini_val = date.today()
                    n_ini = st.date_input("Inicio", value=ini_val, format="DD/MM/YYYY", min_value=date(1950, 1, 1), max_value=date(2100, 12, 31))
                    
                    try:
                        val_fin = sel.iloc[0].get("F_FIN")
                        fin_val = pd.to_datetime(val_fin).date() if pd.notnull(val_fin) else date.today()
                    except:
                        fin_val = date.today()
                    n_fin = st.date_input("Fin", value=fin_val, format="DD/MM/YYYY", min_value=date(1950, 1, 1), max_value=date(2100, 12, 31))
                    
                    # 1. Tipo de trabajador (Dinámico)
                    v_ttrab = str(sel.iloc[0].get("TIPO DE TRABAJADOR", "")).strip()
                    lista_tt = obtener_lista("TIPO DE TRABAJADOR", ["Administrativo", "Docente", "Externo"])
                    if v_ttrab and v_ttrab not in lista_tt: lista_tt.append(v_ttrab)
                    n_ttrab = st.selectbox("Tipo de trabajador", lista_tt, index=lista_tt.index(v_ttrab) if v_ttrab in lista_tt else 0)
                    
                    # 2. Modalidad (Dinámico)
                    v_mod = str(sel.iloc[0].get("MODALIDAD", "")).strip()
                    lista_mod = obtener_lista("MODALIDAD", ["Presencial", "Semipresencial", "Virtual"])
                    if v_mod and v_mod not in lista_mod: lista_mod.append(v_mod)
                    n_mod = st.selectbox("Modalidad", lista_mod, index=lista_mod.index(v_mod) if v_mod in lista_mod else 0)
                    
                    # 3. Temporalidad (Dinámico)
                    v_tem = str(sel.iloc[0].get("TEMPORALIDAD", "")).strip()
                    lista_tem = obtener_lista("TEMPORALIDAD", ["Plazo fijo", "Plazo indeterminado", "Ordinarizado"])
                    if v_tem and v_tem not in lista_tem: lista_tem.append(v_tem)
                    n_tem = st.selectbox("Temporalidad", lista_tem, index=lista_tem.index(v_tem) if v_tem in lista_tem else 0)
                    
                    n_lnk = st.text_input("Link", value=str(sel.iloc[0].get("LINK", "")))
                    
                    # 4. Tipo de Contrato (Dinámico)
                    v_tcont = str(sel.iloc[0].get("TIPO CONTRATO", "")).strip()
                    lista_tcon = obtener_lista("TIPO CONTRATO", ["Planilla completo", "Tiempo Parcial", "Recibo por Honorarios", "Otro"])
                    if v_tcont and v_tcont not in lista_tcon: lista_tcon.append(v_tcont)
                    n_tcont = st.selectbox("Tipo Contrato", lista_tcon, index=lista_tcon.index(v_tcont) if v_tcont in lista_tcon else 0)
                    
                    # 5. Motivo Cese (Dinámico)
                    st.markdown("<small style='color:#666;'>💡 *El estado (ACTIVO/CESADO) se calculará automáticamente al guardar la Fecha de Fin.*</small>", unsafe_allow_html=True)
                    v_mot = str(sel.iloc[0].get("MOTIVO CESE", "Vigente")).strip()
                    base_motivos = ["Renuncia", "Término de contrato", "Despido", "Mutuo disenso"]
                    lista_mot = ["Vigente"] + obtener_lista("MOTIVO CESE", base_motivos)
                    if v_mot and v_mot not in lista_mot: lista_mot.append(v_mot)
                    mot_e = st.selectbox("Motivo Cese", lista_mot, index=lista_mot.index(v_mot) if v_mot in lista_mot else 0)
                    
                    # ---> BOTONES DE ACTUALIZAR Y ELIMINAR (CONTRATOS) <---
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.form_submit_button("Actualizar Contrato"):
                            est_final = "ACTIVO" if n_fin >= date.today() else "CESADO"
                            
                            update_vals = {
                                "cargo": n_car, "area": n_area, "remuneracion basica": n_rem, "bonificacion": n_bon,
                                "condicion de trabajo": n_cond, "f_inicio": n_ini, "f_fin": n_fin, "tipo de trabajador": n_ttrab,
                                "modalidad": n_mod, "temporalidad": n_tem, "link": n_lnk, "tipo contrato": n_tcont, "estado": est_final, "motivo cese": mot_e
                            }
                            for k, v in update_vals.items():
                                if k in dfs[h_name].columns:
                                    dfs[h_name][k] = dfs[h_name][k].astype(object)
                                    dfs[h_name].at[idx, k] = v
                            save_data(dfs)
                            st.rerun()
                            
                    with col_btn2:
                        if st.form_submit_button("🗑️ Eliminar Contrato", type="primary"):
                            dfs[h_name] = dfs[h_name].drop(idx)
                            save_data(dfs)
                            st.rerun()

                else:
                    # ---> AQUÍ SE RECUPERA EL BLOQUE PARA DATOS GENERALES <---
                    edit_row = {}
                    row = sel.iloc[0]
                    
                    columnas_limpias = []
                    vistas = set()
                    for c in cols_reales:
                        c_upper = str(c).upper().strip() 
                        if c_upper not in vistas and c_upper != "AREA":
                            vistas.add(c_upper)
                            columnas_limpias.append(c)
                    
                    lista_sexo = obtener_lista("SEXO", ["Masculino", "Femenino"])
                    lista_estado = obtener_lista("ESTADO CIVIL", ["Soltero(a)", "Casado(a)", "Divorciado(a)", "Conviviente", "Viudo(a)"])
                    lista_sede = obtener_lista("SEDE TRABAJO", ["Sede Central"])
                    
                    for i, col in enumerate(columnas_limpias):
                        val = row.get(str(col).upper(), "")
                        col_lower = str(col).lower().strip()
                        
                        if h_name == "DATOS GENERALES" and col_lower == "sexo":
                            v_actual = str(val) if pd.notnull(val) and val else "Masculino"
                            if v_actual not in lista_sexo: lista_sexo.append(v_actual)
                            edit_row[col] = st.selectbox(col.title(), lista_sexo, index=lista_sexo.index(v_actual), key=f"sel_{h_name}_{col}_{idx}_{i}")
                            
                        elif h_name == "DATOS GENERALES" and col_lower == "estado civil":
                            v_actual = str(val) if pd.notnull(val) and val else "Soltero(a)"
                            if v_actual not in lista_estado: lista_estado.append(v_actual)
                            edit_row[col] = st.selectbox(col.title(), lista_estado, index=lista_estado.index(v_actual), key=f"sel_{h_name}_{col}_{idx}_{i}")
                            
                        elif h_name == "DATOS GENERALES" and col_lower == "sede":
                            v_actual = str(val) if pd.notnull(val) and val else "Sede Central"
                            if v_actual not in lista_sede: lista_sede.append(v_actual)
                            edit_row[col] = st.selectbox(col.title(), lista_sede, index=lista_sede.index(v_actual), key=f"sel_{h_name}_{col}_{idx}_{i}")
                            
                        elif "fecha" in col_lower or "f_" in col_lower:
                            if pd.notnull(val) and isinstance(val, (date, datetime)): d_val = val
                            elif pd.notnull(val) and isinstance(val, str):
                                try: d_val = pd.to_datetime(val).date()
                                except: d_val = date.today()
                            else: d_val = date.today()
                            edit_row[col] = st.date_input(col.title(), value=d_val, format="DD/MM/YYYY", min_value=date(1950, 1, 1), max_value=date(2100, 12, 31), key=f"date_{h_name}_{col}_{idx}_{i}")
                            
                        elif col_lower == "edad":
                            fnac_val = next((v for k, v in row.items() if "fecha de nacimiento" in str(k).lower()), None)
                            val_edad = 0
                            
                            if pd.notnull(fnac_val) and str(fnac_val).strip() != "":
                                try:
                                    if isinstance(fnac_val, str):
                                        fnac_date = pd.to_datetime(fnac_val, dayfirst=True).date()
                                    else:
                                        fnac_date = fnac_val.date() if isinstance(fnac_val, datetime) else fnac_val
                                    hoy = date.today()
                                    val_edad = hoy.year - fnac_date.year - ((hoy.month, hoy.day) < (fnac_date.month, fnac_date.day))
                                except:
                                    pass
                                    
                            if val_edad == 0:
                                try:
                                    val_edad = int(val) if pd.notnull(val) and str(val).replace('.','',1).isdigit() else 0
                                except:
                                    val_edad = 0
                                    
                            edit_row[col] = st.number_input(col.title(), value=val_edad, disabled=True, key=f"edad_{h_name}_{col}_{idx}_{i}")
                            
                        else:
                            edit_row[col] = st.text_input(col.title(), value=str(val) if pd.notnull(val) else "", key=f"text_{h_name}_{col}_{idx}_{i}")
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.form_submit_button("Actualizar Registro"):
                            # --- CÁLCULO INVISIBLE ANTES DE ENVIAR A SHEETS ---
                            llave_fecha = next((k for k in edit_row.keys() if "fecha de nacimiento" in str(k).lower()), None)
                            llave_edad = next((k for k in edit_row.keys() if str(k).lower().strip() == "edad"), None)
                            
                            if llave_fecha and llave_edad:
                                fnac_nueva = edit_row[llave_fecha]
                                if isinstance(fnac_nueva, (date, datetime)):
                                    hoy = date.today()
                                    f_comparar = fnac_nueva.date() if isinstance(fnac_nueva, datetime) else fnac_nueva
                                    edad_nueva = hoy.year - f_comparar.year - ((hoy.month, hoy.day) < (f_comparar.month, f_comparar.day))
                                    edit_row[llave_edad] = edad_nueva
                            
                            for k, v in edit_row.items():
                                if k in dfs[h_name].columns:
                                    dfs[h_name][k] = dfs[h_name][k].astype(object)
                                    dfs[h_name].at[idx, k] = v
                                    
                            try:
                                save_data(dfs, pestana_especifica=h_name)
                            except TypeError:
                                save_data(dfs) # Fallback por si tu save_data original no usa "pestana_especifica"
                            st.rerun()
                            
                    with col_btn2:
                        if st.form_submit_button("🗑️ Eliminar Registro", type="primary"):
                            dfs[h_name] = dfs[h_name].drop(idx)
                            save_data(dfs)
                            st.rerun()
                            
        else:
            st.info("Activa la casilla (SEL) en la tabla superior para editar o eliminar el registro. Si estás buscando a alguien que ingresaste a mano, verifica que su nombre en el Google Sheets no tenga espacios al final.")

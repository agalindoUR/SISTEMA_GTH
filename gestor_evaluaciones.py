import streamlit as st
import pandas as pd
import io

def mostrar(dfs, save_data): # Añadimos save_data aquí
    st.markdown("<h2 style='color: #4A0000;'>📋 Gestión de Evaluaciones de Desempeño</h2>", unsafe_allow_html=True)
    
    # Creamos las pestañas (¡Ahora con Dashboard!)
    tab_carga, tab_interna, tab_ficha, tab_dashboard = st.tabs([
        "📥 Carga Masiva (Google Forms)", 
        "📝 Realizar Evaluación Interna", 
        "📇 Ficha Individual Completa",
        "📊 Dashboard de Resultados"
    ])
    
    # ==========================================
    # PESTAÑA 1: CARGA MASIVA (EL TRADUCTOR)
    # ==========================================
    with tab_carga:
        st.markdown("### 📤 Importar resultados de Google Forms")
        st.info("Sube el archivo Excel/CSV. El sistema cruzará los DNIs con la tabla PERSONAL para extraer áreas y cargos automáticamente.")
        
        col1, col2 = st.columns(2)
        with col1:
            periodo_sel = st.selectbox("📅 Selecciona el Periodo:", ["2024-I", "2024-II", "2025-I", "2025-II"])
        with col2:
            tipo_eval_sel = st.selectbox("🏷️ Tipo de Evaluación:", ["Competencias Generales", "Competencias Específicas", "KPIs", "Evaluación 360"])
            
        archivo_subido = st.file_uploader("Sube el archivo CSV o Excel de Google Forms", type=["csv", "xlsx"])
        
        if archivo_subido is not None:
            try:
                # Detectamos si es CSV o Excel
                if archivo_subido.name.endswith('.csv'):
                    try:
                        df_raw = pd.read_csv(archivo_subido, sep=None, engine='python', encoding='utf-8')
                    except UnicodeDecodeError:
                        archivo_subido.seek(0)
                        df_raw = pd.read_csv(archivo_subido, sep=None, engine='python', encoding='latin-1')
                elif archivo_subido.name.endswith('.xlsx'):
                    df_raw = pd.read_excel(archivo_subido)
                
                st.success("✅ Archivo leído correctamente. Vista previa:")
                st.dataframe(df_raw.head(3))
                
                st.markdown("#### ⚙️ Configuración del Traductor")
                col_identificador = st.selectbox("1️⃣ ¿Qué columna contiene el DNI del empleado evaluado?", df_raw.columns)
                
                if st.button("🪄 Procesar y Traducir Datos", type="primary"):
                    st.write("Iniciando procesamiento y cruce de datos...")
                    
                    cols_preguntas = [c for c in df_raw.columns if ":" in c or "[" in c]
                    
                    if not cols_preguntas:
                        st.error("No se detectaron columnas con el formato de preguntas (Ej: 'COMPETENCIA: ... [Pregunta]').")
                    else:
                        resultados = []
                        df_per = dfs.get("PERSONAL", pd.DataFrame()) # Obtenemos datos del personal
                        
                        for index, row in df_raw.iterrows():
                            empleado_id = str(row[col_identificador]).strip()
                            
                            # Variables por defecto (por si el DNI no existe en PERSONAL)
                            nombres_completos = empleado_id
                            dni_final = empleado_id
                            cargo_final = "No registrado"
                            area_final = "No registrada"

                            # Cruce mágico con la base de PERSONAL
                            if not df_per.empty and "dni" in df_per.columns:
                                match = df_per[df_per["dni"].astype(str).str.strip() == empleado_id]
                                if not match.empty:
                                    nombres_completos = f"{match.iloc[0].get('apellidos', '')} {match.iloc[0].get('nombres', '')}".strip()
                                    cargo_final = match.iloc[0].get('cargo', 'No registrado')
                                    area_final = match.iloc[0].get('area', 'No registrada')
                                    dni_final = match.iloc[0].get('dni', empleado_id)

                            diccionario_notas = {}
                            
                            for col in cols_preguntas:
                                competencia = col.split(":")[0].strip().title()
                                valor = row[col]
                                
                                try:
                                    if pd.notna(valor):
                                        nota_num = float(str(valor).split(".")[0])
                                        if competencia not in diccionario_notas:
                                            diccionario_notas[competencia] = []
                                        diccionario_notas[competencia].append(nota_num)
                                except:
                                    pass 
                                    
                            texto_formato_final = []
                            suma_total = 0
                            cant_comps = 0
                            
                            for comp, notas in diccionario_notas.items():
                                if notas:
                                    promedio_comp = sum(notas) / len(notas)
                                    texto_formato_final.append(f"{comp}: {promedio_comp:.1f}")
                                    suma_total += promedio_comp
                                    cant_comps += 1
                                    
                            promedio_general = suma_total / cant_comps if cant_comps > 0 else 0
                            string_final = " | ".join(texto_formato_final)
                            
                            # ARMAMOS EL DICCIONARIO EXACTAMENTE COMO TU GOOGLE SHEET
                            resultados.append({
                                "DNI": dni_final,
                                "NOMBRES Y APELLIDOS": nombres_completos,
                                "PERIODO": periodo_sel,
                                "CARGO": cargo_final,
                                "ÁREA": area_final,
                                "PROMEDIO GENERAL": round(promedio_general, 2),
                                "NOTAS GENERALES": string_final,
                                "TIPO DE EVALUACIÓN": tipo_eval_sel
                            })
                            
                        st.session_state['tabla_temporal'] = pd.DataFrame(resultados)
                        
            except Exception as e:
                st.error(f"Hubo un error al procesar el archivo: {e}")

        # --- BOTÓN PARA GUARDAR DEFINITIVAMENTE ---
        if 'tabla_temporal' in st.session_state:
            st.success("🎉 ¡Datos traducidos! Revisa que los nombres, cargos y áreas se hayan completado correctamente.")
            st.dataframe(st.session_state['tabla_temporal'])
            
            if st.button("💾 Guardar Resultados en Base de Datos", type="primary"):
                # Si la pestaña EVALUACIONES no existe, la creamos con tus columnas
                if "EVALUACIONES" not in dfs:
                    dfs["EVALUACIONES"] = pd.DataFrame(columns=[
                        "DNI", "NOMBRES Y APELLIDOS", "PERIODO", "CARGO", "ÁREA", "PROMEDIO GENERAL", "NOTAS GENERALES", "TIPO DE EVALUACIÓN"
                    ])
                    
                # Unimos y Guardamos
                dfs["EVALUACIONES"] = pd.concat([dfs["EVALUACIONES"], st.session_state['tabla_temporal']], ignore_index=True)
                
                # ¡LA FUNCIÓN MÁGICA QUE GUARDA EN GOOGLE SHEETS!
                save_data(dfs)
                
                st.balloons()
                st.success("✅ ¡Datos guardados exitosamente en Google Sheets!")
                del st.session_state['tabla_temporal']

    # ==========================================
    # PESTAÑA 2: EVALUACIÓN INTERNA 
    # ==========================================
    with tab_interna:
        st.markdown("### 📝 Formulario de Evaluación Interna")
        st.write("Genera una evaluación manual en el sistema o copia el enlace para enviarlo a un evaluador.")
        df_per = dfs.get("PERSONAL", pd.DataFrame())
        if not df_per.empty:
            lista_emp = df_per["dni"].astype(str) + " - " + df_per.get("nombres", "Empleado")
            emp_a_evaluar = st.selectbox("Selecciona al trabajador a evaluar:", lista_emp)
            st.markdown(f"**🔗 Enlace directo para el evaluador:**")
            st.code(f"https://tu-sistema-gth.streamlit.app/?evaluar={emp_a_evaluar.split(' - ')[0]}&periodo=2025-I")
            st.info("Función en desarrollo para próximas versiones.")
        else:
            st.warning("No hay datos de personal cargados.")

    # ==========================================
    # PESTAÑA 3: FICHA INDIVIDUAL 
    # ==========================================
    with tab_ficha:
        st.markdown("### 📇 Ficha de Evaluación Detallada")
        st.write("Consulta el detalle exacto de un trabajador.")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.text_input("🔍 Ingresa el DNI del trabajador:")
        with col_f2:
            st.selectbox("📅 Filtrar por Periodo:", ["Todos", "2024-I", "2024-II", "2025-I"])
        st.info("Aquí mostraremos la vista estilo 'Boleta de Notas'.")

    # ==========================================
    # PESTAÑA 4: DASHBOARD GENERAL
    # ==========================================
    with tab_dashboard:
        st.markdown("### 📊 Dashboard de Desempeño")
        
        df_eval = dfs.get("EVALUACIONES", pd.DataFrame()).copy()
        
        # 🛡️ BLINDAJE DE COLUMNAS: Limpiamos espacios ocultos y forzamos mayúsculas
        df_eval.columns = [str(c).strip().upper() for c in df_eval.columns]
        
        # Verificamos si la columna existe después de limpiarla
        if df_eval.empty or "PROMEDIO GENERAL" not in df_eval.columns:
            st.warning("Aún no hay evaluaciones registradas o no se encuentra la columna 'PROMEDIO GENERAL'. Ve a la pestaña 'Carga Masiva', procesa un archivo y guárdalo.")
        else:
            # Limpiamos las comas por puntos y convertimos a número
            df_eval["PROMEDIO GENERAL"] = df_eval["PROMEDIO GENERAL"].astype(str).str.replace(',', '.').str.strip()
            df_eval["PROMEDIO GENERAL"] = pd.to_numeric(df_eval["PROMEDIO GENERAL"], errors='coerce')
            
            # Filtro por periodo (si la columna PERIODO existe)
            if "PERIODO" in df_eval.columns:
                periodos_disp = ["Todos"] + df_eval["PERIODO"].dropna().unique().tolist()
                filtro_periodo = st.selectbox("Filtrar Dashboard por Periodo:", periodos_disp)
                if filtro_periodo != "Todos":
                    df_filtrado = df_eval[df_eval["PERIODO"] == filtro_periodo]
                else:
                    df_filtrado = df_eval.copy()
            else:
                df_filtrado = df_eval.copy()
            
            # Ocultamos filas sin nota válida
            df_filtrado = df_filtrado.dropna(subset=["PROMEDIO GENERAL"])
            
            # KPIs Rápidos
            col_k1, col_k2, col_k3 = st.columns(3)
            promedio_empresa = df_filtrado["PROMEDIO GENERAL"].mean()
            total_evaluados = len(df_filtrado)
            
            col_k1.metric("Promedio General Empresa", f"{promedio_empresa:.2f}" if pd.notnull(promedio_empresa) else "0.0")
            col_k2.metric("Total Evaluaciones", total_evaluados)
            
            if "ÁREA" in df_filtrado.columns:
                col_k3.metric("Áreas Evaluadas", df_filtrado["ÁREA"].nunique())
            else:
                col_k3.metric("Áreas Evaluadas", 0)
            
            st.divider()
            
            # Gráficos de barra
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.markdown("**Promedio de Desempeño por Área**")
                if "ÁREA" in df_filtrado.columns and not df_filtrado.empty:
                    promedio_area = df_filtrado.groupby("ÁREA")["PROMEDIO GENERAL"].mean().reset_index()
                    st.bar_chart(promedio_area.set_index("ÁREA"))
                else:
                    st.info("No hay datos de áreas para graficar.")
                    
            with col_g2:
                st.markdown("**Top 5 Colaboradores**")
                if "NOMBRES Y APELLIDOS" in df_filtrado.columns and not df_filtrado.empty:
                    top_5 = df_filtrado.nlargest(5, "PROMEDIO GENERAL")[["NOMBRES Y APELLIDOS", "PROMEDIO GENERAL"]]
                    st.dataframe(top_5, hide_index=True, use_container_width=True)
                else:
                    st.info("No hay datos de colaboradores para mostrar.")

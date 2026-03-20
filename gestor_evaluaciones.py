import streamlit as st
import pandas as pd
import io

def mostrar(dfs):
    st.markdown("<h2 style='color: #4A0000;'>📋 Gestión de Evaluaciones de Desempeño</h2>", unsafe_allow_html=True)
    
    # Creamos las pestañas de navegación interna
    tab_carga, tab_interna, tab_ficha = st.tabs([
        "📥 Carga Masiva (Google Forms)", 
        "📝 Realizar Evaluación Interna", 
        "📇 Ficha Individual Completa"
    ])
    
    # ==========================================
    # PESTAÑA 1: CARGA MASIVA (EL TRADUCTOR)
    # ==========================================
    with tab_carga:
        st.markdown("### 📤 Importar resultados de Google Forms")
        st.info("Sube el archivo Excel o CSV descargado de tu formulario. El sistema agrupará las preguntas por competencia y calculará los promedios.")
        
        col1, col2 = st.columns(2)
        with col1:
            periodo_sel = st.selectbox("📅 Selecciona el Periodo:", ["2025-I", "2025-II", "2026-I"])
        with col2:
            tipo_eval_sel = st.selectbox("🏷️ Tipo de Evaluación:", ["Competencias Generales", "Competencias Específicas", "KPIs"])
            
        archivo_subido = st.file_uploader("Sube el archivo CSV o Excel de Google Forms", type=["csv", "xlsx"])
        
        if archivo_subido is not None:
            try:
                # Detectamos si es CSV o Excel
                if archivo_subido.name.endswith('.csv'):
                    try:
                        # La magia: sep=None y engine='python' adivina automáticamente el separador
                        df_raw = pd.read_csv(archivo_subido, sep=None, engine='python', encoding='utf-8')
                    except UnicodeDecodeError:
                        archivo_subido.seek(0)
                        df_raw = pd.read_csv(archivo_subido, sep=None, engine='python', encoding='latin-1')
                elif archivo_subido.name.endswith('.xlsx'):
                    # Si subes el Excel directo, nos evitamos todos los problemas de comas
                    df_raw = pd.read_excel(archivo_subido)
                
                st.success("✅ Archivo leído correctamente. Vista previa de los datos crudos:")
                st.dataframe(df_raw.head(3))
                
                st.markdown("#### ⚙️ Configuración del Traductor")
                # Le preguntamos al usuario qué columna tiene el nombre o DNI
                col_identificador = st.selectbox("1️⃣ ¿Qué columna contiene el Nombre o DNI del empleado evaluado?", df_raw.columns)
                
                if st.button("🪄 Procesar y Traducir Datos", type="primary"):
                    st.write("Iniciando procesamiento...")
                    
                    # --- AQUÍ VA LA LÓGICA DE TRADUCCIÓN ---
                    # 1. Filtramos las columnas que parecen ser preguntas (tienen corchetes "[" o dos puntos ":")
                    cols_preguntas = [c for c in df_raw.columns if ":" in c or "[" in c]
                    
                    if not cols_preguntas:
                        st.error("No se detectaron columnas con el formato de preguntas de Google Forms (Ej: 'COMPETENCIA: ... [Pregunta]').")
                    else:
                        # Estructura para guardar los resultados
                        resultados = []
                        
                        for index, row in df_raw.iterrows():
                            empleado = row[col_identificador]
                            diccionario_notas = {}
                            
                            for col in cols_preguntas:
                                # Extraemos la competencia (lo que está antes de los dos puntos)
                                competencia = col.split(":")[0].strip().title()
                                valor = row[col]
                                
                                # Limpiamos el valor por si dice "4. Siempre" y lo volvemos número
                                try:
                                    if pd.notna(valor):
                                        nota_num = float(str(valor).split(".")[0]) # Toma el "4" de "4. Siempre"
                                        
                                        if competencia not in diccionario_notas:
                                            diccionario_notas[competencia] = []
                                        diccionario_notas[competencia].append(nota_num)
                                except:
                                    pass # Si no es un número, lo ignoramos
                                    
                            # Calculamos promedios por competencia para este empleado
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
                            
                            resultados.append({
                                "Empleado": empleado,
                                "Periodo": periodo_sel,
                                "Promedio General": round(promedio_general, 2),
                                "Notas Generales (Formato Mágico)": string_final
                            })
                            
                        # Guardamos el resultado en la "memoria" de Streamlit
                        st.session_state['tabla_temporal'] = pd.DataFrame(resultados)
                        
                # --- BOTÓN PARA GUARDAR DEFINITIVAMENTE ---
                if 'tabla_temporal' in st.session_state:
                    st.success("🎉 ¡Datos traducidos exitosamente! Revisa la vista previa y guárdalos.")
                    st.dataframe(st.session_state['tabla_temporal'])
                    
                    if st.button("💾 Guardar Resultados en el Sistema", type="primary"):
                        # Creamos la tabla EVALUACIONES si aún no existe en tu sistema
                        if "EVALUACIONES" not in dfs:
                            dfs["EVALUACIONES"] = pd.DataFrame()
                            
                        # Unimos los datos nuevos con los que ya existían
                        dfs["EVALUACIONES"] = pd.concat([dfs["EVALUACIONES"], st.session_state['tabla_temporal']], ignore_index=True)
                        
                        st.balloons()
                        st.success("✅ ¡Datos guardados exitosamente en la base de datos!")
                        
                        # Limpiamos la memoria
                        del st.session_state['tabla_temporal']
            except Exception as e:
                st.error(f"Hubo un error al procesar el archivo: {e}")

    # ==========================================
    # PESTAÑA 2: EVALUACIÓN INTERNA (Y ENLACES)
    # ==========================================
    with tab_interna:
        st.markdown("### 📝 Formulario de Evaluación Interna")
        st.write("Genera una evaluación manual en el sistema o copia el enlace para enviarlo a un evaluador.")
        # Simulación de buscador de empleados
        df_per = dfs.get("PERSONAL", pd.DataFrame())
        if not df_per.empty:
            lista_emp = df_per["dni"].astype(str) + " - " + df_per.get("nombres", "Empleado")
            emp_a_evaluar = st.selectbox("Selecciona al trabajador a evaluar:", lista_emp)
            st.markdown(f"**🔗 Enlace directo para el evaluador:**")
            st.code(f"https://tu-sistema-gth.streamlit.app/?evaluar={emp_a_evaluar.split(' - ')[0]}&periodo=2025-I")
            st.button("Realizar evaluación en pantalla ahora", type="primary")
        else:
            st.warning("No hay datos de personal cargados.")

    # ==========================================
    # PESTAÑA 3: FICHA INDIVIDUAL (BOLETA DE NOTAS)
    # ==========================================
    with tab_ficha:
        st.markdown("### 📇 Ficha de Evaluación Detallada")
        st.write("Consulta el detalle exacto (pregunta por pregunta) de un trabajador.")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.text_input("🔍 Ingresa el DNI del trabajador:")
        with col_f2:
            st.selectbox("📅 Filtrar por Periodo:", ["Todos", "2025-I", "2025-II"])
        st.info("Aquí mostraremos la vista estilo 'Boleta de Notas'.")

# ==========================================
# MÓDULO: CUMPLEAÑEROS
# ==========================================

import streamlit as st
import pandas as pd
from datetime import date
from io import BytesIO
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

def mostrar(dfs):
    st.markdown("<h2 style='color: #4A0000;'>🎂 Reporte de Cumpleañeros</h2>", unsafe_allow_html=True)
    
    df_per = dfs.get("PERSONAL", pd.DataFrame())
    df_gen = dfs.get("DATOS GENERALES", pd.DataFrame())
    
    if not df_per.empty and not df_gen.empty:
        # BLINDAJE: Limpiar nombres de columnas para evitar espacios ocultos
        df_per.columns = df_per.columns.astype(str).str.strip().str.upper()
        df_gen.columns = df_gen.columns.astype(str).str.strip().str.upper()

        col_fnac = next((c for c in df_gen.columns if "NACIMIENTO" in c and "FECHA" in c), None)
        
        if col_fnac:
            # --- LÓGICA ULTRA SEGURA DE NOMBRES ---
            col_nombres = next((c for c in df_per.columns if "NOMBRE" in c), None)
            col_apellidos = next((c for c in df_per.columns if "APELLIDO" in c), None)
            
            if col_nombres and col_apellidos:
                df_per["Trabajador"] = df_per[col_nombres].astype(str).str.strip() + " " + df_per[col_apellidos].astype(str).str.strip()
            elif col_nombres:
                df_per["Trabajador"] = df_per[col_nombres].astype(str).str.strip()
            else:
                df_per["Trabajador"] = "Nombre no encontrado"
            
            # --- LÓGICA PARA LA FOTO Y CONTACTO ---
            col_foto = next((c for c in df_per.columns if "FOTO" in c), None)
            col_cel = next((c for c in df_gen.columns if any(x in c for x in ["CELULAR", "TELEFONO", "MÓVIL"])), None)
            col_em = next((c for c in df_gen.columns if any(x in c for x in ["CORREO", "EMAIL"])), None)
            col_sede = next((c for c in df_gen.columns if "SEDE" in c), None)
            
            if col_foto: df_per.rename(columns={col_foto: "Foto_URL"}, inplace=True)
            
            cols_per_a_jalar = ["DNI", "Trabajador"]
            if col_foto: cols_per_a_jalar.append("Foto_URL")
            
            df_cumple = df_per[cols_per_a_jalar].copy()
            
            cols_gen_a_jalar = ["DNI", col_fnac]
            if col_sede: cols_gen_a_jalar.append(col_sede)
            if col_cel: cols_gen_a_jalar.append(col_cel)
            if col_em: cols_gen_a_jalar.append(col_em)
            
            df_gen_temp = df_gen[cols_gen_a_jalar].copy()
            
            # Unión segura
            df_cumple = df_cumple.merge(df_gen_temp, on="DNI", how="inner")
            if col_sede:
                df_cumple.rename(columns={col_sede: "SEDE"}, inplace=True)
            else:
                df_cumple["SEDE"] = "No registrada"
            
            df_cumple[col_fnac] = pd.to_datetime(df_cumple[col_fnac], errors="coerce")
            df_cumple = df_cumple.dropna(subset=[col_fnac])
            
            meses = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
            df_cumple["Mes_Num"] = df_cumple[col_fnac].dt.month
            df_cumple["Dia"] = df_cumple[col_fnac].dt.day
            df_cumple["Mes"] = df_cumple["Mes_Num"].map(meses)
            
            año_actual = date.today().year
            df_cumple["Años a cumplir"] = año_actual - df_cumple[col_fnac].dt.year
            df_cumple["Fecha de cumpleaños"] = df_cumple["Dia"].astype(str) + " de " + df_cumple["Mes"]
            
            # --- Filtros ---
            st.markdown("### 🔍 Filtros")
            col1, col2 = st.columns(2)
            with col1:
                sedes_opciones = sorted(df_cumple["SEDE"].unique())
                f_sede = st.multiselect("Sede", options=sedes_opciones)
            with col2:
                f_mes = st.multiselect("Mes", options=list(meses.values()), default=[meses[date.today().month]])
            
            if f_sede: df_cumple = df_cumple[df_cumple["SEDE"].isin(f_sede)]
            if f_mes: df_cumple = df_cumple[df_cumple["Mes"].isin(f_mes)]
            df_cumple = df_cumple.sort_values(["Mes_Num", "Dia"])

            if col_cel: df_cumple.rename(columns={col_cel: "Celular"}, inplace=True)
            if col_em: df_cumple.rename(columns={col_em: "Email"}, inplace=True)

            st.markdown("### ✨ Celebraciones Visuales")
            
            # =========================================================
            # URLs CORREGIDAS PARA QUE COINCIDAN CON TU GITHUB EXACTAMENTE
            # =========================================================
            img_mes_url = "https://raw.githubusercontent.com/agalindoUR/SISTEMA_GTH/main/img_mes_url.png" 
            img_ind_url = "https://raw.githubusercontent.com/agalindoUR/SISTEMA_GTH/main/img_ind_url.jpg"

            nombres_mes = "<br>".join(df_cumple["Trabajador"].tolist()) if not df_cumple.empty else "Nadie este mes"
            
            # HTML de la tarjeta grupal (se mantiene igual, es solo visual)
            html_mes = f"""<div style="position: relative; width: 100%; max-width: 600px; margin: auto;">
<img src="{img_mes_url}" style="width: 100%; border-radius: 15px; box-shadow: 0px 4px 10px rgba(0,0,0,0.2);">
<div style="position: absolute; top: 35%; left: 10%; right: 10%; text-align: center; font-family: sans-serif;">
<p style="font-size: 1.5em; color: white; margin-top: 15px; line-height: 1.5; text-shadow: 2px 2px 4px black;">{nombres_mes}</p>
</div>
</div>"""
            st.markdown(html_mes, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # --- GENERACIÓN DE IMAGEN REAL PARA TARJETAS INDIVIDUALES ---
            if not df_cumple.empty:
                st.info("💡 Haz clic en 'Descargar Tarjeta' para obtener la imagen final lista para enviar por WhatsApp.")
                
                # Función interna para procesar la imagen fusionada
                def crear_imagen_cumple(template_url, foto_url, nombre, fecha):
                    try:
                        # 1. Descargar la plantilla base (fondo rojo)
                        resp_temp = requests.get(template_url)
                        img_base = Image.open(BytesIO(resp_temp.content)).convert("RGBA")
                        
                        # 2. Intentar descargar la foto del trabajador (de Postimages)
                        try:
                            resp_foto = requests.get(foto_url)
                            img_foto = Image.open(BytesIO(resp_foto.content)).convert("RGBA")
                        except:
                            # Si falla, crea un fondo blanco transparente
                            img_foto = Image.new('RGBA', (300, 300), (255, 255, 255, 0))
                        
                        # 3. Recortar foto en círculo y AGRANDARLA
                        # Calibrado para ser grande y visible a la izquierda
                        size = (280, 280) 
                        img_foto = img_foto.resize(size, Image.Resampling.LANCZOS)
                        mask = Image.new('L', size, 0)
                        draw_mask = ImageDraw.Draw(mask)
                        # Crear el círculo de recorte
                        draw_mask.ellipse((0, 0) + size, fill=255)
                        # Aplicar el recorte circular
                        img_circular = ImageOps.fit(img_foto, mask.size, centering=(0.5, 0.5))
                        img_circular.putalpha(mask)
                        
                        # 4. Pegar foto circular en la plantilla (Coordenadas calibradas: 100, 350)
                        # Esto la coloca a la izquierda, flotando al lado del globo
                        img_base.paste(img_circular, (100, 350), img_circular) 
                        
                        # 5. Escribir el texto
                        draw = ImageDraw.Draw(img_base)
                        # Nota: Usamos una fuente por defecto agrandada. 
                        # Para mejor resultado, sube un .ttf a GitHub.
                        fuente_nombre = ImageFont.load_default() 
                        fuente_fecha = ImageFont.load_default()
                        
                        # 6. Coordenadas y estilos calibrados para el texto
                        # NOMBRE (Grande, Dorado/Amarillo, Centrado debajo del título)
                        # fill=(255, 215, 0) es el color dorado Universidad Roosevelt
                        # Tendrás que ajustar la coordenada X para centrarlo según el ancho real
                        draw.text((320, 150), nombre, font=fuente_nombre, fill=(255, 215, 0)) 
                        # FECHA (Mediana, Dorada/Blanca, Centrada debajo del nombre)
                        draw.text((350, 210), fecha, font=fuente_fecha, fill=(255, 215, 0)) 
                        
                        # 7. Convertir a Bytes para descargar
                        img_final = BytesIO()
                        img_base.convert("RGB").save(img_final, format='JPEG', quality=95)
                        return img_final.getvalue()
                    except Exception as e:
                        return None

                # Mostrar las tarjetas y botones de acción
                for _, row in df_cumple.iterrows():
                    foto_trabajador_url = row.get("Foto_URL", "https://raw.githubusercontent.com/agalindoUR/SISTEMA_GTH/main/Logo_guindo.png")
                    if pd.isna(foto_trabajador_url) or str(foto_trabajador_url).strip() == "":
                        foto_trabajador_url = "https://raw.githubusercontent.com/agalindoUR/SISTEMA_GTH/main/Logo_guindo.png"

                    with st.expander(f"🎉 {row['Trabajador']} ({row['Fecha de cumpleaños']})"):
                        with st.spinner('Generando tarjeta...'):
                            imagen_bytes = crear_imagen_cumple(img_ind_url, foto_trabajador_url, row['Trabajador'], row['Fecha de cumpleaños'])
                            
                        if imagen_bytes:
                            # Mostrar la imagen generada en pantalla
                            st.image(imagen_bytes, use_container_width=True)
                            
                            # Botones de acción integrados
                            col_b1, col_b2 = st.columns(2)
                            with col_b1:
                                # Botón para descargar la imagen final
                                st.download_button(
                                    label="📥 Descargar Tarjeta",
                                    data=imagen_bytes,
                                    file_name=f"Cumpleaños_{row['Trabajador']}.jpg",
                                    mime="image/jpeg",
                                    type="primary",
                                    use_container_width=True
                                )
                            with col_b2:
                                # Botón para abrir WhatsApp con el mensaje de texto
                                wa_num = str(row.get("Celular", "")).replace(".0", "").strip()
                                if wa_num and wa_num != "nan":
                                    wa_url = f"https://wa.me/51{wa_num}?text=¡Feliz%20Cumpleaños,%20{row['Trabajador']}!%20🥳%20De%20parte%20de%20todo%20el%20equipo%20de%20la%20Universidad%20Roosevelt,%20esperamos%20que%20pases%20un%20día%20increíble."
                                    st.markdown(f"""<a href="{wa_url}" target="_blank" style="display: block; width: 100%; padding: 10px; background-color: #25D366; color: white; text-align: center; font-weight: bold; border-radius: 8px; text-decoration: none;">📲 Abrir WhatsApp</a>""", unsafe_allow_html=True)
                        else:
                            st.error("Hubo un error al generar la imagen.")

            st.markdown("---")
            
            # Tabla y Exportación a Excel intactas
            st.dataframe(df_cumple[["DNI", "Trabajador", "SEDE", "Fecha de cumpleaños", "Años a cumplir"]], hide_index=True)
            
            output_cump = BytesIO()
            with pd.ExcelWriter(output_cump, engine='openpyxl') as writer:
                df_cumple[["DNI", "Trabajador", "SEDE", "Fecha de cumpleaños", "Años a cumplir"]].to_excel(writer, index=False, sheet_name='Cumpleañeros')
            st.download_button(label="📥 Exportar a Excel", data=output_cump.getvalue(), file_name="Reporte_Cumpleañeros.xlsx", key="btn_exp_cump", type="primary")

        else:
            st.warning("⚠️ No se encontró la columna de 'Fecha de nacimiento'.")
    else:
        st.warning("⚠️ Faltan datos en Personal o Datos Generales.")

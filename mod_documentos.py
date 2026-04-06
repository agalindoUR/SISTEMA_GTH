import streamlit as st
import pandas as pd

def generar_boton_certificado(nom_c, dni_buscado, df_contratos, gen_word):
    if not df_contratos.empty:
        st.markdown("""
            <style>
            [data-testid="stDownloadButton"] button { background-color: #FFD700 !important; border: 2px solid #4A0000 !important;}
            [data-testid="stDownloadButton"] button p { color: #4A0000 !important; font-weight: bold !important; font-size: 16px !important; }
            [data-testid="stDownloadButton"] button:hover { background-color: #ffffff !important; border: 2px solid #FFD700 !important; }
            </style>
        """, unsafe_allow_html=True)
        # Invocamos la función de crear Word que ya tienes en tu app.py
        word_file = gen_word(nom_c, dni_buscado, df_contratos)
        st.download_button("📄 Generar Certificado de Trabajo", data=word_file, file_name=f"Certificado_{dni_buscado}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        st.markdown("<br>", unsafe_allow_html=True)

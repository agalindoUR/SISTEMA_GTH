# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import date
from io import BytesIO
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# =========================================================
# --- 1. CONFIGURACIÓN, CONSTANTES Y DATOS DEL FIRMANTE ---
# =========================================================
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
# --- 2. FUNCIONES DE BASE DE DATOS (EXCEL) ---
# =========================================================
def load_data():
    if not os.path.exists(DB):
        with pd.ExcelWriter(DB) as w:
            for h, cols in COLUMNAS.items(): pd.DataFrame(columns=cols).to_excel(w, sheet_name=h, index=False)
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

# =========================================================
# --- 3. FUNCIÓN GENERADORA DEL CERTIFICADO (WORD) ---
# =========================================================
def gen_word(nom, dni, df_c):
    doc = Document()
    section = doc.sections[0]
    section.page_height = Inches(11.69); section.page_width = Inches(8.27)
    section.top_margin = Inches(1.6); section.bottom_margin = Inches(1.2)
    section.left_margin = Inches(1.0); section.right_margin = Inches(1.0)

    header = section.header
    section.header_distance = Inches(0)
    if os.path.exists("header.png"):
        p_h = header.paragraphs[0]
        p_h.paragraph_format.left_indent = Inches(-1.0) 
        p_h.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_h.add_run().add_picture("header.png", width=Inches(8.27))

    footer = section.footer
    section.footer_distance = Inches(0)
    if os.path.exists("footer.png"):
        p_f = footer.paragraphs[0]
        p_f.paragraph_format.left_indent = Inches(-1.0)
        p_f.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_f.add_run().add_picture("footer.png", width=Inches(8.27))

    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_tit = p_tit.add_run("CERTIFICADO DE TRABAJO")
    r_tit.bold = True; r_tit.font.name = 'Arial'; r_tit.font.size = Pt(24)

    doc.add_paragraph("\n" + TEXTO_CERT).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_inf = doc.add_paragraph()
    p_inf.add_run("El TRABAJADOR ").bold = False
    p_inf.add_run(nom).bold = True
    p_inf.add_run(f", identificado con DNI N° {dni}, laboró bajo el siguiente detalle:")

    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    t = doc.add_table(rows=1, cols=3); t.style = 'Table Grid'; t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for i, h in enumerate(["CARGO", "FECHA INICIO", "FECHA FIN"]):
        cell = t.rows[0].cells[i]; r = cell.paragraphs[0].add_run(h); r.bold = True
        shd = OxmlElement('w:shd'); shd.set(qn('w:fill'), 'E1EFFF'); cell._tc.get_or_add_tcPr().append(shd)

    for _, fila in df_c.iterrows():
        celdas = t.add_row().cells
        celdas[0].text = str(fila.get('cargo', ''))
        celdas[1].text = pd.to_datetime(fila.get('f_inicio')).strftime('%d/%m/%Y') if pd.notnull(fila.get('f_inicio')) else ""
        celdas[2].text = pd.to_datetime(fila.get('f_fin')).strftime('%d/%m/%Y') if pd.notnull(fila.get('f_fin')) else ""

    doc.add_paragraph("\n\nHuancayo, " + date.today().strftime("%d/%m/%Y")).alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f = doc.add_paragraph(); f.alignment = WD_ALIGN_PARAGRAPH.CENTER
    # LÍNEA CORREGIDA ABAJO (119):
    f.add_run("\n\n__________________________\n" + str(F_N) + "\n" + str(F_C)).bold = True

    buf = BytesIO(); doc.save(buf); buf.seek(0)

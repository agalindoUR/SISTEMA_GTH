def gen_word(nom, dni, df_c):
    doc = Document()
    
    # 1. CONFIGURACIÓN DE PÁGINA A4
    section = doc.sections[0]
    section.page_height = Inches(11.69)
    section.page_width = Inches(8.27)
    
    # Márgenes para el TEXTO (ajustados para no chocar con las imágenes)
    section.top_margin = Inches(1.6)
    section.bottom_margin = Inches(1.2)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

    # 2. ENCABEZADO (Estirado a los bordes)
    header = section.header
    section.header_distance = Inches(0)
    if os.path.exists("header.png"):
        p_h = header.paragraphs[0]
        # Anulamos el margen izquierdo del encabezado
        p_h.paragraph_format.left_indent = Inches(-1.0) 
        p_h.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run_h = p_h.add_run()
        # 8.27 es el ancho exacto del papel A4
        run_h.add_picture("header.png", width=Inches(8.27))

    # 3. PIE DE PÁGINA (Estirado a los bordes)
    footer = section.footer
    section.footer_distance = Inches(0)
    if os.path.exists("footer.png"):
        p_f = footer.paragraphs[0]
        # Anulamos el margen izquierdo del pie de página
        p_f.paragraph_format.left_indent = Inches(-1.0)
        p_f.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run_f = p_f.add_run()
        run_f.add_picture("footer.png", width=Inches(8.27))

    # 4. CUERPO DEL DOCUMENTO
    # Título
    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_tit = p_tit.add_run("CERTIFICADO DE TRABAJO")
    r_tit.bold = True
    r_tit.font.name = 'Arial'
    r_tit.font.size = Pt(24)

    # Texto principal
    doc.add_paragraph("\n" + TEXTO_CERT).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    p_inf = doc.add_paragraph()
    p_inf.add_run("El TRABAJADOR ").bold = False
    p_inf.add_run(nom).bold = True
    p_inf.add_run(f", identificado con DNI N° {dni}, laboró bajo el siguiente detalle:")

    # 5. TABLA CON CABECERA CELESTE
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    t = doc.add_table(rows=1, cols=3)
    t.style = 'Table Grid'
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    for i, h in enumerate(["CARGO", "FECHA INICIO", "FECHA FIN"]):
        cell = t.rows[0].cells[i]
        r = cell.paragraphs[0].add_run(h)
        r.bold = True
        # Fondo celeste suave
        shd = OxmlElement('w:shd')
        shd.set(qn('w:fill'), 'E1EFFF')
        cell._tc.get_or_add_tcPr().append(shd)

    for _, fila in df_c.iterrows():
        celdas = t.add_row().cells
        celdas[0].text = str(fila.get('cargo', ''))
        celdas[1].text = pd.to_datetime(fila.get('f_inicio')).strftime('%d/%m/%Y') if pd.notnull(fila.get('f_inicio')) else ""
        celdas[2].text = pd.to_datetime(fila.get('f_fin')).strftime('%d/%m/%Y') if pd.notnull(fila.get('f_fin')) else ""

    # 6. FIRMA Y CIERRE
    doc.add_paragraph("\n\nHuancayo, " + date.today().strftime("%d/%m/%Y")).alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    f = doc.add_paragraph()
    f.alignment = WD_ALIGN_PARAGRAPH.CENTER
    f.add_run("\n\n__________________________\n" + F_N + "\n" + F_C).bold = True

    # Generación del archivo
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

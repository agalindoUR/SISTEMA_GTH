import gspread
import pandas as pd

NOMBRE_LIBRO = "Asistencia_2026"  # Nombre de tu archivo en Google Drive
NOMBRE_PESTANA = "Asistencia_Diaria"
ARCHIVO_CREDENCIALES = "credenciales.json"


def exportar_df_a_sheets(df_evaluado):
    """Toma el DataFrame evaluado por Streamlit y lo sube/anexa a Google Sheets."""
    if df_evaluado is None or df_evaluado.empty:
        return False, "El reporte a guardar está vacío."

    try:
        # 1. Autenticación con Google Sheets
        gc = gspread.service_account(filename=ARCHIVO_CREDENCIALES)
        libro = gc.open(NOMBRE_LIBRO)

        try:
            hoja = libro.worksheet(NOMBRE_PESTANA)
        except gspread.WorksheetNotFound:
            # Si no existe la pestaña, la crea con los encabezados del DataFrame
            hoja = libro.add_worksheet(
                title=NOMBRE_PESTANA, rows="10000", cols="20"
            )
            encabezados = [str(col) for col in df_evaluado.columns]
            hoja.append_row(encabezados, value_input_option="USER_ENTERED")

        # 2. Limpieza de datos (reemplazar NaN/None por texto vacío)
        df_clean = df_evaluado.fillna("")

        # Convertir todo a string para evitar errores de serialización JSON
        filas = df_clean.astype(str).values.tolist()

        # 3. Subida masiva en lote (batch upload)
        if filas:
            hoja.append_rows(filas, value_input_option="USER_ENTERED")

        return (
            True,
            f"Se exportaron con éxito {len(filas)} filas a Google Sheets.",
        )

    except Exception as e:
        return False, f"Error de conexión con Google Sheets: {str(e)}"

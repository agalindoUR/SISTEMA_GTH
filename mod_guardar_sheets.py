import gspread
import pandas as pd
import streamlit as st

NOMBRE_LIBRO_DEFAULT = "Asistencia_2026"  # Nombre predeterminado de la hoja en Drive
ARCHIVO_CREDENCIALES = "credenciales.json"


def obtener_cliente_gspread():
    """Conecta con Google Sheets usando Streamlit Secrets (en la nube)

    o 'credenciales.json' (en desarrollo local).
    """
    try:
        # 1. Intenta autenticar usando secretos de Streamlit Cloud (Recomendado)
        if "gcp_service_account" in st.secrets:
            return gspread.service_account_from_dict(
                st.secrets["gcp_service_account"]
            )
        # 2. Si no hay secretos, busca el archivo local
        return gspread.service_account(filename=ARCHIVO_CREDENCIALES)
    except Exception as e:
        raise Exception(f"No se pudo autenticar con Google: {str(e)}")


def cargar_df_desde_sheets(
    nombre_pestana, nombre_libro=NOMBRE_LIBRO_DEFAULT
):
    """Lee una pestaña de Google Sheets y la retorna como un DataFrame de Pandas."""
    try:
        gc = obtener_cliente_gspread()
        libro = gc.open(nombre_libro)
        hoja = libro.worksheet(nombre_pestana)

        datos = hoja.get_all_records()
        return pd.DataFrame(datos)
    except gspread.WorksheetNotFound:
        # Si la pestaña no existe aún, retorna DataFrame vacío
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al cargar '{nombre_pestana}': {str(e)}")
        return pd.DataFrame()


def exportar_df_a_sheets(
    df_evaluado,
    nombre_pestana="ASISTENCIA_PROCESADA",
    modo="anexar",
    nombre_libro=NOMBRE_LIBRO_DEFAULT,
):
    """Sube datos a Google Sheets.

    - modo='anexar': Agrega filas al final de la tabla (para registros de asistencia/regularización).
    - modo='sobrescribir': Reemplaza todo el contenido de la pestaña (para actualizar horarios o tablas maestras).
    """
    if df_evaluado is None or df_evaluado.empty:
        return False, "El reporte a guardar está vacío."

    try:
        gc = obtener_cliente_gspread()
        libro = gc.open(nombre_libro)

        # Buscar pestaña o crearla si no existe
        try:
            hoja = libro.worksheet(nombre_pestana)
        except gspread.WorksheetNotFound:
            hoja = libro.add_worksheet(
                title=nombre_pestana, rows=10000, cols=25
            )
            encabezados = [str(col) for col in df_evaluado.columns]
            hoja.append_row(encabezados, value_input_option="USER_ENTERED")

        # Limpieza de valores nulos o incompatibles
        df_clean = df_evaluado.fillna("")
        filas = df_clean.astype(str).values.tolist()

        if modo == "sobrescribir":
            hoja.clear()
            encabezados = [str(col) for col in df_clean.columns]
            hoja.update(
                [encabezados] + filas, value_input_option="USER_ENTERED"
            )
            msg = f"Se actualizaron {len(filas)} filas en '{nombre_pestana}'."
        else:  # modo 'anexar'
            if filas:
                hoja.append_rows(filas, value_input_option="USER_ENTERED")
            msg = f"Se anexaron {len(filas)} filas en '{nombre_pestana}'."

        return True, msg

    except Exception as e:
        return False, f"Error de conexión con Google Sheets: {str(e)}"

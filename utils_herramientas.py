import pandas as pd
from datetime import datetime, date

def obtener_lista(dfs, nombre_hoja, columna):
    """Obtiene una lista limpia y sin duplicados de una columna en hojas de parámetros."""
    try:
        df_params = dfs.get(nombre_hoja, pd.DataFrame())
        if columna in df_params.columns:
            # Limpieza básica: quitar nulos, espacios extra y convertir a mayúsculas
            lista = df_params[columna].dropna().astype(str).str.strip().str.upper().unique().tolist()
            return sorted(lista)
        return []
    except Exception:
        return []

def calcular_edad(fecha_nacimiento):
    """Calcula la edad exacta basada en la fecha de nacimiento."""
    if pd.isna(fecha_nacimiento) or not isinstance(fecha_nacimiento, (datetime, date)):
        return 0
    hoy = date.today()
    return hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))

def evaluar_estado_contrato(fecha_fin):
    """Evalúa si un contrato está ACTIVO o CESADO comparando con la fecha actual."""
    if pd.isna(fecha_fin):
        return "ACTIVO" # Si no hay fecha de fin, se asume activo
    
    # Asegurar que fecha_fin sea un objeto date para la comparación
    if isinstance(fecha_fin, datetime):
        fecha_fin = fecha_fin.date()
        
    return "ACTIVO" if fecha_fin >= date.today() else "CESADO"

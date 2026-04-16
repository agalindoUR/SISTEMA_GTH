import streamlit as st
import mysql.connector
import pandas as pd

# 1. Conexión a la base de datos de XAMPP
def init_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="sistema_asistencia1"
    )

# 2. Función para obtener los datos cruzados
@st.cache_data(ttl=10) # Se actualiza cada 10 segundos
def get_asistencia_data():
    conn = init_connection()
    
    query = """
    SELECT 
        e.dni AS 'DNI', 
        CONCAT(e.nombres, ' ', e.apellidos) AS 'Empleado', 
        e.area AS 'Área',
        r.fecha AS 'Fecha', 
        r.hora AS 'Hora Marcación', 
        r.tipo_registro AS 'Tipo'
    FROM registros_asistencia r
    JOIN empleados e ON r.empleado_id = e.id
    ORDER BY r.fecha DESC, r.hora DESC
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# 3. Interfaz Visual
st.set_page_config(page_title="Monitor de Asistencia", page_icon="⏱️", layout="wide")

st.title("⏱️ Monitor de Asistencia en Tiempo Real")
st.markdown("Datos conectados directamente desde el servidor local (XAMPP)")

try:
    df_asistencia = get_asistencia_data()
    
    col1, col2 = st.columns(2)
    col1.metric("Total de Marcaciones Registradas", len(df_asistencia))
    col2.metric("Última actualización", pd.Timestamp.now().strftime("%H:%M:%S"))
    
    if st.button("🔄 Refrescar Datos Ahora"):
        st.cache_data.clear()
        st.rerun()
        
    st.dataframe(df_asistencia, use_container_width=True)

except Exception as e:
    st.error(f"⚠️ Error al conectar: {e}")
    st.info("Revisa que XAMPP esté encendido.")

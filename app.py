# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import date
from io import BytesIO
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. CONFIGURACIÓN Y CONSTANTES ---
DB = "DB_SISTEMA_GTH.xlsx"
F_N = "MG. ARTURO JAVIER GALINDO MARTINEZ"  # Nombre del que firma
F_C = "JEFE DE GESTIÓN DEL TALENTO HUMANO"  # Cargo del que firma
TEXTO_CERT = "LA OFICINA DE GESTIÓN DE TALENTO HUMANO DE LA UNIVERSIDAD PRIVADA DE HUANCAYO “FRANKLIN ROOSEVELT”, CERTIFICA QUE:"

# --- ESTILOS CSS CORREGIDOS ---
st.markdown("""
<style>
    /* 1. FONDO GENERAL */
    .stApp { background-color: #4a0000 !important; }

    /* 2. SIDEBAR */
    [data-testid="stSidebar"] { background-color: #4a0000 !important; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:first-child {
        background-color: #FFD700 !important;
        width: 140px !important; height: 140px !important;
        margin: 20px auto !important; border-radius: 15px !important;
        display: flex !important; justify-content: center !important; align-items: center !important;
        padding: 10px !important;
    }

    /* 3. ENCABEZADOS DE TABLAS ESTÁTICAS (st.table) */
    thead tr th {
        background-color: #FFF9C4 !important;
        color: #4a0000 !important;
        font-weight: bold !important;
        text-transform: uppercase !important;
    }

    /* 4. ENCABEZADOS DE CONTRATOS (st.data_editor) */
    [data-testid="stDataEditor"] div[data-testid="styledHeaderCell"] {
        background-color: #FFF9C4 !important;
    }
    [data-testid="stDataEditor"] [data-testid="styledHeaderCell"] span {
        color: #4a0000 !important;
        font-weight: bold !important;
    }

    /* 5. TEXTO DE BIENVENIDA EN LOGIN (Blanco para legibilidad) */
    .login-welcome {
        color: #FFFFFF !important;
        text-align: center;
        font-weight: bold;
        margin-top: 15px;
        display: block;
    }

    /* 6. FRASE MOTIVADORA (Dorada y centrada) */
    .frase-talento {
        text-align: center;
        color: #FFD700 !important;
        font-style: italic;
        font-size: 1.5rem;
        margin-top: 25px;
        margin-bottom: 20px;
        display: block;
    }

    /* 7. BOTONES DORADOS */
    div.stButton > button {
        background-color: #FFD700 !important;
        color: #4a0000 !important;
        border-radius: 10px !important;
        font-weight: bold !important;
    }
</style>
""", unsafe_allow_html=True)
# ==========================================
# 4. LÓGICA DE DATOS Y SESIÓN
# ==========================================
if "rol" not in st.session_state:
    st.session_state.rol = None

# --- FLUJO DE PANTALLAS ---
if st.session_state.rol is None:
    # Mostramos la frase motivadora SOLO AQUÍ para que no se duplique
    st.markdown('<p class="frase-talento">¡Tu talento es importante! :)</p>', unsafe_allow_html=True)
    
    col_l1, col_l2, col_l3 = st.columns([1, 1.2, 1])
    with col_l2:
        if os.path.exists("Logo_amarillo.png"):
            st.image("Logo_amarillo.png")
            
        u = st.text_input("USUARIO").lower().strip()
        p = st.text_input("CONTRASEÑA", type="password")
        
        # Bienvenida con clase CSS corregida
        st.markdown('<p class="login-welcome">Bienvenido (a) al sistema de gestión de datos de los colaboradores</p>', unsafe_allow_html=True)
        
        if st.button("INGRESAR"):
            if u == "admin": 
                st.session_state.rol = "Admin"
                st.rerun()
            elif (u == "lector" or u == "supervisor") and p == "123":
                st.session_state.rol = u.title()
                st.rerun()
            else:
                st.error("Credenciales incorrectas")

else:
    # Aquí empieza todo el sistema principal (Carga de datos, Sidebar, Tabs)
    dfs = load_data()
    # ... resto de tu código de consulta ...

    /* 1. FONDO GENERAL DEL SISTEMA */
    .stApp { 
        background-color: #4a0000 !important; 
    }

    /* 2. SIDEBAR - Fondo Guindo y Alineación */
    [data-testid="stSidebar"] {
        background-color: #4a0000 !important;
        display: flex;
        flex-direction: column;
        align-items: center;
    }

    /* 3. EL CUADRADO AMARILLO DEL LOGO (Centrado) */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:first-child {
        background-color: #FFD700 !important;
        width: 140px !important;
        height: 140px !important;
        margin: 20px auto !important;
        border-radius: 15px !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        padding: 10px !important;
    }

    /* Ajuste del logo para que no se deforme */
    [data-testid="stSidebar"] img {
        max-width: 100% !important;
        max-height: 100% !important;
        object-fit: contain !important;
    }

    /* 4. TEXTOS DEL MENÚ Y ETIQUETAS */
    [data-testid="stSidebar"] h3, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] p {
        color: #FFD700 !important;
        font-weight: bold !important;
        text-align: left !important;
    }

    /* 5. TABLAS Y EDITORES - Cuerpo Blanco */
    [data-testid="stDataEditor"], [data-testid="stTable"], .stTable {
        background-color: white !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }

    /* 6. ENCABEZADO DE TABLAS - AMARILLO PASTEL SUAVE */
    thead tr th {
        background-color: #FFF9C4 !important; /* Tono pastel suave */
        color: #4a0000 !important;           /* Texto guindo */
        font-weight: bold !important;
        text-transform: uppercase !important;
        border: 1px solid #f0f0f0 !important;
    }

    /* 7. BOTÓN CERRAR SESIÓN */
    [data-testid="stSidebar"] div.stButton > button {
        background-color: #FFD700 !important;
        color: #4a0000 !important;
        border-radius: 10px !important;
        border: 2px solid #FFFFFF !important;
        font-weight: bold !important;
        font-size: 16px !important;
        width: 100% !important;
        height: 45px !important;
    }

    /* 8. COLORES DE LA PANTALLA DE LOGIN */
    .stApp h1, .stApp h2, .stApp h3 {
        color: #FFD700 !important;
    }

    .stApp label p {
        color: #FFFFFF !important;
        font-weight: bold !important;
    }

    .stApp input {
        background-color: #ffffff !important;
        color: #4a0000 !important;
        border: 2px solid #FFD700 !important;
    }

    /* Frase motivadora centrada */
    .frase-talento {
        width: 100% !important;
        text-align: center !important;
        color: #FFD700 !important;
        font-style: italic !important;
        font-size: 1.3rem !important;
        margin-top: 25px !important;
        display: block !important;
    }
    /* 9. SELECTORES PARA ST.DATA_EDITOR (CONTRATOS) */
    
    /* Fondo amarillo pastel para las celdas del encabezado */
    [data-testid="stDataEditor"] div[data-testid="styledHeaderCell"] {
        background-color: #FFF9C4 !important;
        border-bottom: 1px solid #f0f0f0 !important;
    }

    /* Color de texto guindo y negrita para los títulos de las columnas */
    [data-testid="stDataEditor"] [data-testid="styledHeaderCell"] span {
        color: #4a0000 !important;
        font-weight: bold !important;
        text-transform: uppercase !important;
    }

    /* Colorea la esquina superior izquierda y el área de encabezado del editor */
    [data-testid="stCanvasDataFrame"] > div:first-child {
        background-color: #FFF9C4 !important;
    }

    /* Selector adicional para asegurar que las cabeceras se pinten en versiones nuevas */
    [data-testid="stDataEditor"] .react-grid-HeaderCell {
        background-color: #FFF9C4 !important;
    }
</style>
""", unsafe_allow_html=True)

if "rol" not in st.session_state:
    st.session_state.rol = None


if st.session_state.rol is None:

    st.markdown('<p class="login-welcome"> ¡Tu talento es importante! :)</p>', unsafe_allow_html=True)

    col_logo1, col_logo2, col_logo3 = st.columns([1, 1.2, 1])
    with col_logo2:
        if os.path.exists("Logo_amarillo.png"):
            st.image("Logo_amarillo.png", use_container_width=True)
        else:
            st.warning("No se encontró el archivo Logo_amarillo.png")

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        u = st.text_input("USUARIO")
        p = st.text_input("CONTRASEÑA", type="password")

        st.markdown(
            '<p class="login-welcome">Bienvenido (a) al sistema de gestión de datos de los colaboradores</p>',
            unsafe_allow_html=True
        )

        if st.button("INGRESAR"):
            u_low = u.lower().strip()

            if u_low == "admin":
                st.session_state.rol = "Admin"
            elif u_low == "supervisor" and p == "123":
                st.session_state.rol = "Supervisor"
            elif u_low == "lector" and p == "123":
                st.session_state.rol = "Lector"
            else:
                st.error("Credenciales incorrectas")

            if st.session_state.rol:
                st.rerun()

else:

    dfs = load_data()
    es_lector = st.session_state.rol == "Lector"

    with st.sidebar:

        col_s1, col_s2 = st.columns([1, 0.2])
        with col_s1:
            if os.path.exists("Logo_guindo.png"):
                st.image("Logo_guindo.png", use_container_width=True)

                st.markdown("### 🛠️ MENÚ PRINCIPAL")
                m = st.radio("", ["🔍 Consulta", "➕ Registro", "📊 Nómina General"], key="menu_p_unico")

                st.markdown("### 📈 REPORTES")
                r = st.radio("", ["Vencimientos", "Vacaciones", "Estadísticas"], key="menu_r_unico")

                st.markdown("---")

        if st.button("🚪 Cerrar Sesión", key="btn_logout"):
            st.session_state.rol = None
            st.rerun()

    col_m1, col_m2, col_m3 = st.columns([1.5, 1, 1.5])
    with col_m2:
        if os.path.exists("Logo_amarillo.png"):
            st.image("Logo_amarillo.png", use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

# --- CONTENIDO POR SECCIÓN ---

    if m == "🔍 Consulta":
        st.markdown("<h2 style='color: #FFD700;'>Búsqueda de Colaborador</h2>", unsafe_allow_html=True)
        
        dni_b = st.text_input("Ingrese DNI para consultar:").strip()

        if dni_b:
            pers = dfs["PERSONAL"][dfs["PERSONAL"]["dni"] == dni_b]

            if not pers.empty:
                nom_c = pers.iloc[0]["apellidos y nombres"]

                # SOLUCIÓN AL DUPLICADO: Usamos solo un título estilizado
                st.markdown(f"""
                    <div style='border-bottom: 2px solid #FFD700; padding-bottom: 10px; margin-bottom: 20px;'>
                        <h1 style='color: white; margin: 0;'>👤 {nom_c}</h1>
                    </div>
                """, unsafe_allow_html=True)

                t_noms = [
                    "Datos Generales", "Exp. Laboral", "Form. Académica",
                    "Investigación", "Datos Familiares", "Contratos",
                    "Vacaciones", "Otros Beneficios", "Méritos/Demer.",
                    "Evaluación", "Liquidaciones"
                ]

                h_keys = [
                    "DATOS GENERALES", "EXP. LABORAL", "FORM. ACADEMICA",
                    "INVESTIGACION", "DATOS FAMILIARES", "CONTRATOS",
                    "VACACIONES", "OTROS BENEFICIOS", "MERITOS Y DEMERITOS",
                    "EVALUACION DEL DESEMPEÑO", "LIQUIDACIONES"
                ]

                tabs = st.tabs(t_noms)

                for i, tab in enumerate(tabs):
                    h_name = h_keys[i]
                    with tab:
                        # Filtrado de datos por DNI
                        if "dni" in dfs[h_name].columns:
                            c_df = dfs[h_name][dfs[h_name]["dni"] == dni_b]
                        else:
                            c_df = pd.DataFrame(columns=COLUMNAS[h_name])

                        if h_name == "CONTRATOS":
    # 1. Copiamos y preparamos columnas en mayúsculas
                            vst = c_df.copy()
                            vst.columns = [col.upper() for col in vst.columns] # Cabeceras Mayúsculas
                            vst.insert(0, "SEL", False) # Columna de selección en mayúsculas

    # 2. El editor de datos SIN el índice de la izquierda
                            ed = st.data_editor(
                                vst,
                                hide_index=True,  # ESTO QUITA LA COLUMNA QUE SOBRA
                                use_container_width=True,
                                key=f"ed_{h_name}"
                            )

                            sel = ed[ed["SEL"] == True]

                            if not es_lector:
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    with st.expander("➕ Nuevo Contrato"):
                                        with st.form("f_add"):
                                            car = st.text_input("Cargo")
                                            sue = st.number_input("Sueldo", 0.0)
                                            ini = st.date_input("Inicio")
                                            fin = st.date_input("Fin")
                                            est_a = "ACTIVO" if fin >= date.today() else "CESADO"
                                            mot_a = st.selectbox("Motivo Cese", ["Vigente"] + MOTIVOS_CESE) if est_a == "CESADO" else "Vigente"

                                            if st.form_submit_button("Guardar Contrato"):
                                                nid = dfs[h_name]["id"].max() + 1 if not dfs[h_name].empty else 1
                                                new = {"id": nid, "dni": dni_b, "cargo": car, "sueldo": sue, 
                                                       "f_inicio": ini, "f_fin": fin, "estado": est_a, "motivo cese": mot_a}
                                                dfs[h_name] = pd.concat([dfs[h_name], pd.DataFrame([new])], ignore_index=True)
                                                save_data(dfs)
                                                st.rerun()

                                with col_b:
                                    with st.expander("📝 Editar/Eliminar"):
                                        if not sel.empty:
                                            with st.form("f_edit"):
                                                n_car = st.text_input("Cargo", value=sel.iloc[0]["cargo"])
                                                n_fin = st.date_input("Fin", value=pd.to_datetime(sel.iloc[0]["f_fin"]))
                                                est_e = "ACTIVO" if n_fin >= date.today() else "CESADO"
                                                mot_e = st.selectbox("Motivo Cese", MOTIVOS_CESE) if est_e == "CESADO" else "Vigente"

                                                if st.form_submit_button("Actualizar"):
                                                    idx = sel.index[0]
                                                    dfs[h_name].at[idx, "cargo"] = n_car
                                                    dfs[h_name].at[idx, "f_fin"] = n_fin
                                                    dfs[h_name].at[idx, "estado"] = est_e
                                                    dfs[h_name].at[idx, "motivo cese"] = mot_e
                                                    save_data(dfs)
                                                    st.rerun()
                                            
                                            if st.button("🚨 Eliminar Fila Seleccionada"):
                                                dfs[h_name] = dfs[h_name].drop(sel.index)
                                                save_data(dfs)
                                                st.rerun()
                                        else:
                                            st.info("Selecciona una fila en la tabla para editar.")

                        else:
                            # Vista para las demás pestañas
                            c_df_v = c_df.copy()
    
                            # ESTA LÍNEA ES LA QUE CAMBIA LA CABECERA A MAYÚSCULAS:
                            c_df_v.columns = [col.upper() for col in c_df_v.columns]
    
                            # USAMOS st.table PARA QUE EL CSS DEL PASO 1 FUNCIONE
                            st.table(c_df_v)

                            if not es_lector:
                                with st.expander(f"➕ Registrar Nuevo Dato"):
                                    with st.form(f"f_{h_name}"):
                                        new_row = {"dni": dni_b}
                                        cols_f = [c for c in COLUMNAS[h_name] if c not in ["dni", "apellidos y nombres", "edad", "id"]]
                                        
                                        for col in cols_f:
                                            new_row[col] = st.text_input(col.title())

                                        if st.form_submit_button("Confirmar Registro"):
                                            dfs[h_name] = pd.concat([dfs[h_name], pd.DataFrame([new_row])], ignore_index=True)
                                            save_data(dfs)
                                            st.rerun()
            else:
                st.error("DNI no encontrado en la base de datos.")

    elif m == "➕ Registro" and not es_lector:

        with st.form("reg_p"):

            st.write("### Alta de Nuevo Trabajador")

            d = st.text_input("DNI")
            n = st.text_input("Nombres").upper()
            l = st.text_input("Link File")

            if st.form_submit_button("Registrar"):

                if d and n:
                    dfs["PERSONAL"] = pd.concat(
                        [dfs["PERSONAL"], pd.DataFrame([{
                            "dni": d,
                            "apellidos y nombres": n,
                            "link": l
                        }])],
                        ignore_index=True
                    )

                    save_data(dfs)
                    st.success("Registrado correctamente")

    elif m == "📊 Nómina General":
        st.markdown("<h2 style='color: #FFD700;'>👥 Trabajadores registrados en el sistema</h2>", unsafe_allow_html=True)
        
        # 1. Barra de búsqueda
        busqueda = st.text_input("🔍 Buscar por nombre o DNI:").strip().lower()
        df_nom = dfs["PERSONAL"].copy()
        
        if busqueda:
            df_nom = df_nom[
                df_nom['apellidos y nombres'].str.lower().str.contains(busqueda, na=False) | 
                df_nom['dni'].astype(str).str.contains(busqueda, na=False)
            ]

        # 2. Preparación de la tabla
        df_ver = df_nom.copy()
        df_ver.columns = [col.upper() for col in df_ver.columns]
        df_ver.insert(0, "SEL", False) # Columna para seleccionar
        
        # 3. El Editor (AQUÍ ES DONDE SE MUESTRA LA TABLA)
        ed_nom = st.data_editor(
            df_ver,
            hide_index=True, 
            use_container_width=True,
            key="nomina_v3_blanco" 
        )

        # 4. AQUÍ PEGAS EL CÓDIGO DEL BOTÓN ELIMINAR ↓
        filas_sel = ed_nom[ed_nom["SEL"] == True]
        
        if not filas_sel.empty:
            st.markdown("---")
            # El botón aparecerá abajo solo cuando marques un check en la tabla
            if st.button(f"🚨 ELIMINAR {len(filas_sel)} REGISTRO(S)", type="secondary", use_container_width=True):
                dnis = filas_sel["DNI"].astype(str).tolist()
                
                for h in dfs:
                    if 'dni' in dfs[h].columns:
                        dfs[h] = dfs[h][~dfs[h]['dni'].astype(str).isin(dnis)]
                
                save_data(dfs) # Guarda los cambios en tu Excel subido
                st.success("Registros eliminados correctamente del sistema y del Excel.")
                st.rerun()























































































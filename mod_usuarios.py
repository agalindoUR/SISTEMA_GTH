import streamlit as st
import pandas as pd
from datetime import datetime

def mostrar(dfs, save_data):
    # ==========================================
    # LÓGICA DE AUDITORÍA INTEGRADA
    # ==========================================
    # Usaremos esta función si el Admin hace cambios en los propios usuarios
    def log_auditoria(accion, modulo, detalle):
        nuevo_reg = {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "usuario": st.session_state.get("usuario_actual", "Admin"),
            "accion": accion,
            "modulo": modulo,
            "detalle": detalle
        }
        df_aud = dfs.get("AUDITORIA", pd.DataFrame(columns=["fecha", "usuario", "accion", "modulo", "detalle"]))
        dfs["AUDITORIA"] = pd.concat([df_aud, pd.DataFrame([nuevo_reg])], ignore_index=True)

    st.markdown("<h2 style='color: #FFD700;'>Gestión de Usuarios y Seguridad</h2>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["👤 Mi Perfil (Contraseña)", "👥 Administrar Usuarios (Admin)", "📜 Historial de Cambios (Admin)"])
    
    # -------------------------------------------------------------
    # TAB 1: CAMBIAR CONTRASEÑA (Para TODOS los roles)
    # -------------------------------------------------------------
    with tab1:
        st.subheader("Cambiar mi Contraseña")
        with st.form("form_cambio_clave", clear_on_submit=True):
            nueva_clave = st.text_input("Nueva Contraseña", type="password")
            confirmar = st.text_input("Confirmar Contraseña", type="password")
            
            if st.form_submit_button("Actualizar Contraseña", type="primary"):
                if nueva_clave == confirmar and nueva_clave != "":
                    # Buscamos al usuario en el DataFrame
                    idx = dfs["USUARIOS"][dfs["USUARIOS"]["usuario"].astype(str).str.lower() == st.session_state.usuario_actual.lower()].index
                    if len(idx) > 0:
                        dfs["USUARIOS"]["password"] = dfs["USUARIOS"]["password"].astype(object)
                        dfs["USUARIOS"].at[idx[0], "password"] = nueva_clave
                        
                        log_auditoria("UPDATE", "USUARIOS", f"El usuario {st.session_state.usuario_actual} cambió su propia contraseña.")
                        save_data(dfs)
                        st.success("✅ Contraseña actualizada exitosamente.")
                else:
                    st.error("⚠️ Las contraseñas no coinciden o están vacías.")

    # -------------------------------------------------------------
    # BARRERA DE SEGURIDAD PARA ADMIN
    # -------------------------------------------------------------
    if st.session_state.rol != "Admin":
        with tab2:
            st.warning("🚫 No tienes permisos de Administrador para gestionar usuarios.")
        with tab3:
            st.warning("🚫 No tienes permisos de Administrador para ver la auditoría.")
        return

    # -------------------------------------------------------------
    # TAB 2: ADMINISTRAR USUARIOS (Solo Admin)
    # -------------------------------------------------------------
    with tab2:
        df_u = dfs.get("USUARIOS", pd.DataFrame())
        if not df_u.empty:
            st.markdown("### Usuarios Activos e Inactivos")
            # Mostramos contraseñas ocultas con asteriscos por estética
            df_mostrar = df_u.copy()
            df_mostrar["password"] = "********" 
            st.dataframe(df_mostrar[["usuario", "rol", "estado", "password"]], use_container_width=True, hide_index=True)
            
        st.markdown("---")
        with st.expander("➕ Crear / Editar un Usuario"):
            with st.form("form_gestion_usuario", clear_on_submit=True):
                st.info("Si el nombre de usuario ya existe, se actualizarán sus datos. Si no, se creará uno nuevo.")
                u_nom = st.text_input("Nombre de Usuario (Login)").lower().strip()
                u_pass = st.text_input("Contraseña")
                u_rol = st.selectbox("Rol", ["Admin", "Moderador", "Asistente", "Lector"])
                u_est = st.selectbox("Estado", ["Activo", "Inactivo"])
                
                if st.form_submit_button("💾 Guardar / Actualizar Usuario", type="primary"):
                    if not u_nom or not u_pass:
                        st.error("El usuario y contraseña son obligatorios.")
                    else:
                        if u_nom in df_u["usuario"].astype(str).str.lower().values:
                            # Actualizar existente
                            idx = df_u[df_u["usuario"].astype(str).str.lower() == u_nom].index[0]
                            for col in ["password", "rol", "estado"]:
                                dfs["USUARIOS"][col] = dfs["USUARIOS"][col].astype(object)
                            dfs["USUARIOS"].at[idx, "password"] = u_pass
                            dfs["USUARIOS"].at[idx, "rol"] = u_rol
                            dfs["USUARIOS"].at[idx, "estado"] = u_est
                            log_auditoria("UPDATE", "USUARIOS", f"Admin actualizó al usuario: {u_nom} (Rol: {u_rol})")
                            st.success(f"✅ Usuario '{u_nom}' actualizado.")
                        else:
                            # Crear nuevo
                            nuevo = {"usuario": u_nom, "password": u_pass, "rol": u_rol, "estado": u_est}
                            dfs["USUARIOS"] = pd.concat([dfs["USUARIOS"], pd.DataFrame([nuevo])], ignore_index=True)
                            log_auditoria("CREATE", "USUARIOS", f"Admin creó el usuario: {u_nom} (Rol: {u_rol})")
                            st.success(f"✅ Usuario '{u_nom}' creado exitosamente.")
                        
                        save_data(dfs)
                        st.rerun()

    # -------------------------------------------------------------
    # TAB 3: AUDITORÍA (Solo Admin)
    # -------------------------------------------------------------
    with tab3:
        st.markdown("### 📜 Historial de Cambios en el Sistema")
        st.markdown("Aquí puedes ver qué hizo cada usuario, a qué hora y en qué módulo.")
        df_aud = dfs.get("AUDITORIA", pd.DataFrame())
        if not df_aud.empty:
            # Ordenamos para ver lo más reciente arriba
            df_aud_sorted = df_aud.sort_index(ascending=False)
            st.dataframe(df_aud_sorted, use_container_width=True, hide_index=True)
        else:
            st.info("Aún no hay registros en el historial.")

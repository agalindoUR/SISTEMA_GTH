import pandas as pd
from datetime import datetime, timedelta, time


def time_to_seconds(t):
    """Convierte un objeto time u hora en formato HH:MM:SS a segundos desde medianoche."""
    if isinstance(t, str):
        parts = [int(x) for x in t.strip().split(":")]
        return parts[0] * 3600 + parts[1] * 60 + (parts[2] if len(parts) > 2 else 0)
    elif isinstance(t, time):
        return t.hour * 3600 + t.minute * 60 + t.second
    return None


def seconds_to_time_str(sec):
    """Convierte segundos desde medianoche a formato HH:MM:SS."""
    if sec is None:
        return "-"
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def procesar_registros_dia(lista_marcaciones, config_horario):
    """
    Clasifica dinámicamente la lista de marcaciones del día según la configuración
    del horario específico del colaborador para ese día.
    """
    resultado = {
        "ENTRADA_M": "-",
        "SALIDA_M": "-",
        "ENTRADA_T": "-",
        "SALIDA_T": "-",
        "ESTADO": "OK",
        "MINUTOS_SALIDA_ADELANTADA": 0,
    }

    if not lista_marcaciones or config_horario.get("LABORA") != "SI":
        return resultado

    # Convertir marcaciones a segundos y ordenar
    marc_sec = sorted([time_to_seconds(m) for m in lista_marcaciones if time_to_seconds(m) is not None])

    if not marc_sec:
        return resultado

    e1_sec = time_to_seconds(config_horario.get("E1")) if config_horario.get("E1") != "-" else None
    s1_sec = time_to_seconds(config_horario.get("S1")) if config_horario.get("S1") != "-" else None
    e2_sec = time_to_seconds(config_horario.get("E2")) if config_horario.get("E2") != "-" else None
    s2_sec = time_to_seconds(config_horario.get("S2")) if config_horario.get("S2") != "-" else None

    # Caso 1: Horario de Doble Turno (Mañana y Tarde)
    if s1_sec and e2_sec and s2_sec:
        # Separador entre turno mañana y tarde (punto medio entre S1 y E2)
        corte_interturno = (s1_sec + e2_sec) // 2

        # Punto medio para separar Entrada y Salida de cada turno
        corte_m = (e1_sec + s1_sec) // 2 if e1_sec else s1_sec - 3600
        corte_t = (e2_sec + s2_sec) // 2

        m_manana = [m for m in marc_sec if m < corte_interturno]
        m_tarde = [m for m in marc_sec if m >= corte_interturno]

        # Procesar Mañana
        if m_manana:
            e_m = [m for m in m_manana if m <= corte_m]
            s_m = [m for m in m_manana if m > corte_m]
            if e_m:
                resultado["ENTRADA_M"] = seconds_to_time_str(min(e_m))
            if s_m:
                resultado["SALIDA_M"] = seconds_to_time_str(max(s_m))

        # Procesar Tarde
        if m_tarde:
            e_t = [m for m in m_tarde if m <= corte_t]
            s_t = [m for m in m_tarde if m > corte_t]
            if e_t:
                resultado["ENTRADA_T"] = seconds_to_time_str(min(e_t))
            if s_t:
                resultado["SALIDA_T"] = seconds_to_time_str(max(s_t))

    # Caso 2: Horario de Un Solo Turno (Corrido)
    elif s1_sec:
        corte_unico = (e1_sec + s1_sec) // 2 if e1_sec else s1_sec - 3600
        e_m = [m for m in marc_sec if m <= corte_unico]
        s_m = [m for m in marc_sec if m > corte_unico]

        if e_m:
            resultado["ENTRADA_M"] = seconds_to_time_str(min(e_m))
        if s_m:
            resultado["SALIDA_M"] = seconds_to_time_str(max(s_m))

    # --- Cálculo de Minutos de Salida Anticipada (para Descuentos) ---
    min_adelanto = 0
    if resultado["SALIDA_M"] != "-" and s1_sec:
        sal_m_sec = time_to_seconds(resultado["SALIDA_M"])
        if sal_m_sec < s1_sec:
            min_adelanto += int((s1_sec - sal_m_sec) // 60)

    if resultado["SALIDA_T"] != "-" and s2_sec:
        sal_t_sec = time_to_seconds(resultado["SALIDA_T"])
        if sal_t_sec < s2_sec:
            min_adelanto += int((s2_sec - sal_t_sec) // 60)

    resultado["MINUTOS_SALIDA_ADELANTADA"] = min_adelanto

    # Evaluar si falta alguna marcación esperada
    if (e1_sec and resultado["ENTRADA_M"] == "-") or \
       (s1_sec and resultado["SALIDA_M"] == "-") or \
       (e2_sec and resultado["ENTRADA_T"] == "-") or \
       (s2_sec and resultado["SALIDA_T"] == "-"):
        resultado["ESTADO"] = "INCOMPLETO"

    return resultado

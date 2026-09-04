from datetime import time


def time_to_seconds(t):
    """Convierte un objeto time u hora en formato HH:MM:SS a segundos desde medianoche."""
    if t is None or t == "-" or t == "":
        return None
    if isinstance(t, str):
        try:
            parts = [int(x) for x in t.strip().split(":")]
            return (
                parts[0] * 3600
                + parts[1] * 60
                + (parts[2] if len(parts) > 2 else 0)
            )
        except (ValueError, AttributeError):
            return None
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


def _asignar_entrada_salida(marcaciones_sec, sec_inicio, sec_fin):
    """
    Asigna entrada y salida para un turno específico basándose en la cantidad de marcaciones.
    """
    if not marcaciones_sec:
        return None, None

    # Si hay 2 o más marcaciones en el turno, la primera es Entrada y la última Salida
    if len(marcaciones_sec) >= 2:
        return min(marcaciones_sec), max(marcaciones_sec)

    # Si hay solo 1 marcación, se evalúa con respecto al punto medio del turno
    corte = (
        (sec_inicio + sec_fin) // 2
        if (sec_inicio and sec_fin)
        else (sec_fin - 3600 if sec_fin else sec_inicio + 3600)
    )
    un_registro = marcaciones_sec[0]

    if un_registro <= corte:
        return un_registro, None
    else:
        return None, un_registro


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

    # Si no labora ese día, retorna OK directamente
    if config_horario.get("LABORA") != "SI":
        return resultado

    # Filtrar y convertir marcaciones a segundos
    marc_sec = sorted(
        [
            sec
            for m in (lista_marcaciones or [])
            if (sec := time_to_seconds(m)) is not None
        ]
    )

    e1_sec = time_to_seconds(config_horario.get("E1"))
    s1_sec = time_to_seconds(config_horario.get("S1"))
    e2_sec = time_to_seconds(config_horario.get("E2"))
    s2_sec = time_to_seconds(config_horario.get("S2"))

    # Caso 1: Horario de Doble Turno (Mañana y Tarde)
    if s1_sec and e2_sec and s2_sec:
        corte_interturno = (s1_sec + e2_sec) // 2

        m_manana = [m for m in marc_sec if m < corte_interturno]
        m_tarde = [m for m in marc_sec if m >= corte_interturno]

        e_m, s_m = _asignar_entrada_salida(m_manana, e1_sec, s1_sec)
        e_t, s_t = _asignar_entrada_salida(m_tarde, e2_sec, s2_sec)

        if e_m is not None:
            resultado["ENTRADA_M"] = seconds_to_time_str(e_m)
        if s_m is not None:
            resultado["SALIDA_M"] = seconds_to_time_str(s_m)
        if e_t is not None:
            resultado["ENTRADA_T"] = seconds_to_time_str(e_t)
        if s_t is not None:
            resultado["SALIDA_T"] = seconds_to_time_str(s_t)

    # Caso 2: Horario de Un Solo Turno (Corrido)
    elif s1_sec:
        e_m, s_m = _asignar_entrada_salida(marc_sec, e1_sec, s1_sec)
        if e_m is not None:
            resultado["ENTRADA_M"] = seconds_to_time_str(e_m)
        if s_m is not None:
            resultado["SALIDA_M"] = seconds_to_time_str(s_m)

    # --- Cálculo de Minutos de Salida Anticipada ---
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
    if (
        (e1_sec and resultado["ENTRADA_M"] == "-")
        or (s1_sec and resultado["SALIDA_M"] == "-")
        or (e2_sec and resultado["ENTRADA_T"] == "-")
        or (s2_sec and resultado["SALIDA_T"] == "-")
    ):
        resultado["ESTADO"] = "INCOMPLETO"

    return resultado

"""
Utilidades de tiempo para el sistema de control de descansos.
Funciones para manejo de fechas, horas y zonas horarias.
"""

import pytz
from datetime import datetime, timedelta, date
from typing import Tuple, Dict, Any

# Zona horaria del proyecto (Chile/Punta Arenas)
TZ = pytz.timezone('America/Punta_Arenas')

def get_current_time() -> datetime:
    """
    Obtiene la hora actual en la zona horaria del proyecto (Punta Arenas).
    Esta es la función principal usada en app.py
    """
    return datetime.now(TZ)

def calcular_duracion_descanso(inicio_iso: str) -> Tuple[int, str]:
    """
    Calcular duración y tipo de descanso
    
    Args:
        inicio_iso: Tiempo de inicio en formato ISO
    
    Returns:
        Tuple con (duración_minutos, tipo)
    """
    inicio = datetime.fromisoformat(inicio_iso.replace('Z', '+00:00'))
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=pytz.UTC)
    
    fin = get_current_time()
    duracion_minutos = max(1, int((fin - inicio).total_seconds() / 60))
    tipo = 'COMIDA' if duracion_minutos >= 30 else 'DESCANSO'
    
    return duracion_minutos, tipo

def preparar_datos_tiempo_descanso(usuario_id: int, inicio_iso: str, fin_dt: datetime) -> Dict[str, Any]:
    """
    Preparar datos para insertar en la tabla tiempos_descanso
    
    Args:
        usuario_id: ID del usuario
        inicio_iso: Tiempo de inicio en formato ISO
        fin_dt: Tiempo de fin
    
    Returns:
        Dict con los datos preparados
    """
    inicio = datetime.fromisoformat(inicio_iso.replace('Z', '+00:00'))
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=pytz.UTC)
    
    duracion_minutos = max(1, int((fin_dt - inicio).total_seconds() / 60))
    tipo = 'COMIDA' if duracion_minutos >= 30 else 'DESCANSO'
    
    return {
        'usuario_id': usuario_id,
        'tipo': tipo,
        'fecha': inicio.date().isoformat(),
        'inicio': inicio.time().isoformat(),
        'fin': fin_dt.time().isoformat(),
        'duracion_minutos': duracion_minutos
    }

def get_fecha_rango_default(dias: int = 7) -> Tuple[str, str]:
    """
    Obtener rango de fechas por defecto
    
    Args:
        dias: Número de días hacia atrás desde hoy
    
    Returns:
        Tuple con (fecha_inicio, fecha_fin) en formato ISO
    """
    fecha_fin = date.today().isoformat()
    fecha_inicio = (date.today() - timedelta(days=dias)).isoformat()
    return fecha_inicio, fecha_fin

def formatear_fecha_usuario(fecha_iso: str) -> str:
    """
    Formatear fecha para mostrar al usuario
    
    Args:
        fecha_iso: Fecha en formato ISO
    
    Returns:
        Fecha formateada (dd/mm/yyyy)
    """
    try:
        fecha_obj = datetime.fromisoformat(fecha_iso)
        return fecha_obj.strftime('%d/%m/%Y')
    except:
        return fecha_iso

def es_tiempo_excesivo(duracion_minutos: int, tipo: str) -> Tuple[bool, int]:
    """
    Verificar si un descanso tiene tiempo excesivo
    
    Args:
        duracion_minutos: Duración en minutos
        tipo: Tipo de descanso ('DESCANSO' o 'COMIDA')
    
    Returns:
        Tuple con (es_excesivo, minutos_exceso)
    """
    limite = 40 if tipo == 'COMIDA' else 20
    exceso = max(0, duracion_minutos - limite)
    return exceso > 0, exceso

def get_tiempo_restante(inicio_iso: str) -> Tuple[int, str]:
    """
    Calcular tiempo restante para un descanso activo
    
    Args:
        inicio_iso: Tiempo de inicio en formato ISO
    
    Returns:
        Tuple con (tiempo_restante_minutos, tipo_probable)
    """
    inicio = datetime.fromisoformat(inicio_iso.replace('Z', '+00:00'))
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=pytz.UTC)
    
    ahora = get_current_time()
    tiempo_transcurrido = int((ahora - inicio).total_seconds() / 60)
    
    tiempo_maximo = 40 if tiempo_transcurrido >= 20 else 20
    tiempo_restante = max(0, tiempo_maximo - tiempo_transcurrido)
    tipo_probable = 'COMIDA' if tiempo_transcurrido >= 20 else 'DESCANSO'
    
    return tiempo_restante, tipo_probable

def get_current_time_formatted() -> str:
    """
    Obtiene la hora actual formateada para mostrar en la interfaz.
    Formato: 'YYYY-MM-DD HH:MM:SS'
    """
    return get_current_time().strftime('%Y-%m-%d %H:%M:%S')

def format_datetime_for_display(dt: datetime, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Formatea un datetime para mostrar en la interfaz.
    
    Args:
        dt: datetime object
        format_str: Formato de salida (opcional)
        
    Returns:
        str: Fecha y hora formateada
    """
    # Si el datetime no tiene zona horaria, convertir a la zona del proyecto
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.UTC).astimezone(TZ)
    elif dt.tzinfo != TZ:
        dt = dt.astimezone(TZ)
    
    return dt.strftime(format_str)

def format_time_only(dt: datetime) -> str:
    """
    Formatea solo la hora de un datetime.
    
    Args:
        dt: datetime object
        
    Returns:
        str: Hora formateada como 'HH:MM'
    """
    return format_datetime_for_display(dt, '%H:%M')

def parse_iso_datetime_safe(iso_string: str) -> datetime:
    """
    Convierte un string ISO a datetime con manejo robusto.
    
    Args:
        iso_string: String en formato ISO (puede incluir 'Z' al final)
        
    Returns:
        datetime: Objeto datetime con zona horaria UTC
    """
    try:
        # Limpiar el string
        clean_string = iso_string.replace('Z', '+00:00')
        dt = datetime.fromisoformat(clean_string)
        
        # Asegurar que tenga zona horaria UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)
        
        return dt
    except Exception as e:
        print(f"⚠️ Error parseando datetime ISO '{iso_string}': {e}")
        return get_current_time()

def get_date_range_defaults() -> Dict[str, str]:
    """
    Obtiene rangos de fechas por defecto para filtros.
    
    Returns:
        dict: Diccionario con fechas por defecto en formato ISO
    """
    today = date.today()
    
    return {
        'today': today.isoformat(),
        'yesterday': (today - timedelta(days=1)).isoformat(),
        'week_start': (today - timedelta(days=7)).isoformat(),
        'month_start': (today - timedelta(days=30)).isoformat(),
        'year_start': (today - timedelta(days=365)).isoformat()
    }
    tipo_probable = 'COMIDA' if tiempo_transcurrido >= 20 else 'DESCANSO'
    
    return tiempo_restante, tipo_probable

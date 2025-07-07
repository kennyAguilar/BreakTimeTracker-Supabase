"""
Módulo de Gestión de Descansos
==============================

Maneja todas las operaciones relacionadas con descansos activos y registros de tiempo.
"""

import traceback
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date
from db_core import get_client, get_admin_client
from time_utils import get_current_time

def obtener_descanso_activo(usuario_id: str) -> Optional[Dict]:
    """
    Verifica si un usuario tiene un descanso activo
    
    Args:
        usuario_id: ID del usuario
        
    Returns:
        Dict con datos del descanso activo o None si no tiene
    """
    try:
        client = get_client()
        response = client.table('descansos').select('*').eq('usuario_id', usuario_id).execute()
        
        if response.data and len(response.data) > 0:
            print(f"✅ Descanso activo encontrado para usuario: {usuario_id}")
            return response.data[0]
        
        print(f"ℹ️ No hay descanso activo para usuario: {usuario_id}")
        return None
        
    except Exception as e:
        print(f"❌ Error verificando descanso activo: {e}")
        traceback.print_exc()
        return None

def crear_descanso(usuario_id: str, inicio_iso: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    Crea un nuevo descanso activo para un usuario
    
    Args:
        usuario_id: ID del usuario
        inicio_iso: Timestamp de inicio en formato ISO
        
    Returns:
        Tupla (éxito, mensaje, datos_descanso)
    """
    try:
        # Verificar que no tenga descanso activo
        descanso_existente = obtener_descanso_activo(usuario_id)
        if descanso_existente:
            return False, "Usuario ya tiene un descanso activo", None
        
        # Crear nuevo descanso
        admin_client = get_admin_client()
        
        datos_descanso = {
            'usuario_id': usuario_id,
            'inicio': inicio_iso,
            'tipo': 'Pendiente'
        }
        
        response = admin_client.table('descansos').insert(datos_descanso).execute()
        
        if response.data and len(response.data) > 0:
            print(f"✅ Descanso creado para usuario: {usuario_id}")
            return True, "Descanso iniciado exitosamente", response.data[0]
        
        return False, "Error al crear descanso", None
        
    except Exception as e:
        print(f"❌ Error creando descanso: {e}")
        traceback.print_exc()
        return False, f"Error: {str(e)}", None

def obtener_todos_descansos_activos() -> List[Dict]:
    """
    Obtiene todos los descansos activos con información del usuario
    
    Returns:
        Lista de diccionarios con descansos activos
    """
    try:
        client = get_client()
        response = client.table('descansos').select('*').execute()
        
        if response.data:
            print(f"✅ Obtenidos {len(response.data)} descansos activos")
            return response.data
        
        print("ℹ️ No hay descansos activos")
        return []
        
    except Exception as e:
        print(f"❌ Error obteniendo descansos activos: {e}")
        traceback.print_exc()
        return []

def cerrar_descanso(usuario_id: str, tiempo_data: Dict) -> Tuple[bool, str, Optional[Dict]]:
    """
    Cierra un descanso activo y guarda el registro en tiempos_descanso
    
    Args:
        usuario_id: ID del usuario
        tiempo_data: Diccionario con datos del tiempo (inicio, fin, duracion, tipo)
        
    Returns:
        Tupla (éxito, mensaje, datos_tiempo)
    """
    try:
        admin_client = get_admin_client()
        
        # 1. Eliminar de descansos_activos
        response_delete = admin_client.table('descansos_activos').delete().eq('usuario_id', usuario_id).execute()
        print(f"🗑️ Descanso activo eliminado para usuario: {usuario_id}")
        
        # 2. Crear registro en tiempos_descanso
        response_insert = admin_client.table('tiempos_descanso').insert(tiempo_data).execute()
        
        if response_insert.data and len(response_insert.data) > 0:
            print(f"✅ Registro de tiempo guardado para usuario: {usuario_id}")
            return True, "Descanso cerrado exitosamente", response_insert.data[0]
        
        return False, "Error al guardar registro de tiempo", None
        
    except Exception as e:
        print(f"❌ Error cerrando descanso: {e}")
        traceback.print_exc()
        return False, f"Error: {str(e)}", None

def cerrar_descanso_completo(usuario_id: str, descanso_activo: Dict) -> Tuple[bool, str, Optional[Dict]]:
    """
    Función completa para cerrar un descanso con todos los cálculos
    
    Args:
        usuario_id: ID del usuario
        descanso_activo: Datos del descanso activo
        
    Returns:
        Tupla (éxito, mensaje, datos_detalle)
    """
    try:
        print(f"🔄 Iniciando proceso de cierre completo para usuario ID: {usuario_id}")
        print(f"   Descanso a cerrar: ID {descanso_activo['id']}")
        
        # Importar pytz para manejo de zonas horarias
        import pytz
        
        # Zona horaria de Punta Arenas
        tz = pytz.timezone('America/Punta_Arenas')
        
        # Calcular duración
        inicio = datetime.fromisoformat(descanso_activo['inicio'].replace('Z', '+00:00'))
        if inicio.tzinfo is None:
            inicio = inicio.replace(tzinfo=pytz.UTC)
        
        fin = get_current_time()  # Usar hora local
        duracion_minutos = max(1, int((fin - inicio).total_seconds() / 60))  # Mínimo 1 minuto
        tipo = 'COMIDA' if duracion_minutos >= 30 else 'DESCANSO'
        
        print(f"   Duración: {duracion_minutos} min → {tipo}")
        
        # Convertir ambos tiempos a la misma zona horaria (local)
        inicio_local = inicio.astimezone(tz)
        fin_local = fin  # ya está en hora local
        
        print(f"   🕐 Conversión de tiempos:")
        print(f"      Inicio local: {inicio_local}")
        print(f"      Fin local: {fin_local}")
        
        # Preparar datos para guardar
        tiempo_data = {
            'usuario_id': usuario_id,
            'tipo': tipo,
            'fecha': fin_local.date().isoformat(),
            'inicio': inicio_local.time().isoformat(),
            'fin': fin_local.time().isoformat(),
            'duracion_minutos': duracion_minutos
        }
        
        print(f"   💾 Datos a guardar: {tiempo_data}")
        
        # Usar la función básica de cerrar descanso
        success, mensaje, datos = cerrar_descanso(usuario_id, tiempo_data)
        
        if success:
            detalle = {
                'tipo': tipo,
                'duracion_minutos': duracion_minutos,
                'inicio': inicio_local.strftime('%H:%M'),
                'fin': fin_local.strftime('%H:%M'),
                'fecha': fin_local.date().isoformat()
            }
            print(f"   ✅ Descanso cerrado exitosamente")
            return True, mensaje, detalle
        else:
            return False, mensaje, None
            
    except Exception as e:
        print(f"❌ Error en cierre completo de descanso: {e}")
        traceback.print_exc()
        return False, f"Error: {str(e)}", None

def obtener_registros_periodo(fecha_inicio: date, fecha_fin: date, usuario_id: Optional[str] = None) -> List[Dict]:
    """
    Obtiene registros de descansos para un período específico
    
    Args:
        fecha_inicio: Fecha de inicio del período
        fecha_fin: Fecha de fin del período
        usuario_id: ID del usuario (opcional, si no se especifica trae todos)
        
    Returns:
        Lista de registros de descansos
    """
    try:
        client = get_client()
        query = client.table('tiempos_descanso').select('''
            *,
            usuarios (
                id,
                nombre,
                codigo_empleado,
                puesto
            )
        ''').gte('fecha', fecha_inicio.isoformat()).lte('fecha', fecha_fin.isoformat())
        
        if usuario_id:
            query = query.eq('usuario_id', usuario_id)
        
        response = query.order('fecha', desc=True).execute()
        
        if response.data:
            print(f"✅ Obtenidos {len(response.data)} registros para el período")
            return response.data
        
        print("ℹ️ No hay registros para el período especificado")
        return []
        
    except Exception as e:
        print(f"❌ Error obteniendo registros del período: {e}")
        traceback.print_exc()
        return []
```
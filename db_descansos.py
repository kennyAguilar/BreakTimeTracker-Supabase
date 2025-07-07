"""
Módulo de Gestión de Descansos
==============================

Maneja todas las operaciones relacionadas con descansos activos y registros de tiempo.
"""

import traceback
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date
from db_core import get_client, get_admin_client

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

def crear_descanso(usuario_id: str, inicio_iso: str) -> Optional[Dict]:
    """
    Crea un nuevo descanso activo para un usuario
    
    Args:
        usuario_id: ID del usuario
        inicio_iso: Timestamp de inicio en formato ISO
        
    Returns:
        Dict con datos del descanso creado o None si hay error
    """
    try:
        # Verificar que no tenga descanso activo
        descanso_existente = obtener_descanso_activo(usuario_id)
        if descanso_existente:
            print(f"⚠️ Usuario ya tiene descanso activo: ID {descanso_existente['id']}")
            return None
        
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
            return response.data[0]
        
        print(f"❌ Error al crear descanso - Sin datos de respuesta")
        return None
        
    except Exception as e:
        print(f"❌ Error creando descanso: {e}")
        traceback.print_exc()
        return None

def obtener_todos_descansos_activos() -> List[Dict]:
    """
    Obtiene todos los descansos activos del sistema
    
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

def cerrar_descanso(usuario_id: str, descanso_activo: Dict, tiempo_data: Dict) -> Tuple[bool, str, Dict]:
    """
    Cierra un descanso activo y guarda el tiempo en tiempos_descanso
    
    Args:
        usuario_id: ID del usuario
        descanso_activo: Dict con datos del descanso activo
        tiempo_data: Dict con datos del tiempo a guardar
        
    Returns:
        Tuple (success: bool, mensaje: str, detalle: dict)
    """
    try:
        print(f"🔄 Cerrando descanso ID: {descanso_activo['id']} para usuario ID: {usuario_id}")
        
        admin_client = get_admin_client()
        
        # Paso 1: Insertar en tiempos_descanso
        print(f"   📝 Insertando tiempo de descanso...")
        insert_response = admin_client.table('tiempos_descanso').insert(tiempo_data).execute()
        
        if not insert_response.data:
            error_msg = "Error insertando en tiempos_descanso"
            print(f"   ❌ {error_msg}")
            return False, error_msg, {'insert_response': insert_response}
        
        tiempo_id = insert_response.data[0]['id']
        print(f"   ✅ Tiempo insertado con ID: {tiempo_id}")
        
        # Paso 2: Eliminar de descansos
        print(f"   🗑️ Eliminando descanso activo...")
        delete_response = admin_client.table('descansos').delete().eq('id', descanso_activo['id']).execute()
        
        if delete_response.data:
            print(f"   ✅ Descanso eliminado: {len(delete_response.data)} registros")
        else:
            print(f"   ⚠️ ADVERTENCIA: No se confirmó eliminación")

        # Paso 3: Verificación final
        verify_response = admin_client.table('descansos').select("*").eq('usuario_id', usuario_id).execute()
        descansos_restantes = len(verify_response.data)
        print(f"   🔍 Verificación: {descansos_restantes} descansos activos restantes")
        
        tipo = tiempo_data.get('tipo', 'DESCANSO')
        duracion = tiempo_data.get('duracion_minutos', 0)
        success_msg = f"Descanso cerrado: {tipo} de {duracion} min"
        print(f"   ✅ ÉXITO: {success_msg}")
        
        return True, success_msg, {
            'tiempo_id': tiempo_id,
            'tipo': tipo,
            'duracion_minutos': duracion,
            'descansos_restantes': descansos_restantes
        }
        
    except Exception as e:
        error_msg = f"Error cerrando descanso: {str(e)}"
        print(f"   ❌ ERROR CRÍTICO: {error_msg}")
        print(f"   Stack trace: {traceback.format_exc()}")
        return False, error_msg, {'exception': str(e)}

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
                codigo,
                turno
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

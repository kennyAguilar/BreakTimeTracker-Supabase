"""
Módulo de Gestión de Usuarios
============================

Maneja todas las operaciones relacionadas con usuarios en la base de datos.
"""

import traceback
from typing import Dict, List, Optional, Any, Tuple
from db_core import get_client, get_admin_client

def buscar_usuario_por_tarjeta(numero_tarjeta: str) -> Optional[Dict]:
    """
    Busca un usuario por número de tarjeta magnética
    
    Args:
        numero_tarjeta: Número de la tarjeta magnética
        
    Returns:
        Dict con datos del usuario o None si no se encuentra
    """
    try:
        client = get_client()
        response = client.table('usuarios').select('*').eq('tarjeta', numero_tarjeta).execute()
        
        if response.data and len(response.data) > 0:
            print(f"✅ Usuario encontrado por tarjeta: {response.data[0]['nombre']}")
            return response.data[0]
        
        print(f"❌ No se encontró usuario con tarjeta: {numero_tarjeta}")
        return None
        
    except Exception as e:
        print(f"❌ Error buscando usuario por tarjeta: {e}")
        traceback.print_exc()
        return None

def buscar_usuario_por_codigo(codigo_empleado: str) -> Optional[Dict]:
    """
    Busca un usuario por código de empleado
    
    Args:
        codigo_empleado: Código del empleado
        
    Returns:
        Dict con datos del usuario o None si no se encuentra
    """
    try:
        client = get_client()
        response = client.table('usuarios').select('*').eq('codigo', codigo_empleado.upper()).execute()
        
        if response.data and len(response.data) > 0:
            print(f"✅ Usuario encontrado por código: {response.data[0]['nombre']}")
            return response.data[0]
        
        print(f"❌ No se encontró usuario con código: {codigo_empleado}")
        return None
        
    except Exception as e:
        print(f"❌ Error buscando usuario por código: {e}")
        traceback.print_exc()
        return None

def buscar_usuario_inteligente(entrada: str) -> Optional[Dict]:
    """
    Búsqueda inteligente de usuario por tarjeta magnética o código de empleado
    
    Args:
        entrada: Datos de entrada (tarjeta o código)
        
    Returns:
        Dict con datos del usuario o None si no se encuentra
    """
    print(f"🔍 Búsqueda inteligente para: '{entrada}'")
    
    # Intentar primero por tarjeta magnética
    usuario = buscar_usuario_por_tarjeta(entrada)
    if usuario:
        return usuario
    
    # Si no se encuentra, intentar por código de empleado
    usuario = buscar_usuario_por_codigo(entrada)
    if usuario:
        return usuario
    
    print(f"❌ Usuario no encontrado con entrada: '{entrada}'")
    return None

def obtener_todos_los_usuarios() -> List[Dict]:
    """
    Obtiene todos los usuarios registrados
    
    Returns:
        Lista de diccionarios con datos de usuarios
    """
    try:
        client = get_client()
        response = client.table('usuarios').select('*').order('nombre').execute()
        
        if response.data:
            print(f"✅ Obtenidos {len(response.data)} usuarios")
            return response.data
        
        print("ℹ️ No hay usuarios registrados")
        return []
        
    except Exception as e:
        print(f"❌ Error obteniendo usuarios: {e}")
        traceback.print_exc()
        return []

def obtener_usuario_por_id(usuario_id: str) -> Optional[Dict]:
    """
    Obtiene un usuario específico por su ID
    
    Args:
        usuario_id: ID del usuario
        
    Returns:
        Dict con datos del usuario o None si no se encuentra
    """
    try:
        client = get_client()
        response = client.table('usuarios').select('*').eq('id', usuario_id).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        
        return None
        
    except Exception as e:
        print(f"❌ Error obteniendo usuario por ID: {e}")
        traceback.print_exc()
        return None

def crear_usuario(datos_usuario: Dict) -> Tuple[bool, str]:
    """
    Crea un nuevo usuario en la base de datos
    
    Args:
        datos_usuario: Diccionario con los datos del usuario
        
    Returns:
        Tupla (éxito, mensaje)
    """
    try:
        admin_client = get_admin_client()
        response = admin_client.table('usuarios').insert(datos_usuario).execute()
        
        if response.data:
            print(f"✅ Usuario creado: {datos_usuario.get('nombre', 'N/A')}")
            return True, "Usuario creado exitosamente"
        
        return False, "Error al crear usuario"
        
    except Exception as e:
        print(f"❌ Error creando usuario: {e}")
        return False, f"Error: {str(e)}"

def actualizar_usuario(usuario_id: str, datos_actualizados: Dict) -> Tuple[bool, str]:
    """
    Actualiza los datos de un usuario existente
    
    Args:
        usuario_id: ID del usuario a actualizar
        datos_actualizados: Diccionario con los nuevos datos
        
    Returns:
        Tupla (éxito, mensaje)
    """
    try:
        admin_client = get_admin_client()
        response = admin_client.table('usuarios').update(datos_actualizados).eq('id', usuario_id).execute()
        
        if response.data:
            print(f"✅ Usuario actualizado: ID {usuario_id}")
            return True, "Usuario actualizado exitosamente"
        
        return False, "Error al actualizar usuario"
        
    except Exception as e:
        print(f"❌ Error actualizando usuario: {e}")
        return False, f"Error: {str(e)}"

def eliminar_usuario(usuario_id: str) -> Tuple[bool, str]:
    """
    Elimina un usuario de la base de datos
    
    Args:
        usuario_id: ID del usuario a eliminar
        
    Returns:
        Tupla (éxito, mensaje)
    """
    try:
        admin_client = get_admin_client()
        response = admin_client.table('usuarios').delete().eq('id', usuario_id).execute()
        
        print(f"✅ Usuario eliminado: ID {usuario_id}")
        return True, "Usuario eliminado exitosamente"
        
    except Exception as e:
        print(f"❌ Error eliminando usuario: {e}")
        return False, f"Error: {str(e)}"
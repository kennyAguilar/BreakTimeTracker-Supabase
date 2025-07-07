"""
Módulo de Gestión de Administradores
====================================

Maneja todas las operaciones relacionadas con administradores del sistema.
"""

import traceback
from typing import Dict, Optional
from db_core import get_client

def buscar_administrador(usuario: str, password: str) -> Optional[Dict]:
    """
    Valida las credenciales de un administrador
    
    Args:
        usuario: Nombre de usuario del administrador
        password: Contraseña del administrador
        
    Returns:
        Dict con datos del administrador o None si no es válido
    """
    try:
        client = get_client()
        response = client.table('administradores').select('*').eq('usuario', usuario).eq('password', password).execute()
        
        if response.data and len(response.data) > 0:
            admin_data = response.data[0]
            print(f"✅ Administrador autenticado: {admin_data['nombre']}")
            return admin_data
        
        print(f"❌ Credenciales inválidas para usuario: {usuario}")
        return None
        
    except Exception as e:
        print(f"❌ Error autenticando administrador: {e}")
        traceback.print_exc()
        return None

def obtener_administrador_por_id(admin_id: str) -> Optional[Dict]:
    """
    Obtiene los datos de un administrador por su ID
    
    Args:
        admin_id: ID del administrador
        
    Returns:
        Dict con datos del administrador o None si no se encuentra
    """
    try:
        client = get_client()
        response = client.table('administradores').select('*').eq('id', admin_id).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        
        return None
        
    except Exception as e:
        print(f"❌ Error obteniendo administrador por ID: {e}")
        traceback.print_exc()
        return None
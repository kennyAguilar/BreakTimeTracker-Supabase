"""
Utilidades de Base de Datos para BreakTimeTracker
================================================

Este módulo centraliza todas las operaciones de base de datos
para hacer el código más limpio y mantenible.

Funciones principales:
- Gestión de usuarios
- Gestión de descansos activos
- Gestión de tiempos de descanso
- Gestión de administradores
- Operaciones de consulta y estadísticas
"""

import traceback
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date
from supabase import Client

# Variables globales para los clientes de Supabase
_supabase_client: Optional[Client] = None
_supabase_admin: Optional[Client] = None

def initialize_db_clients(supabase_client: Client, supabase_admin: Client):
    """
    Inicializa los clientes de Supabase para uso en las utilidades
    
    Args:
        supabase_client: Cliente público de Supabase
        supabase_admin: Cliente administrativo de Supabase
    """
    global _supabase_client, _supabase_admin
    _supabase_client = supabase_client
    _supabase_admin = supabase_admin
    print("✅ Clientes de base de datos inicializados en db_utils")

def get_client() -> Client:
    """Obtiene el cliente público de Supabase"""
    if _supabase_client is None:
        raise RuntimeError("Cliente de Supabase no inicializado. Llama a initialize_db_clients() primero.")
    return _supabase_client

def get_admin_client() -> Client:
    """Obtiene el cliente administrativo de Supabase"""
    if _supabase_admin is None:
        raise RuntimeError("Cliente administrativo de Supabase no inicializado. Llama a initialize_db_clients() primero.")
    return _supabase_admin

# ===== FUNCIONES DE USUARIOS =====

def buscar_usuario_por_tarjeta(tarjeta: str) -> Optional[Dict]:
    """
    Busca un usuario por número de tarjeta
    
    Args:
        tarjeta: Número de tarjeta a buscar
        
    Returns:
        Dict con datos del usuario o None si no se encuentra
    """
    try:
        print(f"🔍 Buscando usuario por tarjeta: '{tarjeta}'")
        response = get_client().table('usuarios').select("*").eq('tarjeta', tarjeta).execute()
        
        if response.data:
            usuario = response.data[0]
            print(f"✅ Usuario encontrado: {usuario['nombre']} (ID: {usuario['id']})")
            return usuario
        else:
            print(f"❌ No se encontró usuario con tarjeta: '{tarjeta}'")
            return None
            
    except Exception as e:
        print(f"❌ Error buscando usuario por tarjeta: {e}")
        return None

def buscar_usuario_por_codigo(codigo: str) -> Optional[Dict]:
    """
    Busca un usuario por código de empleado
    
    Args:
        codigo: Código de empleado a buscar
        
    Returns:
        Dict con datos del usuario o None si no se encuentra
    """
    try:
        print(f"🔍 Buscando usuario por código: '{codigo}'")
        response = get_client().table('usuarios').select("*").eq('codigo', codigo.upper()).execute()
        
        if response.data:
            usuario = response.data[0]
            print(f"✅ Usuario encontrado: {usuario['nombre']} (ID: {usuario['id']})")
            return usuario
        else:
            print(f"❌ No se encontró usuario con código: '{codigo}'")
            return None
            
    except Exception as e:
        print(f"❌ Error buscando usuario por código: {e}")
        return None

def obtener_descanso_activo(usuario_id: int) -> Optional[Dict]:
    """
    Obtiene el descanso activo de un usuario
    
    Args:
        usuario_id: ID del usuario
        
    Returns:
        Dict con datos del descanso activo o None si no hay ninguno
    """
    try:
        print(f"🔍 Buscando descanso activo para usuario ID: {usuario_id}")
        response = get_client().table('descansos').select("*").eq('usuario_id', usuario_id).execute()
        
        if response.data:
            descanso = response.data[0]
            print(f"✅ Descanso activo encontrado: ID {descanso['id']}, Inicio: {descanso['inicio']}")
            return descanso
        else:
            print(f"ℹ️ No hay descanso activo para usuario ID: {usuario_id}")
            return None
            
    except Exception as e:
        print(f"❌ Error buscando descanso activo: {e}")
        return None

def crear_descanso(usuario_id: int, inicio: str) -> Optional[Dict]:
    """
    Crea un nuevo descanso activo para un usuario
    
    Args:
        usuario_id: ID del usuario
        inicio: Timestamp de inicio en formato ISO
        
    Returns:
        Dict con datos del descanso creado o None si hay error
    """
    try:
        print(f"📝 Creando descanso para usuario ID: {usuario_id}")
        
        # Verificar que no haya descanso activo
        descanso_activo = obtener_descanso_activo(usuario_id)
        if descanso_activo:
            print(f"⚠️ Usuario ya tiene descanso activo: ID {descanso_activo['id']}")
            return None
        
        data = {
            'usuario_id': usuario_id,
            'inicio': inicio,
            'tipo': 'Pendiente'
        }
        
        response = get_admin_client().table('descansos').insert(data).execute()
        
        if response.data:
            descanso = response.data[0]
            print(f"✅ Descanso creado exitosamente: ID {descanso['id']}")
            return descanso
        else:
            print(f"❌ Error al crear descanso - Sin datos de respuesta")
            return None
            
    except Exception as e:
        print(f"❌ Error creando descanso: {e}")
        return None

def obtener_todos_descansos_activos() -> List[Dict]:
    """
    Obtiene todos los descansos activos en el sistema
    
    Returns:
        Lista de diccionarios con datos de descansos activos
    """
    try:
        print(f"📊 Obteniendo todos los descansos activos...")
        response = get_client().table('descansos').select("*").execute()
        
        descansos = response.data or []
        print(f"✅ Encontrados {len(descansos)} descansos activos")
        
        return descansos
        
    except Exception as e:
        print(f"❌ Error obteniendo descansos activos: {e}")
        return []

def cerrar_descanso(usuario_id: int, descanso_activo: Dict, tiempo_data: Dict) -> Tuple[bool, str, Dict]:
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
        
        # Paso 1: Insertar en tiempos_descanso
        print(f"   📝 Insertando tiempo de descanso...")
        insert_response = get_admin_client().table('tiempos_descanso').insert(tiempo_data).execute()
        
        if not insert_response.data:
            error_msg = "Error insertando en tiempos_descanso"
            print(f"   ❌ {error_msg}")
            return False, error_msg, {'insert_response': insert_response}
        
        tiempo_id = insert_response.data[0]['id']
        print(f"   ✅ Tiempo insertado con ID: {tiempo_id}")
        
        # Paso 2: Eliminar de descansos
        print(f"   🗑️ Eliminando descanso activo...")
        delete_response = get_admin_client().table('descansos').delete().eq('id', descanso_activo['id']).execute()
        
        if delete_response.data:
            print(f"   ✅ Descanso eliminado: {len(delete_response.data)} registros")
        else:
            print(f"   ⚠️ ADVERTENCIA: No se confirmó eliminación")

        # Paso 3: Verificación final
        verify_response = get_admin_client().table('descansos').select("*").eq('usuario_id', usuario_id).execute()
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

# ===== FUNCIONES DE ADMINISTRADORES =====

def buscar_administrador(usuario: str, activo: bool = True) -> Optional[Dict]:
    """
    Busca un administrador por nombre de usuario
    
    Args:
        usuario: Nombre de usuario del administrador
        activo: Si True, solo busca administradores activos
        
    Returns:
        Dict con datos del administrador o None si no se encuentra
    """
    try:
        print(f"🔍 Buscando administrador: '{usuario}' (activo: {activo})")
        
        query = get_admin_client().table('administradores').select("*").eq('usuario', usuario)
        if activo:
            query = query.eq('activo', True)
        
        response = query.execute()
        
        if response.data:
            admin = response.data[0]
            print(f"✅ Administrador encontrado: {admin['nombre']} (ID: {admin['id']})")
            return admin
        else:
            print(f"❌ No se encontró administrador: '{usuario}'")
            return None
            
    except Exception as e:
        print(f"❌ Error buscando administrador: {e}")
        return None

def obtener_todos_los_usuarios() -> List[Dict]:
    """
    Obtiene todos los usuarios del sistema
    
    Returns:
        Lista de diccionarios con datos de usuarios
    """
    try:
        print(f"📊 Obteniendo todos los usuarios...")
        response = get_client().table('usuarios').select("*").order('nombre').execute()
        
        usuarios = response.data or []
        print(f"✅ Encontrados {len(usuarios)} usuarios")
        
        return usuarios
        
    except Exception as e:
        print(f"❌ Error obteniendo usuarios: {e}")
        return []

def obtener_usuario_por_id(usuario_id: int) -> Optional[Dict]:
    """
    Obtiene un usuario por su ID
    
    Args:
        usuario_id: ID del usuario
        
    Returns:
        Dict con datos del usuario o None si no se encuentra
    """
    try:
        print(f"🔍 Buscando usuario por ID: {usuario_id}")
        response = get_client().table('usuarios').select("*").eq('id', usuario_id).execute()
        
        if response.data:
            usuario = response.data[0]
            print(f"✅ Usuario encontrado: {usuario['nombre']} (ID: {usuario['id']})")
            return usuario
        else:
            print(f"❌ No se encontró usuario con ID: {usuario_id}")
            return None
            
    except Exception as e:
        print(f"❌ Error buscando usuario por ID: {e}")
        return None

def crear_usuario(nombre: str, tarjeta: str, turno: str, codigo: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    Crea un nuevo usuario en el sistema
    
    Args:
        nombre: Nombre completo del usuario
        tarjeta: Número de tarjeta
        turno: Tipo de turno (Full, Part Time, Llamado)
        codigo: Código de empleado
        
    Returns:
        Tuple (success: bool, mensaje: str, usuario: Dict o None)
    """
    try:
        print(f"📝 Creando usuario: {nombre} ({codigo})")
        
        # Verificar que no exista el código
        existing = get_client().table('usuarios').select("id").eq('codigo', codigo.upper()).execute()
        if existing.data:
            error_msg = f"Ya existe un usuario con el código {codigo}"
            print(f"❌ {error_msg}")
            return False, error_msg, None
        
        data = {
            'nombre': nombre,
            'tarjeta': tarjeta,
            'turno': turno,
            'codigo': codigo.upper()
        }
        
        response = get_admin_client().table('usuarios').insert(data).execute()
        
        if response.data:
            usuario = response.data[0]
            success_msg = f"Usuario {nombre} creado exitosamente"
            print(f"✅ {success_msg}")
            return True, success_msg, usuario
        else:
            error_msg = "Error al crear usuario - Sin datos de respuesta"
            print(f"❌ {error_msg}")
            return False, error_msg, None
            
    except Exception as e:
        error_msg = f"Error al crear usuario: {str(e)}"
        print(f"❌ {error_msg}")
        return False, error_msg, None

def actualizar_usuario(usuario_id: int, nombre: str, tarjeta: str, turno: str, codigo: str) -> Tuple[bool, str, Optional[Dict]]:
    """
    Actualiza los datos de un usuario existente
    
    Args:
        usuario_id: ID del usuario a actualizar
        nombre: Nuevo nombre completo
        tarjeta: Nuevo número de tarjeta
        turno: Nuevo tipo de turno
        codigo: Nuevo código de empleado
        
    Returns:
        Tuple (success: bool, mensaje: str, usuario: Dict o None)
    """
    try:
        print(f"🔄 Actualizando usuario ID: {usuario_id}")
        
        data = {
            'nombre': nombre,
            'tarjeta': tarjeta,
            'turno': turno,
            'codigo': codigo.upper()
        }
        
        response = get_admin_client().table('usuarios').update(data).eq('id', usuario_id).execute()
        
        if response.data:
            usuario = response.data[0]
            success_msg = f"Usuario {nombre} actualizado exitosamente"
            print(f"✅ {success_msg}")
            return True, success_msg, usuario
        else:
            error_msg = "Error al actualizar usuario - Sin datos de respuesta"
            print(f"❌ {error_msg}")
            return False, error_msg, None
            
    except Exception as e:
        error_msg = f"Error al actualizar usuario: {str(e)}"
        print(f"❌ {error_msg}")
        return False, error_msg, None

def eliminar_usuario(usuario_id: int) -> Tuple[bool, str]:
    """
    Elimina un usuario del sistema
    
    Args:
        usuario_id: ID del usuario a eliminar
        
    Returns:
        Tuple (success: bool, mensaje: str)
    """
    try:
        print(f"🗑️ Eliminando usuario ID: {usuario_id}")
        
        # Obtener nombre del usuario antes de eliminar
        usuario = obtener_usuario_por_id(usuario_id)
        nombre_usuario = usuario['nombre'] if usuario else "Usuario"
        
        response = get_admin_client().table('usuarios').delete().eq('id', usuario_id).execute()
        
        if response.data:
            success_msg = f"Usuario {nombre_usuario} eliminado exitosamente"
            print(f"✅ {success_msg}")
            return True, success_msg
        else:
            error_msg = f"Error al eliminar usuario - Sin confirmación"
            print(f"❌ {error_msg}")
            return False, error_msg
            
    except Exception as e:
        error_msg = f"Error al eliminar usuario: {str(e)}"
        print(f"❌ {error_msg}")
        return False, error_msg

# ===== FUNCIONES DE BÚSQUEDA INTELIGENTE =====

def buscar_usuario_inteligente(entrada: str) -> Optional[Dict]:
    """
    Busca un usuario de forma inteligente: primero por tarjeta, luego por código
    
    Args:
        entrada: Datos de entrada (tarjeta o código)
        
    Returns:
        Dict con datos del usuario o None si no se encuentra
    """
    # Intentar por tarjeta
    usuario = buscar_usuario_por_tarjeta(entrada)
    if usuario:
        return usuario
    
    # Intentar por código
    usuario = buscar_usuario_por_codigo(entrada)
    if usuario:
        return usuario
    
    print(f"❌ Usuario no encontrado con: '{entrada}'")
    return None

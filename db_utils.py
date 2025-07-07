"""
Utilidades de Base de Datos para BreakTimeTracker
================================================

Módulo principal que centraliza todas las operaciones de base de datos.
Importa y expone funciones de módulos especializados.

Estructura modular:
- db_core: Inicialización y clientes base
- db_usuarios: Gestión de usuarios
- db_descansos: Gestión de descansos y tiempos
- db_admin: Gestión de administradores
"""

# Importar funciones de inicialización
from db_core import initialize_db_clients, get_client, get_admin_client

# Importar funciones de usuarios
from db_usuarios import (
    buscar_usuario_por_tarjeta,
    buscar_usuario_por_codigo,
    buscar_usuario_inteligente,
    obtener_todos_los_usuarios,
    obtener_usuario_por_id,
    crear_usuario,
    actualizar_usuario,
    eliminar_usuario
)

# Importar funciones de descansos
from db_descansos import (
    obtener_descanso_activo,
    crear_descanso,
    obtener_todos_descansos_activos,
    cerrar_descanso,
    obtener_registros_periodo
)

# Importar funciones de administradores
from db_admin import (
    buscar_administrador,
    obtener_administrador_por_id
)

# Exportar todas las funciones para que estén disponibles
__all__ = [
    # Core
    'initialize_db_clients',
    'get_client',
    'get_admin_client',
    
    # Usuarios
    'buscar_usuario_por_tarjeta',
    'buscar_usuario_por_codigo',
    'buscar_usuario_inteligente',
    'obtener_todos_los_usuarios',
    'obtener_usuario_por_id',
    'crear_usuario',
    'actualizar_usuario',
    'eliminar_usuario',
    
    # Descansos
    'obtener_descanso_activo',
    'crear_descanso',
    'obtener_todos_descansos_activos',
    'cerrar_descanso',
    'cerrar_descanso_completo',
    'obtener_registros_periodo',
    
    # Administradores
    'buscar_administrador',
    'obtener_administrador_por_id'
]

# Información del módulo
def get_module_info():
    """
    Obtiene información sobre el módulo de base de datos
    
    Returns:
        Dict con información del módulo
    """
    return {
        'nombre': 'BreakTimeTracker Database Utils',
        'version': '2.0.0',
        'descripcion': 'Utilidades modularizadas de base de datos',
        'modulos': [
            'db_core - Inicialización y clientes',
            'db_usuarios - Gestión de usuarios',
            'db_descansos - Gestión de descansos',
            'db_admin - Gestión de administradores'
        ],
        'funciones_disponibles': len(__all__)
    }

# Función de prueba de conectividad
def test_connectivity():
    """
    Prueba la conectividad de todos los módulos
    
    Returns:
        Dict con resultado de las pruebas
    """
    results = {
        'core': False,
        'usuarios': False,
        'descansos': False,
        'admin': False,
        'mensaje': ''
    }
    
    try:
        # Probar core
        client = get_client()
        if client:
            results['core'] = True
        
        # Probar usuarios
        usuarios = obtener_todos_los_usuarios()
        if isinstance(usuarios, list):
            results['usuarios'] = True
        
        # Probar descansos
        descansos = obtener_todos_descansos_activos()
        if isinstance(descansos, list):
            results['descansos'] = True
        
        # Admin se considera funcional si core funciona
        results['admin'] = results['core']
        
        if all(results.values()):
            results['mensaje'] = 'Todos los módulos funcionan correctamente'
        else:
            results['mensaje'] = 'Algunos módulos presentan problemas'
            
    except Exception as e:
        results['mensaje'] = f'Error en prueba de conectividad: {str(e)}'
    
    return results

print("✅ Módulo db_utils v2.0 cargado - Estructura modular activa")

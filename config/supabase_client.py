"""
Cliente de Supabase para BreakTimeTracker
Configura las conexiones con diferentes niveles de permisos
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Obtener URLs y claves
url: str = os.environ.get("SUPABASE_URL")
anon_key: str = os.environ.get("SUPABASE_ANON_KEY")
service_key: str = os.environ.get("SUPABASE_SERVICE_KEY")

if not url or not anon_key:
    raise ValueError("SUPABASE_URL y SUPABASE_ANON_KEY son requeridos")

# Cliente público (para operaciones generales con RLS)
supabase: Client = create_client(url, anon_key)

# Cliente de servicio (para operaciones administrativas sin RLS)
# Solo crear si existe la service key
supabase_admin: Client = None
if service_key:
    supabase_admin = create_client(url, service_key)
else:
    print("⚠️  SUPABASE_SERVICE_KEY no configurada - operaciones admin limitadas")
    # En este caso, usar el cliente anon para operaciones admin
    supabase_admin = supabase

# Funciones auxiliares para verificar conexión
def test_connection():
    """Verifica que la conexión a Supabase funcione"""
    try:
        # Intentar una consulta simple
        response = supabase.table('usuarios').select("count", count='exact').execute()
        print(f"✅ Conexión exitosa - {response.count} usuarios en la base de datos")
        return True
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

def get_table_stats():
    """Obtiene estadísticas básicas de las tablas"""
    try:
        stats = {}
        tables = ['usuarios', 'administradores', 'descansos', 'tiempos_descanso']
        
        for table in tables:
            response = supabase.table(table).select("count", count='exact').execute()
            stats[table] = response.count
        
        return stats
    except Exception as e:
        print(f"Error obteniendo estadísticas: {e}")
        return {}
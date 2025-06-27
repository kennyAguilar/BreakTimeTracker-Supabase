"""
Script de migración de PostgreSQL/Neon a Supabase
Ejecutar una sola vez para migrar todos los datos existentes
"""

import psycopg2
from supabase import create_client
from dotenv import load_dotenv
import os
from datetime import datetime
import sys

# Cargar variables de entorno
load_dotenv()

# Configurar cliente Supabase
supabase_admin = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_KEY')
)

def migrate_from_postgres():
    """Migra todos los datos de PostgreSQL a Supabase"""
    
    print("🚀 Iniciando migración a Supabase...")
    
    try:
        # Conectar a PostgreSQL
        pg_conn = psycopg2.connect(
            host=os.getenv('OLD_DB_HOST'),
            port=os.getenv('OLD_DB_PORT', 5432),
            database=os.getenv('OLD_DB_NAME'),
            user=os.getenv('OLD_DB_USER'),
            password=os.getenv('OLD_DB_PASSWORD')
        )
        
        cursor = pg_conn.cursor()
        print("✅ Conectado a PostgreSQL")
        
    except Exception as e:
        print(f"❌ Error conectando a PostgreSQL: {e}")
        sys.exit(1)
    
    # Diccionario para mapear IDs antiguos a nuevos
    usuario_map = {}
    
    # 1. Migrar usuarios
    print("\n📦 Migrando usuarios...")
    try:
        cursor.execute("SELECT id, nombre, tarjeta, turno, codigo FROM usuarios ORDER BY id")
        usuarios = cursor.fetchall()
        
        for old_id, nombre, tarjeta, turno, codigo in usuarios:
            try:
                # Insertar en Supabase
                response = supabase_admin.table('usuarios').insert({
                    'nombre': nombre,
                    'tarjeta': tarjeta,
                    'turno': turno,
                    'codigo': codigo
                }).execute()
                
                # Guardar mapeo de IDs
                new_id = response.data[0]['id']
                usuario_map[old_id] = new_id
                print(f"  ✓ {nombre} ({codigo})")
                
            except Exception as e:
                print(f"  ✗ Error con {nombre}: {e}")
        
        print(f"✅ {len(usuarios)} usuarios migrados")
        
    except Exception as e:
        print(f"❌ Error migrando usuarios: {e}")
    
    # 2. Migrar administradores
    print("\n📦 Migrando administradores...")
    try:
        cursor.execute("SELECT usuario, clave, nombre, activo FROM administradores")
        admins = cursor.fetchall()
        
        for usuario, clave, nombre, activo in admins:
            try:
                supabase_admin.table('administradores').insert({
                    'usuario': usuario,
                    'clave': clave,  # Nota: En producción, re-hashear con bcrypt
                    'nombre': nombre,
                    'activo': activo
                }).execute()
                print(f"  ✓ {nombre} ({usuario})")
                
            except Exception as e:
                print(f"  ✗ Error con admin {usuario}: {e}")
        
        print(f"✅ {len(admins)} administradores migrados")
        
    except Exception as e:
        print(f"❌ Error migrando administradores: {e}")
    
    # 3. Migrar tiempos_descanso (historial)
    print("\n📦 Migrando historial de tiempos...")
    try:
        cursor.execute("""
            SELECT usuario_id, tipo, fecha, inicio, fin, duracion_minutos 
            FROM tiempos_descanso 
            ORDER BY fecha DESC, inicio DESC
        """)
        tiempos = cursor.fetchall()
        
        migrados = 0
        errores = 0
        
        for usuario_id, tipo, fecha, inicio, fin, duracion_minutos in tiempos:
            if usuario_id in usuario_map:
                try:
                    supabase_admin.table('tiempos_descanso').insert({
                        'usuario_id': usuario_map[usuario_id],
                        'tipo': tipo,
                        'fecha': str(fecha),
                        'inicio': str(inicio),
                        'fin': str(fin),
                        'duracion_minutos': duracion_minutos
                    }).execute()
                    migrados += 1
                    
                    # Mostrar progreso cada 100 registros
                    if migrados % 100 == 0:
                        print(f"  ... {migrados} registros migrados")
                        
                except Exception as e:
                    errores += 1
                    if errores <= 5:  # Mostrar solo los primeros 5 errores
                        print(f"  ✗ Error en registro: {e}")
            else:
                errores += 1
        
        print(f"✅ {migrados} registros de tiempo migrados")
        if errores > 0:
            print(f"⚠️  {errores} registros con errores (usuarios no encontrados)")
        
    except Exception as e:
        print(f"❌ Error migrando tiempos: {e}")
    
    # 4. Migrar descansos activos
    print("\n📦 Migrando descansos activos...")
    try:
        cursor.execute("""
            SELECT usuario_id, tipo, inicio 
            FROM descansos 
            WHERE inicio IS NOT NULL
        """)
        descansos = cursor.fetchall()
        
        for usuario_id, tipo, inicio in descansos:
            if usuario_id in usuario_map:
                try:
                    supabase_admin.table('descansos').insert({
                        'usuario_id': usuario_map[usuario_id],
                        'tipo': tipo or 'Pendiente',
                        'inicio': inicio.isoformat() if inicio else datetime.now().isoformat()
                    }).execute()
                    
                except Exception as e:
                    print(f"  ✗ Error con descanso activo: {e}")
        
        print(f"✅ {len(descansos)} descansos activos migrados")
        
    except Exception as e:
        print(f"❌ Error migrando descansos activos: {e}")
    
    # Cerrar conexión PostgreSQL
    cursor.close()
    pg_conn.close()
    
    # Mostrar resumen
    print("\n" + "="*50)
    print("🎉 MIGRACIÓN COMPLETADA")
    print("="*50)
    
    # Verificar datos en Supabase
    try:
        stats = {}
        for table in ['usuarios', 'administradores', 'tiempos_descanso', 'descansos']:
            response = supabase_admin.table(table).select("count", count='exact').execute()
            stats[table] = response.count
        
        print("\n📊 Estadísticas finales en Supabase:")
        for table, count in stats.items():
            print(f"  - {table}: {count} registros")
            
    except Exception as e:
        print(f"Error obteniendo estadísticas: {e}")
    
    print("\n✅ La migración ha finalizado. Verifica los datos en tu dashboard de Supabase.")
    print("🔐 Recuerda actualizar las contraseñas de administradores con bcrypt en producción.")

def verify_connection():
    """Verifica que las conexiones funcionen antes de migrar"""
    print("🔍 Verificando conexiones...")
    
    # Verificar PostgreSQL
    try:
        pg_conn = psycopg2.connect(
            host=os.getenv('OLD_DB_HOST'),
            port=os.getenv('OLD_DB_PORT', 5432),
            database=os.getenv('OLD_DB_NAME'),
            user=os.getenv('OLD_DB_USER'),
            password=os.getenv('OLD_DB_PASSWORD')
        )
        cursor = pg_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        count = cursor.fetchone()[0]
        cursor.close()
        pg_conn.close()
        print(f"✅ PostgreSQL: OK ({count} usuarios encontrados)")
    except Exception as e:
        print(f"❌ PostgreSQL: {e}")
        return False
    
    # Verificar Supabase
    try:
        response = supabase_admin.table('usuarios').select("count", count='exact').execute()
        print(f"✅ Supabase: OK")
        if response.count > 0:
            print(f"⚠️  ADVERTENCIA: Ya hay {response.count} usuarios en Supabase")
            respuesta = input("¿Continuar con la migración? (s/n): ")
            if respuesta.lower() != 's':
                return False
    except Exception as e:
        print(f"❌ Supabase: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Script de Migración BreakTimeTracker")
    print("=====================================")
    
    # Verificar conexiones
    if not verify_connection():
        print("\n❌ Abortando migración por errores de conexión")
        sys.exit(1)
    
    # Confirmar migración
    print("\n⚠️  IMPORTANTE: Este script migrará todos los datos de PostgreSQL a Supabase.")
    print("   Asegúrate de tener un respaldo de tus datos antes de continuar.")
    
    respuesta = input("\n¿Deseas continuar con la migración? (s/n): ")
    
    if respuesta.lower() == 's':
        migrate_from_postgres()
    else:
        print("❌ Migración cancelada")
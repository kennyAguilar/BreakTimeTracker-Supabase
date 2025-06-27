#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de prueba para verificar la conexión a Supabase
"""

import os
from dotenv import load_dotenv

print("🔧 Test de conexión a Supabase")
print("=" * 50)

# Cargar variables de entorno
print("📁 Cargando variables de entorno...")
load_dotenv()

# Verificar variables
supabase_url = os.getenv('SUPABASE_URL')
supabase_anon_key = os.getenv('SUPABASE_ANON_KEY')
supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')

print(f"🌐 SUPABASE_URL: {supabase_url[:30]}..." if supabase_url else "❌ SUPABASE_URL: NO ENCONTRADA")
print(f"🔑 SUPABASE_ANON_KEY: {'✓ Configurada' if supabase_anon_key else '❌ NO ENCONTRADA'}")
print(f"🔑 SUPABASE_SERVICE_KEY: {'✓ Configurada' if supabase_service_key else '❌ NO ENCONTRADA'}")

if not all([supabase_url, supabase_anon_key, supabase_service_key]):
    print("\n❌ Error: Variables de entorno faltantes")
    print("Verifica que el archivo .env está en el directorio correcto")
    exit(1)

print("\n📦 Importando Supabase...")
try:
    from supabase import create_client, Client
    print("✅ Supabase importado correctamente")
except ImportError as e:
    print(f"❌ Error importando Supabase: {e}")
    print("Ejecuta: pip install supabase")
    exit(1)

print("\n🔗 Intentando conectar a Supabase...")
try:
    # Crear cliente
    supabase = create_client(supabase_url, supabase_anon_key)
    print("✅ Cliente creado exitosamente")
    
    # Probar consulta simple
    print("🧪 Probando consulta a tabla 'usuarios'...")
    response = supabase.table('usuarios').select("*").limit(1).execute()
    print(f"✅ Consulta exitosa - {len(response.data)} registros encontrados")
    
    # Probar con cliente admin
    print("🔐 Probando cliente administrativo...")
    supabase_admin = create_client(supabase_url, supabase_service_key)
    admin_response = supabase_admin.table('administradores').select("*").limit(1).execute()
    print(f"✅ Cliente admin funcionando - {len(admin_response.data)} administradores")
    
    print("\n🎉 ¡TODAS LAS PRUEBAS EXITOSAS!")
    print("La conexión a Supabase está funcionando correctamente.")
    
except Exception as e:
    print(f"\n❌ Error en la conexión:")
    print(f"   Tipo: {type(e).__name__}")
    print(f"   Mensaje: {str(e)}")
    
    print("\n🔧 Posibles soluciones:")
    print("1. Verificar que el proyecto de Supabase está activo")
    print("2. Verificar que las credenciales no han expirado")
    print("3. Verificar conexión a internet")
    print("4. Verificar que las tablas existen en Supabase")
    
    # Mostrar más detalles del error
    import traceback
    print(f"\n📋 Stack trace completo:")
    print(traceback.format_exc())

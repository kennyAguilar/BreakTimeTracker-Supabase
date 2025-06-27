#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script simple para probar la conexión con Supabase
"""

import os
import sys
from datetime import datetime

# Asegurar que las variables de entorno se carguen desde .env
from dotenv import load_dotenv
load_dotenv()

print("=== TEST DE CONEXIÓN SUPABASE ===")
print(f"Directorio actual: {os.getcwd()}")

# Verificar variables de entorno
url = os.getenv("SUPABASE_URL")
anon_key = os.getenv("SUPABASE_ANON_KEY")
service_key = os.getenv("SUPABASE_SERVICE_KEY")

print(f"SUPABASE_URL: {'✓' if url else '✗'} {url[:50] if url else 'No encontrada'}")
print(f"SUPABASE_ANON_KEY: {'✓' if anon_key else '✗'} {anon_key[:20] + '...' if anon_key else 'No encontrada'}")
print(f"SUPABASE_SERVICE_KEY: {'✓' if service_key else '✗'} {service_key[:20] + '...' if service_key else 'No encontrada'}")

if not all([url, anon_key, service_key]):
    print("ERROR: Faltan variables de entorno!")
    sys.exit(1)

try:
    from supabase import create_client
    print("✓ Librería supabase importada correctamente")
except ImportError as e:
    print(f"✗ Error importando supabase: {e}")
    sys.exit(1)

# Crear clientes
try:
    print("\n=== CREANDO CLIENTES ===")
    supabase = create_client(url, anon_key)
    print("✓ Cliente anónimo creado")
    
    supabase_admin = create_client(url, service_key)
    print("✓ Cliente admin creado")
    
except Exception as e:
    print(f"✗ Error creando clientes: {e}")
    sys.exit(1)

# Test 1: Verificar conexión básica
print("\n=== TEST 1: CONEXIÓN BÁSICA ===")
try:
    response = supabase.table("usuarios").select("*").limit(1).execute()
    print(f"✓ Conexión exitosa. Datos: {response.data}")
except Exception as e:
    print(f"✗ Error en conexión básica: {e}")

# Test 2: Listar usuarios
print("\n=== TEST 2: LISTAR USUARIOS ===")
try:
    response = supabase.table("usuarios").select("*").execute()
    print(f"✓ {len(response.data)} usuarios encontrados")
    for user in response.data:
        print(f"  - {user['nombre']} (ID: {user['id']})")
except Exception as e:
    print(f"✗ Error listando usuarios: {e}")

# Test 3: Listar descansos activos
print("\n=== TEST 3: DESCANSOS ACTIVOS ===")
try:
    response = supabase.table("descansos").select("*").execute()
    print(f"✓ {len(response.data)} descansos activos encontrados")
    for descanso in response.data:
        print(f"  - Usuario ID: {descanso['usuario_id']}, Inicio: {descanso['inicio']}")
except Exception as e:
    print(f"✗ Error listando descansos: {e}")

# Test 4: Inserción de prueba (usando admin)
print("\n=== TEST 4: INSERCIÓN DE PRUEBA ===")
try:
    test_data = {
        "usuario_id": 1,  # Asumiendo que existe usuario con ID 1
        "inicio": datetime.now().isoformat()
    }
    
    response = supabase_admin.table("descansos").insert(test_data).execute()
    if response.data:
        test_id = response.data[0]['id']
        print(f"✓ Descanso de prueba insertado (ID: {test_id})")
        
        # Test 5: Eliminación de prueba
        print("\n=== TEST 5: ELIMINACIÓN DE PRUEBA ===")
        delete_response = supabase_admin.table("descansos").delete().eq("id", test_id).execute()
        print(f"✓ Descanso de prueba eliminado")
    else:
        print("✗ No se pudo insertar el descanso de prueba")
        
except Exception as e:
    print(f"✗ Error en inserción/eliminación: {e}")

print("\n=== FIN DE PRUEBAS ===")

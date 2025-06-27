#!/usr/bin/env python3
# -*- coding: utf-8 -*-

print("🔧 Iniciando pruebas de diagnóstico...")

# Prueba 1: Importaciones básicas
try:
    import os
    print("✅ os importado")
except Exception as e:
    print(f"❌ Error importando os: {e}")

try:
    from dotenv import load_dotenv
    print("✅ dotenv importado")
except Exception as e:
    print(f"❌ Error importando dotenv: {e}")

try:
    from flask import Flask
    print("✅ Flask importado")
except Exception as e:
    print(f"❌ Error importando Flask: {e}")

# Prueba 2: Cargar variables de entorno
try:
    load_dotenv()
    print("✅ Variables de entorno cargadas")
    
    url = os.getenv('SUPABASE_URL')
    anon_key = os.getenv('SUPABASE_ANON_KEY')
    service_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    print(f"📊 SUPABASE_URL: {'✓' if url else '✗'}")
    print(f"📊 SUPABASE_ANON_KEY: {'✓' if anon_key else '✗'}")
    print(f"📊 SUPABASE_SERVICE_KEY: {'✓' if service_key else '✗'}")
    
except Exception as e:
    print(f"❌ Error cargando variables: {e}")

# Prueba 3: Importar Supabase
try:
    from supabase import create_client, Client
    print("✅ Supabase importado")
except Exception as e:
    print(f"❌ Error importando Supabase: {e}")
    exit(1)

# Prueba 4: Crear cliente Supabase
try:
    if url and anon_key:
        client = create_client(url, anon_key)
        print("✅ Cliente Supabase creado exitosamente")
    else:
        print("❌ No se puede crear cliente - faltan variables de entorno")
except Exception as e:
    print(f"❌ Error creando cliente Supabase: {e}")

print("🎉 Diagnóstico completado")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test directo de la conexión sin dependencias externas
"""

import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

print("=== DIAGNÓSTICO DIRECTO DE SUPABASE ===")

# Verificar variables de entorno
url = os.getenv("SUPABASE_URL")
anon_key = os.getenv("SUPABASE_ANON_KEY")
service_key = os.getenv("SUPABASE_SERVICE_KEY")

print(f"SUPABASE_URL: {url}")
print(f"SUPABASE_ANON_KEY: {anon_key[:20]}..." if anon_key else "SUPABASE_ANON_KEY: NO ENCONTRADA")
print(f"SUPABASE_SERVICE_KEY: {service_key[:20]}..." if service_key else "SUPABASE_SERVICE_KEY: NO ENCONTRADA")

if not all([url, anon_key, service_key]):
    print("❌ PROBLEMA: Variables de entorno faltantes")
    exit(1)

try:
    from supabase import create_client
    print("✅ Librería supabase disponible")
    
    # Crear cliente
    supabase = create_client(url, anon_key)
    print("✅ Cliente supabase creado")
    
    # Probar conexión
    response = supabase.table("usuarios").select("*").limit(1).execute()
    print(f"✅ Conexión exitosa: {len(response.data)} registros")
    
    print("🎉 DIAGNÓSTICO: LA CONEXIÓN FUNCIONA CORRECTAMENTE")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("💡 La conexión con Supabase tiene problemas")
    
print("=== FIN DEL DIAGNÓSTICO ===")

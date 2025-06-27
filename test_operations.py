#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar específicamente las operaciones de registrar y cerrar descansos
"""

import os
import sys
from datetime import datetime, timedelta
import pytz

# Asegurar que las variables de entorno se carguen desde .env
from dotenv import load_dotenv
load_dotenv()

try:
    from supabase import create_client
except ImportError:
    print("Error: pip install supabase")
    sys.exit(1)

# Zona horaria
tz = pytz.timezone('America/Punta_Arenas')

def get_current_time():
    return datetime.now(tz)

def main():
    print("=== TEST DE OPERACIONES DE DESCANSO ===")
    
    # Configurar clientes
    url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_KEY")
    anon_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not all([url, service_key, anon_key]):
        print("❌ Variables de entorno faltantes")
        return
    
    supabase = create_client(url, anon_key)
    supabase_admin = create_client(url, service_key)
    
    print("✅ Clientes Supabase creados")
    
    # Paso 1: Verificar usuarios disponibles
    print("\n=== PASO 1: USUARIOS DISPONIBLES ===")
    try:
        users_response = supabase.table("usuarios").select("*").execute()
        print(f"Usuarios encontrados: {len(users_response.data)}")
        
        if not users_response.data:
            print("❌ No hay usuarios en la base de datos")
            return
            
        test_user = users_response.data[0]
        print(f"Usuario de prueba: {test_user['nombre']} (ID: {test_user['id']})")
        
    except Exception as e:
        print(f"❌ Error obteniendo usuarios: {e}")
        return
    
    # Paso 2: Limpiar descansos activos del usuario de prueba
    print(f"\n=== PASO 2: LIMPIANDO DESCANSOS ACTIVOS PARA USUARIO {test_user['id']} ===")
    try:
        clean_response = supabase_admin.table("descansos").delete().eq("usuario_id", test_user['id']).execute()
        print(f"Descansos activos eliminados: {len(clean_response.data) if clean_response.data else 0}")
    except Exception as e:
        print(f"Error limpiando: {e}")
    
    # Paso 3: Registrar entrada a descanso
    print(f"\n=== PASO 3: REGISTRANDO ENTRADA A DESCANSO ===")
    try:
        entrada_data = {
            'usuario_id': test_user['id'],
            'inicio': get_current_time().isoformat(),
            'tipo': 'Pendiente'
        }
        
        insert_response = supabase_admin.table('descansos').insert(entrada_data).execute()
        
        if insert_response.data:
            descanso_id = insert_response.data[0]['id']
            print(f"✅ Entrada registrada (ID: {descanso_id})")
            print(f"   Usuario: {test_user['nombre']}")
            print(f"   Inicio: {entrada_data['inicio']}")
        else:
            print("❌ No se pudo registrar la entrada")
            return
            
    except Exception as e:
        print(f"❌ Error registrando entrada: {e}")
        return
    
    # Paso 4: Verificar descanso activo
    print(f"\n=== PASO 4: VERIFICANDO DESCANSO ACTIVO ===")
    try:
        active_response = supabase.table("descansos").select("*").eq("usuario_id", test_user['id']).execute()
        
        if active_response.data:
            descanso_activo = active_response.data[0]
            print(f"✅ Descanso activo encontrado:")
            print(f"   ID: {descanso_activo['id']}")
            print(f"   Inicio: {descanso_activo['inicio']}")
            print(f"   Tipo: {descanso_activo['tipo']}")
        else:
            print("❌ No se encontró descanso activo")
            return
            
    except Exception as e:
        print(f"❌ Error verificando descanso activo: {e}")
        return
    
    # Esperar un momento para simular tiempo de descanso
    print(f"\n=== PASO 5: SIMULANDO TIEMPO DE DESCANSO (3 segundos) ===")
    import time
    time.sleep(3)
    
    # Paso 6: Cerrar descanso
    print(f"\n=== PASO 6: CERRANDO DESCANSO ===")
    try:
        # Calcular duración y tipo
        inicio = datetime.fromisoformat(descanso_activo['inicio'].replace('Z', '+00:00'))
        fin = get_current_time()
        duracion_minutos = int((fin - inicio).total_seconds() / 60)
        tipo = 'COMIDA' if duracion_minutos >= 30 else 'DESCANSO'
        
        print(f"   Inicio: {inicio}")
        print(f"   Fin: {fin}")
        print(f"   Duración: {duracion_minutos} minutos")
        print(f"   Tipo: {tipo}")
        
        # Insertar en tiempos_descanso
        tiempo_data = {
            'usuario_id': test_user['id'],
            'tipo': tipo,
            'fecha': inicio.date().isoformat(),
            'inicio': inicio.time().isoformat(),
            'fin': fin.time().isoformat(),
            'duracion_minutos': duracion_minutos
        }
        
        insert_tiempo_response = supabase_admin.table('tiempos_descanso').insert(tiempo_data).execute()
        
        if insert_tiempo_response.data:
            print(f"✅ Tiempo de descanso registrado (ID: {insert_tiempo_response.data[0]['id']})")
        else:
            print("❌ Error registrando tiempo de descanso")
            return
        
        # Eliminar de descansos activos
        delete_response = supabase_admin.table('descansos').delete().eq('id', descanso_activo['id']).execute()
        
        if delete_response.data:
            print(f"✅ Descanso activo eliminado")
        else:
            print("⚠️ No se pudo confirmar eliminación del descanso activo")
            
    except Exception as e:
        print(f"❌ Error cerrando descanso: {e}")
        return
    
    # Paso 7: Verificar resultado final
    print(f"\n=== PASO 7: VERIFICACIÓN FINAL ===")
    try:
        # Verificar que no hay descansos activos
        active_check = supabase.table("descansos").select("*").eq("usuario_id", test_user['id']).execute()
        print(f"Descansos activos restantes: {len(active_check.data)}")
        
        # Verificar que se registró el tiempo
        tiempo_check = supabase.table("tiempos_descanso").select("*").eq("usuario_id", test_user['id']).order('id', desc=True).limit(1).execute()
        
        if tiempo_check.data:
            ultimo_tiempo = tiempo_check.data[0]
            print(f"✅ Último tiempo registrado:")
            print(f"   Tipo: {ultimo_tiempo['tipo']}")
            print(f"   Fecha: {ultimo_tiempo['fecha']}")
            print(f"   Duración: {ultimo_tiempo['duracion_minutos']} minutos")
        else:
            print("❌ No se encontraron tiempos registrados")
            
    except Exception as e:
        print(f"❌ Error en verificación final: {e}")
    
    print(f"\n=== PRUEBA COMPLETADA ===")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script directo para probar las operaciones principales sin Flask
"""

import os
import sys
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Zona horaria
tz = pytz.timezone('America/Punta_Arenas')

def get_current_time():
    return datetime.now(tz)

def test_supabase_operations():
    print("🔧 === TEST DIRECTO DE OPERACIONES SUPABASE ===")
    
    try:
        from supabase import create_client
        
        # Configuración
        url = os.getenv("SUPABASE_URL")
        anon_key = os.getenv("SUPABASE_ANON_KEY")
        service_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not all([url, anon_key, service_key]):
            print("❌ Variables de entorno faltantes")
            return False
        
        # Crear clientes
        supabase = create_client(url, anon_key)
        supabase_admin = create_client(url, service_key)
        print("✅ Clientes Supabase creados")
        
        # 1. Obtener primer usuario
        print("\n📊 1. Obteniendo usuarios...")
        users_response = supabase.table("usuarios").select("*").execute()
        
        if not users_response.data:
            print("❌ No hay usuarios en la base de datos")
            return False
        
        test_user = users_response.data[0]
        print(f"✅ Usuario de prueba: {test_user['nombre']} (ID: {test_user['id']})")
        
        # 2. Limpiar descansos activos previos
        print(f"\n🧹 2. Limpiando descansos activos para usuario {test_user['id']}...")
        clean_response = supabase_admin.table("descansos").delete().eq("usuario_id", test_user['id']).execute()
        print(f"✅ Limpieza completada: {len(clean_response.data) if clean_response.data else 0} registros eliminados")
        
        # 3. Registrar entrada a descanso
        print(f"\n⏱️ 3. Registrando entrada a descanso...")
        
        entrada_data = {
            'usuario_id': test_user['id'],
            'inicio': get_current_time().isoformat(),
            'tipo': 'Pendiente'
        }
        
        insert_response = supabase_admin.table('descansos').insert(entrada_data).execute()
        
        if not insert_response.data:
            print("❌ Error: No se pudo insertar el descanso")
            return False
        
        descanso_creado = insert_response.data[0]
        print(f"✅ Descanso creado exitosamente:")
        print(f"   - ID: {descanso_creado['id']}")
        print(f"   - Usuario: {test_user['nombre']}")
        print(f"   - Inicio: {descanso_creado['inicio']}")
        print(f"   - Tipo: {descanso_creado['tipo']}")
        
        # 4. Verificar que el descanso está activo
        print(f"\n🔍 4. Verificando descanso activo...")
        verify_response = supabase.table("descansos").select("*").eq("usuario_id", test_user['id']).execute()
        
        if not verify_response.data:
            print("❌ Error: No se encuentra el descanso activo")
            return False
        
        descanso_activo = verify_response.data[0]
        print(f"✅ Descanso activo confirmado (ID: {descanso_activo['id']})")
        
        # 5. Simular tiempo transcurrido
        print(f"\n⏳ 5. Simulando tiempo de descanso (3 segundos)...")
        import time
        time.sleep(3)
        
        # 6. Cerrar descanso
        print(f"\n🔚 6. Cerrando descanso...")
        
        # Calcular duración
        inicio = datetime.fromisoformat(descanso_activo['inicio'].replace('Z', '+00:00'))
        fin = get_current_time()
        duracion_minutos = int((fin - inicio).total_seconds() / 60)
        tipo = 'COMIDA' if duracion_minutos >= 30 else 'DESCANSO'
        
        print(f"   - Inicio: {inicio.strftime('%H:%M:%S')}")
        print(f"   - Fin: {fin.strftime('%H:%M:%S')}")
        print(f"   - Duración: {duracion_minutos} minutos")
        print(f"   - Tipo: {tipo}")
        
        # 6a. Insertar en tiempos_descanso
        tiempo_data = {
            'usuario_id': test_user['id'],
            'tipo': tipo,
            'fecha': inicio.date().isoformat(),
            'inicio': inicio.time().isoformat(),
            'fin': fin.time().isoformat(),
            'duracion_minutos': duracion_minutos
        }
        
        tiempo_response = supabase_admin.table('tiempos_descanso').insert(tiempo_data).execute()
        
        if not tiempo_response.data:
            print("❌ Error: No se pudo insertar el tiempo de descanso")
            return False
        
        tiempo_creado = tiempo_response.data[0]
        print(f"✅ Tiempo de descanso registrado (ID: {tiempo_creado['id']})")
        
        # 6b. Eliminar descanso activo
        delete_response = supabase_admin.table('descansos').delete().eq('id', descanso_activo['id']).execute()
        
        if delete_response.data:
            print(f"✅ Descanso activo eliminado correctamente")
        else:
            print("⚠️ Advertencia: No se pudo confirmar la eliminación del descanso activo")
        
        # 7. Verificación final
        print(f"\n✅ 7. Verificación final...")
        
        # Verificar que no quedan descansos activos
        final_active_response = supabase.table("descansos").select("*").eq("usuario_id", test_user['id']).execute()
        
        # Verificar que se registró el tiempo
        final_tiempo_response = supabase.table("tiempos_descanso").select("*").eq("usuario_id", test_user['id']).order('id', desc=True).limit(1).execute()
        
        print(f"   - Descansos activos restantes: {len(final_active_response.data)}")
        print(f"   - Tiempos registrados: {len(final_tiempo_response.data)}")
        
        if len(final_active_response.data) == 0 and len(final_tiempo_response.data) > 0:
            ultimo_tiempo = final_tiempo_response.data[0]
            print(f"✅ ÉXITO: Operación completada correctamente")
            print(f"   - Último registro: {ultimo_tiempo['tipo']} de {ultimo_tiempo['duracion_minutos']} minutos")
            print(f"   - Fecha: {ultimo_tiempo['fecha']}")
            return True
        else:
            print(f"❌ Error: Estado final inconsistente")
            return False
        
    except Exception as e:
        print(f"❌ Error durante las pruebas: {e}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        return False

def test_flask_simulation():
    """Simular el flujo que ocurre en Flask"""
    print("\n🌐 === SIMULACIÓN DEL FLUJO FLASK ===")
    
    try:
        from supabase import create_client
        
        # Configuración
        url = os.getenv("SUPABASE_URL")
        anon_key = os.getenv("SUPABASE_ANON_KEY")
        service_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        supabase = create_client(url, anon_key)
        supabase_admin = create_client(url, service_key)
        
        # Simular entrada de tarjeta (código de usuario)
        print("📝 Simulando entrada de código de usuario...")
        
        # Buscar usuario por código (simulamos código "001")
        user_response = supabase.table('usuarios').select('*').eq('codigo', '001').execute()
        
        if not user_response.data:
            print("⚠️ Usuario con código '001' no encontrado, usando primer usuario disponible")
            all_users = supabase.table('usuarios').select('*').execute()
            if not all_users.data:
                print("❌ No hay usuarios en la base de datos")
                return False
            usuario = all_users.data[0]
        else:
            usuario = user_response.data[0]
        
        print(f"👤 Usuario seleccionado: {usuario['nombre']} (Código: {usuario['codigo']})")
        
        # Verificar si tiene descanso activo
        descanso_response = supabase.table('descansos').select('*').eq('usuario_id', usuario['id']).execute()
        
        if descanso_response.data:
            # Tiene descanso activo - SALIDA
            print(f"🚪 Usuario tiene descanso activo - Procesando SALIDA...")
            
            descanso_activo = descanso_response.data[0]
            
            # Calcular duración
            inicio = datetime.fromisoformat(descanso_activo['inicio'].replace('Z', '+00:00'))
            fin = get_current_time()
            duracion_minutos = int((fin - inicio).total_seconds() / 60)
            tipo = 'COMIDA' if duracion_minutos >= 30 else 'DESCANSO'
            
            print(f"   Duración: {duracion_minutos} minutos → {tipo}")
            
            # Registrar tiempo de descanso
            insert_response = supabase_admin.table('tiempos_descanso').insert({
                'usuario_id': usuario['id'],
                'tipo': tipo,
                'fecha': inicio.date().isoformat(),
                'inicio': inicio.time().isoformat(),
                'fin': fin.time().isoformat(),
                'duracion_minutos': duracion_minutos
            }).execute()
            
            if insert_response.data:
                print(f"✅ Tiempo registrado: {insert_response.data[0]['id']}")
            else:
                print(f"❌ Error registrando tiempo")
                return False
            
            # Eliminar descanso activo
            delete_response = supabase_admin.table('descansos').delete().eq('id', descanso_activo['id']).execute()
            
            if delete_response.data:
                print(f"✅ Descanso activo eliminado")
            else:
                print(f"⚠️ No se pudo eliminar descanso activo")
            
            print(f"✅ SALIDA procesada: {usuario['nombre']} - {tipo} de {duracion_minutos} minutos")
            
        else:
            # No tiene descanso activo - ENTRADA
            print(f"🚪 Usuario sin descanso activo - Procesando ENTRADA...")
            
            insert_response = supabase_admin.table('descansos').insert({
                'usuario_id': usuario['id'],
                'inicio': get_current_time().isoformat(),
                'tipo': 'Pendiente'
            }).execute()
            
            if insert_response.data:
                print(f"✅ ENTRADA procesada: {usuario['nombre']} - Descanso iniciado (ID: {insert_response.data[0]['id']})")
            else:
                print(f"❌ Error procesando entrada")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error en simulación Flask: {e}")
        return False

if __name__ == "__main__":
    print("🔧 DIAGNÓSTICO COMPLETO DE SUPABASE")
    print("=" * 50)
    
    # Test 1: Operaciones básicas
    success1 = test_supabase_operations()
    
    print("\n" + "=" * 50)
    
    # Test 2: Simulación de Flask
    success2 = test_flask_simulation()
    
    print("\n" + "=" * 50)
    print("📊 RESUMEN FINAL:")
    print(f"   - Test de operaciones básicas: {'✅ ÉXITO' if success1 else '❌ FALLO'}")
    print(f"   - Test de simulación Flask: {'✅ ÉXITO' if success2 else '❌ FALLO'}")
    
    if success1 and success2:
        print("🎉 DIAGNÓSTICO EXITOSO: Todas las operaciones funcionan correctamente")
        print("✅ La aplicación debería funcionar sin problemas")
    else:
        print("⚠️ Se encontraron problemas durante las pruebas")
    
    print("=" * 50)

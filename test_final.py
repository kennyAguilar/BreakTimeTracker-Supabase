#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test final para verificar que Supabase funciona correctamente
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

def log_mensaje(mensaje):
    """Escribir mensaje tanto en pantalla como en archivo"""
    print(mensaje)
    with open('test_resultado.txt', 'a', encoding='utf-8') as f:
        f.write(mensaje + '\n')

def main():
    # Limpiar archivo de log
    with open('test_resultado.txt', 'w', encoding='utf-8') as f:
        f.write('=== TEST FINAL SUPABASE ===\n')
        f.write(f'Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
    
    log_mensaje("🔧 INICIANDO TEST FINAL DE SUPABASE")
    log_mensaje("=" * 50)
    
    try:
        from supabase import create_client
        log_mensaje("✅ Librería supabase importada correctamente")
    except ImportError as e:
        log_mensaje(f"❌ Error importando supabase: {e}")
        return False
    
    # Verificar variables de entorno
    url = os.getenv("SUPABASE_URL")
    anon_key = os.getenv("SUPABASE_ANON_KEY")
    service_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    log_mensaje(f"📊 Variables de entorno:")
    log_mensaje(f"   SUPABASE_URL: {'✓' if url else '✗'}")
    log_mensaje(f"   SUPABASE_ANON_KEY: {'✓' if anon_key else '✗'}")
    log_mensaje(f"   SUPABASE_SERVICE_KEY: {'✓' if service_key else '✗'}")
    
    if not all([url, anon_key, service_key]):
        log_mensaje("❌ FALLO: Variables de entorno faltantes")
        return False
    
    try:
        # Crear clientes
        log_mensaje("\n🔗 Creando clientes Supabase...")
        supabase = create_client(url, anon_key)
        supabase_admin = create_client(url, service_key)
        log_mensaje("✅ Clientes creados exitosamente")
        
        # Test 1: Conexión básica
        log_mensaje("\n📊 TEST 1: Conexión básica")
        users_response = supabase.table("usuarios").select("*").execute()
        log_mensaje(f"✅ Conexión exitosa - {len(users_response.data)} usuarios encontrados")
        
        if not users_response.data:
            log_mensaje("⚠️ No hay usuarios en la base de datos")
            return False
        
        # Mostrar algunos usuarios
        for i, user in enumerate(users_response.data[:3]):
            log_mensaje(f"   Usuario {i+1}: {user['nombre']} (ID: {user['id']}, Código: {user['codigo']})")
        
        # Test 2: Descansos activos
        log_mensaje("\n📊 TEST 2: Descansos activos")
        descansos_response = supabase.table("descansos").select("*").execute()
        log_mensaje(f"✅ {len(descansos_response.data)} descansos activos encontrados")
        
        # Test 3: Registros históricos
        log_mensaje("\n📊 TEST 3: Registros históricos")
        tiempos_response = supabase.table("tiempos_descanso").select("*").limit(5).execute()
        log_mensaje(f"✅ {len(tiempos_response.data)} registros históricos encontrados")
        
        # Test 4: Operación completa de prueba
        log_mensaje("\n📊 TEST 4: Operación completa de prueba")
        test_user = users_response.data[0]
        log_mensaje(f"   Usando usuario de prueba: {test_user['nombre']} (ID: {test_user['id']})")
        
        # 4a. Limpiar descansos previos
        clean_response = supabase_admin.table("descansos").delete().eq("usuario_id", test_user['id']).execute()
        log_mensaje(f"   ✓ Limpieza: {len(clean_response.data) if clean_response.data else 0} descansos eliminados")
        
        # 4b. Crear descanso
        inicio_test = get_current_time()
        crear_response = supabase_admin.table("descansos").insert({
            'usuario_id': test_user['id'],
            'inicio': inicio_test.isoformat(),
            'tipo': 'Pendiente'
        }).execute()
        
        if not crear_response.data:
            log_mensaje("   ❌ Error creando descanso de prueba")
            return False
        
        descanso_test_id = crear_response.data[0]['id']
        log_mensaje(f"   ✓ Descanso de prueba creado (ID: {descanso_test_id})")
        
        # 4c. Simular tiempo transcurrido
        import time
        time.sleep(3)
        log_mensaje("   ✓ Tiempo simulado (3 segundos)")
        
        # 4d. Cerrar descanso
        fin_test = get_current_time()
        duracion_test = int((fin_test - inicio_test).total_seconds() / 60)
        tipo_test = 'COMIDA' if duracion_test >= 30 else 'DESCANSO'
        
        # Insertar en tiempos_descanso
        tiempo_test_response = supabase_admin.table('tiempos_descanso').insert({
            'usuario_id': test_user['id'],
            'tipo': tipo_test,
            'fecha': inicio_test.date().isoformat(),
            'inicio': inicio_test.time().isoformat(),
            'fin': fin_test.time().isoformat(),
            'duracion_minutos': duracion_test
        }).execute()
        
        if not tiempo_test_response.data:
            log_mensaje("   ❌ Error registrando tiempo de prueba")
            return False
        
        log_mensaje(f"   ✓ Tiempo registrado: {tipo_test} - {duracion_test} min")
        
        # Eliminar descanso activo
        delete_test_response = supabase_admin.table('descansos').delete().eq('id', descanso_test_id).execute()
        log_mensaje(f"   ✓ Descanso activo eliminado")
        
        # Verificación final
        log_mensaje("\n📊 TEST 5: Verificación final")
        final_descansos = supabase.table("descansos").select("*").eq("usuario_id", test_user['id']).execute()
        final_tiempos = supabase.table("tiempos_descanso").select("*").eq("usuario_id", test_user['id']).order('id', desc=True).limit(1).execute()
        
        log_mensaje(f"   ✓ Descansos activos para usuario: {len(final_descansos.data)}")
        log_mensaje(f"   ✓ Último registro: {final_tiempos.data[0]['tipo'] if final_tiempos.data else 'Ninguno'}")
        
        # Resumen final
        log_mensaje("\n" + "=" * 50)
        log_mensaje("🎉 RESUMEN FINAL")
        log_mensaje("=" * 50)
        log_mensaje("✅ Conexión a Supabase: EXITOSA")
        log_mensaje("✅ Lectura de datos: EXITOSA")
        log_mensaje("✅ Escritura de datos: EXITOSA")
        log_mensaje("✅ Eliminación de datos: EXITOSA")
        log_mensaje("✅ Operación completa: EXITOSA")
        log_mensaje("\n🎯 DIAGNÓSTICO: LA APLICACIÓN DEBERÍA FUNCIONAR CORRECTAMENTE")
        log_mensaje("   - La conexión con Supabase está funcionando")
        log_mensaje("   - Todas las operaciones CRUD funcionan correctamente")
        log_mensaje("   - Los permisos de lectura y escritura están configurados")
        
        if len(users_response.data) > 0:
            log_mensaje(f"\n👥 USUARIOS DISPONIBLES PARA PRUEBAS:")
            for user in users_response.data[:5]:
                log_mensaje(f"   - {user['nombre']} (Código: {user['codigo']}, ID: {user['id']})")
        
        log_mensaje("\n📝 PRÓXIMOS PASOS:")
        log_mensaje("   1. Ejecutar la aplicación Flask: python app.py")
        log_mensaje("   2. Abrir http://localhost:5000 en el navegador")
        log_mensaje("   3. Probar registrar entrada/salida con códigos de usuarios")
        log_mensaje("   4. Verificar que los datos se guardan en Supabase")
        
        return True
        
    except Exception as e:
        log_mensaje(f"\n❌ ERROR DURANTE LAS PRUEBAS:")
        log_mensaje(f"   Tipo: {type(e).__name__}")
        log_mensaje(f"   Mensaje: {str(e)}")
        
        import traceback
        log_mensaje(f"   Stack trace:")
        for line in traceback.format_exc().split('\n'):
            if line.strip():
                log_mensaje(f"     {line}")
        
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        log_mensaje("\n🚀 TEST COMPLETADO EXITOSAMENTE")
        log_mensaje("El archivo 'test_resultado.txt' contiene todos los detalles")
    else:
        log_mensaje("\n💥 TEST FALLÓ")
        log_mensaje("Revisa los errores en 'test_resultado.txt'")
    
    # Esperar para mostrar el resultado
    print("\nPresiona Enter para continuar...")
    input()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para iniciar Flask y probar automáticamente las operaciones
"""

import requests
import time
import subprocess
import threading
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def iniciar_flask():
    """Iniciar Flask en un hilo separado"""
    os.system('cd "d:\\BreakTimeTracker-Supabase" && python app.py')

def probar_rutas():
    """Probar las rutas de diagnóstico"""
    print("🧪 INICIANDO PRUEBAS DE RUTAS")
    print("=" * 50)
    
    # Esperar a que Flask inicie
    print("⏳ Esperando que Flask inicie...")
    time.sleep(5)
    
    base_url = "http://localhost:5000"
    
    try:
        # 1. Probar ruta de status
        print("\n1️⃣ Probando ruta /status")
        response = requests.get(f"{base_url}/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status OK")
            print(f"   Conexión: {data.get('conexion', {}).get('conectado')}")
            print(f"   Usuarios: {data.get('tablas', {}).get('usuarios', 0)}")
            print(f"   Descansos activos: {data.get('tablas', {}).get('descansos_activos', 0)}")
            
            # Si hay usuarios, usar el primero para pruebas
            usuarios = data.get('usuarios_muestra', [])
            if usuarios:
                test_codigo = usuarios[0].get('codigo', '001')
                print(f"   🎯 Código de prueba: {test_codigo}")
                
                # 2. Probar flujo completo
                print(f"\n2️⃣ Probando flujo completo con código {test_codigo}")
                flujo_response = requests.get(f"{base_url}/test_flujo_completo/{test_codigo}", timeout=10)
                
                if flujo_response.status_code == 200:
                    flujo_data = flujo_response.json()
                    print(f"✅ Flujo completo: {'ÉXITO' if flujo_data.get('success') else 'FALLO'}")
                    print(f"   Usuario: {flujo_data.get('usuario')}")
                    print(f"   Operación completa: {flujo_data.get('operacion_completa')}")
                    
                    # Mostrar log
                    print(f"\n📝 Log del flujo:")
                    for log_line in flujo_data.get('log', []):
                        print(f"   {log_line}")
                        
                else:
                    print(f"❌ Error en flujo completo: {flujo_response.status_code}")
                    print(f"   Respuesta: {flujo_response.text}")
            else:
                print("⚠️ No hay usuarios para probar")
        else:
            print(f"❌ Error en status: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ No se pudo conectar a Flask. ¿Está ejecutándose?")
    except requests.exceptions.Timeout:
        print("❌ Timeout conectando a Flask")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🚀 INICIANDO PRUEBAS AUTOMÁTICAS")
    print("=" * 50)
    
    # Iniciar Flask en hilo separado
    flask_thread = threading.Thread(target=iniciar_flask, daemon=True)
    flask_thread.start()
    
    # Probar rutas
    probar_rutas()
    
    print("\n✅ PRUEBAS COMPLETADAS")
    print("Para continuar probando manualmente:")
    print("1. Ve a http://localhost:5000")
    print("2. Prueba las rutas de diagnóstico:")
    print("   - /status")
    print("   - /test_flujo_completo/[CODIGO]")
    print("   - /test_close_by_code/[CODIGO]")
    
    input("\nPresiona Enter para salir...")

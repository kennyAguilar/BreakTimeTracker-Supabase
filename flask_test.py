#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Aplicación Flask simplificada para probar operaciones básicas
"""

from flask import Flask, jsonify, request
from supabase import create_client
import pytz
from datetime import datetime
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.secret_key = 'test-key'

# Zona horaria
tz = pytz.timezone('America/Punta_Arenas')

# Cliente Supabase
url = os.getenv("SUPABASE_URL")
anon_key = os.getenv("SUPABASE_ANON_KEY") 
service_key = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(url, anon_key)
supabase_admin = create_client(url, service_key)

def get_current_time():
    return datetime.now(tz)

@app.route('/test')
def test():
    """Ruta de prueba básica"""
    try:
        # Probar conexión
        response = supabase.table("usuarios").select("*").limit(1).execute()
        return jsonify({
            "status": "success",
            "message": "Conexión exitosa",
            "data": response.data
        })
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

@app.route('/usuarios')
def listar_usuarios():
    """Listar todos los usuarios"""
    try:
        response = supabase.table("usuarios").select("*").execute()
        return jsonify({
            "status": "success",
            "count": len(response.data),
            "usuarios": response.data
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/descansos')
def listar_descansos():
    """Listar descansos activos"""
    try:
        response = supabase.table("descansos").select("*").execute()
        return jsonify({
            "status": "success", 
            "count": len(response.data),
            "descansos": response.data
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/iniciar_descanso/<int:usuario_id>', methods=['POST'])
def iniciar_descanso(usuario_id):
    """Iniciar un descanso para un usuario"""
    try:
        # Verificar que el usuario existe
        user_response = supabase.table("usuarios").select("*").eq("id", usuario_id).execute()
        
        if not user_response.data:
            return jsonify({
                "status": "error",
                "message": "Usuario no encontrado"
            }), 404
        
        usuario = user_response.data[0]
        
        # Verificar si ya tiene un descanso activo
        active_response = supabase.table("descansos").select("*").eq("usuario_id", usuario_id).execute()
        
        if active_response.data:
            return jsonify({
                "status": "error",
                "message": "El usuario ya tiene un descanso activo"
            }), 400
        
        # Crear nuevo descanso
        insert_response = supabase_admin.table('descansos').insert({
            'usuario_id': usuario_id,
            'inicio': get_current_time().isoformat(),
            'tipo': 'Pendiente'
        }).execute()
        
        return jsonify({
            "status": "success",
            "message": f"Descanso iniciado para {usuario['nombre']}",
            "descanso": insert_response.data[0]
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/cerrar_descanso/<int:usuario_id>', methods=['POST'])
def cerrar_descanso(usuario_id):
    """Cerrar el descanso activo de un usuario"""
    try:
        # Buscar descanso activo
        active_response = supabase.table("descansos").select("*").eq("usuario_id", usuario_id).execute()
        
        if not active_response.data:
            return jsonify({
                "status": "error",
                "message": "No se encontró descanso activo para este usuario"
            }), 404
        
        descanso_activo = active_response.data[0]
        
        # Calcular duración
        inicio = datetime.fromisoformat(descanso_activo['inicio'].replace('Z', '+00:00'))
        fin = get_current_time()
        duracion_minutos = int((fin - inicio).total_seconds() / 60)
        tipo = 'COMIDA' if duracion_minutos >= 30 else 'DESCANSO'
        
        # Insertar en tiempos_descanso
        insert_response = supabase_admin.table('tiempos_descanso').insert({
            'usuario_id': usuario_id,
            'tipo': tipo,
            'fecha': inicio.date().isoformat(),
            'inicio': inicio.time().isoformat(),
            'fin': fin.time().isoformat(),
            'duracion_minutos': duracion_minutos
        }).execute()
        
        # Eliminar descanso activo
        delete_response = supabase_admin.table('descansos').delete().eq('id', descanso_activo['id']).execute()
        
        return jsonify({
            "status": "success",
            "message": f"Descanso cerrado ({tipo}: {duracion_minutos} minutos)",
            "tiempo_registrado": insert_response.data[0] if insert_response.data else None,
            "descanso_eliminado": delete_response.data[0] if delete_response.data else None
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/test_completo/<int:usuario_id>')
def test_completo(usuario_id):
    """Realizar un test completo: iniciar y cerrar descanso"""
    try:
        resultado = {
            "pasos": [],
            "status": "success"
        }
        
        # Paso 1: Verificar usuario
        user_response = supabase.table("usuarios").select("*").eq("id", usuario_id).execute()
        if not user_response.data:
            return jsonify({
                "status": "error",
                "message": "Usuario no encontrado"
            }), 404
        
        usuario = user_response.data[0]
        resultado["pasos"].append(f"✓ Usuario encontrado: {usuario['nombre']}")
        
        # Paso 2: Limpiar descansos previos
        clean_response = supabase_admin.table("descansos").delete().eq("usuario_id", usuario_id).execute()
        resultado["pasos"].append(f"✓ Descansos previos limpiados: {len(clean_response.data) if clean_response.data else 0}")
        
        # Paso 3: Iniciar descanso
        insert_response = supabase_admin.table('descansos').insert({
            'usuario_id': usuario_id,
            'inicio': get_current_time().isoformat(),
            'tipo': 'Pendiente'
        }).execute()
        
        if not insert_response.data:
            resultado["status"] = "error"
            resultado["pasos"].append("✗ Error iniciando descanso")
            return jsonify(resultado), 500
        
        descanso_id = insert_response.data[0]['id']
        resultado["pasos"].append(f"✓ Descanso iniciado (ID: {descanso_id})")
        
        # Paso 4: Esperar un momento
        import time
        time.sleep(2)
        
        # Paso 5: Cerrar descanso
        descanso_activo = insert_response.data[0]
        inicio = datetime.fromisoformat(descanso_activo['inicio'].replace('Z', '+00:00'))
        fin = get_current_time()
        duracion_minutos = int((fin - inicio).total_seconds() / 60)
        tipo = 'COMIDA' if duracion_minutos >= 30 else 'DESCANSO'
        
        # Insertar tiempo
        tiempo_response = supabase_admin.table('tiempos_descanso').insert({
            'usuario_id': usuario_id,
            'tipo': tipo,
            'fecha': inicio.date().isoformat(),
            'inicio': inicio.time().isoformat(),
            'fin': fin.time().isoformat(),
            'duracion_minutos': duracion_minutos
        }).execute()
        
        # Eliminar descanso activo
        delete_response = supabase_admin.table('descansos').delete().eq('id', descanso_id).execute()
        
        resultado["pasos"].append(f"✓ Tiempo registrado: {tipo} - {duracion_minutos} min")
        resultado["pasos"].append(f"✓ Descanso activo eliminado")
        
        # Verificación final
        final_active = supabase.table("descansos").select("*").eq("usuario_id", usuario_id).execute()
        final_tiempos = supabase.table("tiempos_descanso").select("*").eq("usuario_id", usuario_id).order('id', desc=True).limit(1).execute()
        
        resultado["pasos"].append(f"✓ Verificación: {len(final_active.data)} descansos activos, {len(final_tiempos.data)} tiempos registrados")
        
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "pasos": resultado.get("pasos", [])
        }), 500

if __name__ == '__main__':
    print("🚀 Iniciando servidor Flask de prueba...")
    print("📊 Rutas disponibles:")
    print("   GET  /test - Prueba básica de conexión")
    print("   GET  /usuarios - Listar usuarios")
    print("   GET  /descansos - Listar descansos activos")
    print("   POST /iniciar_descanso/<usuario_id> - Iniciar descanso")
    print("   POST /cerrar_descanso/<usuario_id> - Cerrar descanso")
    print("   GET  /test_completo/<usuario_id> - Test completo")
    print("🌐 Servidor disponible en: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)

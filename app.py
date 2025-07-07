from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from supabase import create_client, Client
import pytz
from datetime import datetime, timedelta, date
import os
from dotenv import load_dotenv
import csv
import io
import traceback
from functools import wraps

# Importar utilidades de parsing de tarjetas
from tarjeta_utils import parse_card_data, validate_card_format, get_card_info, debug_card_parsing

# Importar utilidades de tiempo
from time_utils import get_current_time, get_current_time_formatted, format_datetime_for_display, format_time_only

# Importar módulo de base de datos
import db_utils

# Cargar variables de entorno
load_dotenv()

# Configuración Flask
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

# Estado de conexión global para mostrar en la interfaz
conexion_supabase_status = {
    'conectado': False,
    'mensaje': '',
    'detalle': ''
}

# Cliente Supabase
try:
    print("Iniciando conexión a Supabase...")
    
    # Verificar variables de entorno
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_anon_key = os.getenv('SUPABASE_ANON_KEY')
    supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    print(f"SUPABASE_URL: {'CONFIGURADA' if supabase_url else 'NO ENCONTRADA'}")
    print(f"SUPABASE_ANON_KEY: {'CONFIGURADA' if supabase_anon_key else 'NO ENCONTRADA'}")
    print(f"SUPABASE_SERVICE_KEY: {'CONFIGURADA' if supabase_service_key else 'NO ENCONTRADA'}")
    
    if not supabase_url or not supabase_anon_key or not supabase_service_key:
        conexion_supabase_status.update({
            'conectado': False,
            'mensaje': 'Error: Variables de entorno faltantes',
            'detalle': 'Verifica el archivo .env'
        })
        print("❌ Error: Variables de entorno de Supabase no están configuradas")
        print("Verifica que el archivo .env contenga:")
        print("SUPABASE_URL=https://tu-proyecto.supabase.co")
        print("SUPABASE_ANON_KEY=tu-anon-key")
        print("SUPABASE_SERVICE_KEY=tu-service-key")
        exit(1)
    
    # Intentar crear clientes con configuración específica para producción
    print("🔗 Creando cliente público...")
    try:
        # Configuración específica para evitar problemas de proxy
        from supabase import ClientOptions
        options = ClientOptions()
        supabase: Client = create_client(supabase_url, supabase_anon_key, options)
    except Exception as client_error:
        print(f"⚠️ Error con opciones específicas, intentando configuración básica: {client_error}")
        # Fallback a configuración básica
        supabase: Client = create_client(supabase_url, supabase_anon_key)
    
    print("🔗 Creando cliente administrativo...")
    try:
        from supabase import ClientOptions
        options_admin = ClientOptions()
        supabase_admin: Client = create_client(supabase_url, supabase_service_key, options_admin)
    except Exception as admin_error:
        print(f"⚠️ Error con opciones específicas para admin, intentando configuración básica: {admin_error}")
        # Fallback a configuración básica
        supabase_admin: Client = create_client(supabase_url, supabase_service_key)
    
    # Probar conexión básica
    print("🧪 Probando conexión...")
    test_response = supabase.table('usuarios').select("id").limit(1).execute()
    print(f"✅ Conexión exitosa - Respuesta: {len(test_response.data) if test_response.data else 0} registros")
    
    conexion_supabase_status.update({
        'conectado': True,
        'mensaje': 'Conexión establecida correctamente',
        'detalle': f'Usuarios en BD: {len(test_response.data) if test_response.data else 0}'
    })
    
    print("✅ Conexión a Supabase establecida correctamente")
    
    # Inicializar clientes en db_utils
    import db_utils
    db_utils.initialize_db_clients(supabase, supabase_admin)
    
except Exception as e:
    conexion_supabase_status.update({
        'conectado': False,
        'mensaje': f'Error de conexión: {str(e)}',
        'detalle': f'Tipo: {type(e).__name__}'
    })
    
    print(f"❌ Error detallado conectando a Supabase:")
    print(f"   Tipo de error: {type(e).__name__}")
    print(f"   Mensaje: {str(e)}")
    
    import traceback
    print(f"   Stack trace: {traceback.format_exc()}")
    
    print("\n🔧 Posibles soluciones:")
    print("1. Verificar que el archivo .env existe y contiene las variables correctas")
    print("2. Verificar que las credenciales de Supabase son válidas")
    print("3. Verificar conexión a internet")
    print("4. Verificar que las tablas existen en Supabase")
    
    exit(1)

# Zona horaria (importada de time_utils)
from time_utils import TZ as tz

# Decorador para rutas protegidas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            # Pasar solo la ruta como parámetro 'next'
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

# Función auxiliar para cerrar un descanso
def cerrar_descanso_usuario(usuario_id, descanso_activo):
    """
    Función dedicada para cerrar un descanso de usuario
    Retorna: (success: bool, mensaje: str, detalle: dict)
    """
    try:
        print(f"🔄 Iniciando proceso de cierre para usuario ID: {usuario_id}")
        print(f"   Descanso a cerrar: ID {descanso_activo['id']}")
        
        # Calcular duración
        inicio = datetime.fromisoformat(descanso_activo['inicio'].replace('Z', '+00:00'))
        if inicio.tzinfo is None:
            inicio = inicio.replace(tzinfo=pytz.UTC)
        
        fin = get_current_time()  # Usar hora local
        duracion_minutos = max(1, int((fin - inicio).total_seconds() / 60))  # Mínimo 1 minuto
        tipo = 'COMIDA' if duracion_minutos >= 30 else 'DESCANSO'
        
        print(f"   Duración: {duracion_minutos} min → {tipo}")
        
        # Convertir ambos tiempos a la misma zona horaria (local)
        inicio_local = inicio.astimezone(tz)
        fin_local = fin  # ya está en hora local
        
        print(f"   🕐 Conversión de tiempos:")
        print(f"      Inicio UTC: {inicio.strftime('%H:%M:%S %Z')}")
        print(f"      Inicio Local: {inicio_local.strftime('%H:%M:%S %Z')}")
        print(f"      Fin Local: {fin_local.strftime('%H:%M:%S %Z')}")
        
        # Preparar datos para tiempos_descanso
        tiempo_data = {
            'usuario_id': usuario_id,
            'tipo': tipo,
            'fecha': inicio_local.date().isoformat(),
            'inicio': inicio_local.time().isoformat(),
            'fin': fin_local.time().isoformat(),
            'duracion_minutos': duracion_minutos
        }
        
        print(f"   📊 Datos a insertar:")
        print(f"      Fecha: {tiempo_data['fecha']}")
        print(f"      Inicio: {tiempo_data['inicio']}")
        print(f"      Fin: {tiempo_data['fin']}")
        print(f"      Duración: {tiempo_data['duracion_minutos']} min")
        
        # Paso 1: Insertar en tiempos_descanso
        print(f"   📝 Insertando tiempo de descanso...")
        insert_response = supabase_admin.table('tiempos_descanso').insert(tiempo_data).execute()
        
        if not insert_response.data:
            error_msg = "Error insertando en tiempos_descanso"
            print(f"   ❌ {error_msg}")
            return False, error_msg, {'insert_response': insert_response}
        
        tiempo_id = insert_response.data[0]['id']
        print(f"   ✅ Tiempo insertado con ID: {tiempo_id}")
        
        # Paso 2: Eliminar de descansos
        print(f"   🗑️ Eliminando descanso activo...")
        delete_response = supabase_admin.table('descansos').delete().eq('id', descanso_activo['id']).execute()
        
        if delete_response.data:
            print(f"   ✅ Descanso eliminado: {len(delete_response.data)} registros")
        else:
            print(f"   ⚠️ ADVERTENCIA: No se confirmó eliminación - Error: {delete_response.error if hasattr(delete_response, 'error') else 'Sin error'}")

        # Paso 3: Verificación final
        verify_response = supabase_admin.table('descansos').select("*").eq('usuario_id', usuario_id).execute()
        descansos_restantes = len(verify_response.data)
        print(f"   🔍 Verificación: {descansos_restantes} descansos activos restantes")
        
        if descansos_restantes > 0:
            print(f"   ⚠️ PROBLEMA: Quedan descansos activos")
            for resto in verify_response.data:
                print(f"      - ID {resto['id']}, Inicio: {resto['inicio']}")
        
        success_msg = f"Descanso cerrado: {tipo} de {duracion_minutos} min"
        print(f"   ✅ ÉXITO: {success_msg}")
        
        return True, success_msg, {
            'tiempo_id': tiempo_id,
            'tipo': tipo,
            'duracion_minutos': duracion_minutos,
            'descansos_restantes': descansos_restantes
        }
        
    except Exception as e:
        error_msg = f"Error cerrando descanso: {str(e)}"
        print(f"   ❌ ERROR CRÍTICO: {error_msg}")
        import traceback
        print(f"   Stack trace: {traceback.format_exc()}")
        return False, error_msg, {'exception': str(e)}

# Función auxiliar para obtener hora actual en Punta Arenas (duplicada, eliminamos esta línea)
# def get_current_time():
#     return datetime.now(tz)

# Ruta principal - Lector de tarjetas
@app.route('/', methods=['GET', 'POST'])
def index():
    # TEMPORALMENTE COMENTADO: Si hay admin logueado, redirigir a registros
    # if 'admin_id' in session:
    #     return redirect(url_for('registros'))
    
    mensaje = None
    tipo_mensaje = None
    
    if request.method == 'POST':
        entrada_raw = request.form.get('entrada', '').strip()
        
        if entrada_raw:
            # ✨ NUEVA FUNCIONALIDAD: Parsear datos de tarjeta con banda magnética
            entrada = parse_card_data(entrada_raw)
            
            print(f"🔍 Procesando entrada:")
            print(f"   Datos crudos: '{entrada_raw}'")
            print(f"   Datos parseados: '{entrada}'")
            
            # Validar formato de tarjeta
            if not validate_card_format(entrada):
                print(f"⚠️ Formato de tarjeta inválido")
                mensaje = "Formato de tarjeta inválido. Intente nuevamente."
                tipo_mensaje = "error"
            else:
                try:
                    # Importar funciones de búsqueda
                    from db_utils import buscar_usuario_inteligente, obtener_descanso_activo, crear_descanso
                    
                    # Usar búsqueda inteligente centralizada
                    print(f"🔍 Iniciando búsqueda inteligente para: '{entrada}'")
                    usuario = buscar_usuario_inteligente(entrada)
                    
                    # Si no se encuentra con datos parseados, intentar con datos originales
                    if not usuario and entrada != entrada_raw:
                        print(f"🔄 Intentando con datos originales como fallback...")
                        usuario = buscar_usuario_inteligente(entrada_raw)
                    
                    if usuario:
                        print(f"👤 Usuario encontrado: {usuario['nombre']} (ID: {usuario['id']})")
                        
                        # Verificar si tiene descanso activo usando db_utils
                        descanso_activo = obtener_descanso_activo(usuario['id'])
                        
                        if descanso_activo:
                            print(f"🚪 PROCESANDO SALIDA DE DESCANSO")
                            print(f"   Usuario: {usuario['nombre']} (ID: {usuario['id']})")
                            print(f"   Descanso ID: {descanso_activo['id']}")
                            
                            # Usar función helper para cerrar descanso
                            success, resultado_msg, detalle = cerrar_descanso_usuario(usuario['id'], descanso_activo)
                            
                            if success:
                                mensaje = f"{usuario['nombre']} - Salida registrada ({resultado_msg})"
                                tipo_mensaje = "salida"
                                print(f"🎉 SALIDA PROCESADA EXITOSAMENTE: {resultado_msg}")
                            else:
                                mensaje = f"Error al registrar salida de {usuario['nombre']}: {resultado_msg}"
                                tipo_mensaje = "error"
                                print(f"❌ FALLO EN SALIDA: {resultado_msg}")
                                print(f"   Detalles: {detalle}")
                                
                        else:
                            # Registrar entrada a descanso usando db_utils
                            descanso_creado = crear_descanso(usuario['id'], get_current_time().isoformat())
                            
                            if descanso_creado:
                                print(f"✅ Entrada registrada: {descanso_creado}")
                                mensaje = f"{usuario['nombre']} - Entrada a descanso registrada"
                                tipo_mensaje = "entrada"
                            else:
                                mensaje = f"Error al registrar entrada para {usuario['nombre']}"
                                tipo_mensaje = "error"
                    else:
                        mensaje = "Usuario no encontrado"
                        tipo_mensaje = "error"
                        
                except Exception as e:
                    mensaje = f"Error al procesar: {str(e)}"
                    tipo_mensaje = "error"
    
    # Obtener usuarios en descanso con información de usuario
    usuarios_en_descanso = []
    try:
        print(f"\n🔍 === OBTENIENDO USUARIOS EN DESCANSO ===")
        
        # Usar utilidad centralizada para obtener descansos activos
        from db_utils import obtener_todos_descansos_activos
        descansos_activos = obtener_todos_descansos_activos()
        
        print(f"📊 Descansos activos encontrados: {len(descansos_activos)}")
        
        if len(descansos_activos) == 0:
            print(f"ℹ️ No hay descansos activos en la tabla 'descansos'")
        else:
            print(f"📋 Lista de descansos activos:")
            for i, d in enumerate(descansos_activos):
                print(f"   {i+1}. ID: {d['id']}, Usuario ID: {d['usuario_id']}, Inicio: {d['inicio']}")
        
        # Procesar cada descanso activo
        for i, d in enumerate(descansos_activos):
            print(f"\n👤 Procesando descanso {i+1}/{len(descansos_activos)}:")
            print(f"   Descanso ID: {d['id']}")
            print(f"   Usuario ID: {d['usuario_id']}")
            print(f"   Inicio: {d['inicio']}")
            
            try:
                # Obtener información del usuario para cada descanso
                print(f"   🔍 Buscando información del usuario ID {d['usuario_id']}...")
                user_response = supabase.table('usuarios').select("nombre, codigo").eq('id', d['usuario_id']).execute()
                
                print(f"   📊 Respuesta de usuario: {len(user_response.data)} registros encontrados")
                
                if user_response.data:
                    usuario_info = user_response.data[0]
                    print(f"   ✅ Usuario encontrado: {usuario_info['nombre']} (Código: {usuario_info['codigo']})")
                    
                    # Calcular tiempo transcurrido
                    try:
                        # Procesar hora de inicio asegurando zona horaria consistente
                        inicio = datetime.fromisoformat(d['inicio'].replace('Z', '+00:00'))
                        if inicio.tzinfo is None:
                            inicio = inicio.replace(tzinfo=pytz.UTC)
                        
                        # Convertir inicio a zona horaria local para comparar
                        inicio_local = inicio.astimezone(tz)
                        ahora = get_current_time()  # Ya está en hora local
                        
                        # Calcular diferencia en minutos
                        diferencia_segundos = (ahora - inicio_local).total_seconds()
                        tiempo_transcurrido = int(diferencia_segundos / 60)
                        
                        # Debug: mostrar cálculos detallados
                        print(f"   ⏰ Cálculo de tiempo:")
                        print(f"      Inicio UTC: {inicio.strftime('%H:%M:%S %Z')}")
                        print(f"      Inicio Local: {inicio_local.strftime('%H:%M:%S %Z')}")
                        print(f"      Ahora Local: {ahora.strftime('%H:%M:%S %Z')}")
                        print(f"      Diferencia segundos: {diferencia_segundos}")
                        print(f"      Tiempo transcurrido: {tiempo_transcurrido} minutos")
                        
                        # Si el tiempo es negativo, podría ser un problema de sincronización
                        if tiempo_transcurrido < 0:
                            print(f"   ⚠️ ADVERTENCIA: Tiempo negativo detectado ({tiempo_transcurrido} min)")
                            print(f"      Esto podría indicar un problema de sincronización de tiempo")
                            # Forzar a 0 para evitar valores negativos en la UI
                            tiempo_transcurrido = 0
                        
                        # Determinar tiempo máximo según el tiempo transcurrido
                        tiempo_maximo = 40 if tiempo_transcurrido >= 20 else 20
                        tiempo_restante = max(0, tiempo_maximo - tiempo_transcurrido)
                        tipo_probable = 'COMIDA' if tiempo_transcurrido >= 20 else 'DESCANSO'
                        
                        # Asegurar que los valores sean números válidos y no negativos
                        tiempo_transcurrido = max(0, tiempo_transcurrido)
                        tiempo_restante = max(0, tiempo_restante)
                        
                        print(f"   📋 Tipo probable: {tipo_probable}")
                        print(f"   ⏳ Tiempo restante: {tiempo_restante} min")
                        
                        usuario_descanso = {
                            'nombre': usuario_info['nombre'],
                            'codigo': usuario_info['codigo'],
                            'tiempo_transcurrido': tiempo_transcurrido,
                            'tiempo_restante': tiempo_restante,
                            'tipo_probable': tipo_probable,
                            'inicio_formateado': inicio.astimezone(tz).strftime('%H:%M'),  # Para mostrar
                            'inicio_iso': inicio.isoformat()  # Para cálculos de JavaScript
                        }
                        
                        usuarios_en_descanso.append(usuario_descanso)
                        print(f"   ✅ Usuario agregado a la lista de descansos")
                        
                    except Exception as e_tiempo:
                        print(f"   ❌ Error calculando tiempo para usuario {usuario_info['nombre']}: {e_tiempo}")
                        
                else:
                    print(f"   ⚠️ PROBLEMA: No se encontró información para usuario ID {d['usuario_id']}")
                    print(f"      Esto podría indicar que el usuario fue eliminado pero tiene descansos activos")
                    
            except Exception as e_usuario:
                print(f"   ❌ Error procesando descanso individual (ID: {d['id']}): {e_usuario}")
                print(f"   Stack trace: {traceback.format_exc()}")
        
        print(f"\n📊 RESUMEN FINAL:")
        print(f"   Total descansos activos en BD: {len(descansos_activos)}")
        print(f"   Total usuarios procesados exitosamente: {len(usuarios_en_descanso)}")
        
        if len(usuarios_en_descanso) > 0:
            print(f"   👥 Usuarios en descanso para mostrar:")
            for u in usuarios_en_descanso:
                print(f"      - {u['nombre']} ({u['codigo']}) - {u['tiempo_transcurrido']} min")
        else:
            print(f"   ℹ️ No hay usuarios en descanso para mostrar")
            
    except Exception as e:
        print(f"❌ ERROR CRÍTICO al obtener descansos: {e}")
        print(f"Stack trace completo: {traceback.format_exc()}")
        usuarios_en_descanso = []
    
    return render_template('index.html',
                         descansos=usuarios_en_descanso,
                         hora_actual=get_current_time_formatted(),
                         mensaje=mensaje,
                         tipo_mensaje=tipo_mensaje,
                         conexion_status=conexion_supabase_status)

# Login administrativo
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Debug: mostrar parámetro next
    next_page = request.args.get('next')
    print(f"🔍 Login accedido con parámetro next: '{next_page}'")
    
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        clave = request.form.get('clave', '').strip()
        
        print(f"🔐 Intento de login:")
        print(f"   Usuario recibido: '{usuario}'")
        print(f"   Clave recibida: '{clave}'")
        
        try:
            # Buscar administrador usando cliente administrativo
            print(f"   Buscando administrador en BD...")
            response = supabase_admin.table('administradores').select("*").eq('usuario', usuario).eq('activo', True).execute()
            
            print(f"   Respuesta BD: {len(response.data) if response.data else 0} resultados")
            
            if response.data:
                admin = response.data[0]
                print(f"   Admin encontrado:")
                print(f"      ID: {admin['id']}")
                print(f"      Usuario: '{admin['usuario']}'")
                print(f"      Nombre: '{admin['nombre']}'")
                print(f"      Clave BD: '{admin['clave']}'")
                print(f"      Activo: {admin['activo']}")
                
                if admin['clave'] == clave:
                    print(f"   ✅ Credenciales válidas - Iniciando sesión")
                    session.permanent = True
                    session['admin_id'] = admin['id']
                    session['admin_nombre'] = admin['nombre']
                    session['last_activity'] = datetime.now().isoformat()
                    
                    # Verificar si hay un destino específico
                    next_page = request.args.get('next')
                    if next_page and next_page in ['/base_datos', '/registros', '/reportes']:
                        print(f"   🎯 Redirigiendo a página solicitada: {next_page}")
                        return redirect(next_page)
                    else:
                        print(f"   🎯 Redirigiendo a página por defecto: registros")
                        return redirect(url_for('registros'))
                else:
                    print(f"   ❌ Clave incorrecta: '{clave}' != '{admin['clave']}'")
                    return render_template('login.html', error=f'Credenciales inválidas. Usuario: {usuario}, Clave esperada: {admin["clave"]}')
            else:
                print(f"   ❌ Usuario no encontrado o inactivo")
                return render_template('login.html', error=f'Usuario "{usuario}" no encontrado o inactivo')
                
        except Exception as e:
            print(f"   ❌ Error en login: {e}")
            import traceback
            print(f"   Stack trace: {traceback.format_exc()}")
            return render_template('login.html', error=f'Error al verificar credenciales: {str(e)}')
    
    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Gestión de base de datos (usuarios)
@app.route('/base_datos', methods=['GET', 'POST'])
@login_required
def base_datos():
    mensaje = None
    tipo_mensaje = None
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        try:
            if action == 'add':
                # Agregar nuevo usuario
                nombre = request.form.get('nombre', '').strip()
                tarjeta = request.form.get('tarjeta', '').strip()
                turno = request.form.get('turno', '').strip()
                codigo = request.form.get('codigo', '').strip().upper()
                
                print(f"🔍 Creando usuario - Action: {action}")
                print(f"   Nombre: '{nombre}', Tarjeta: '{tarjeta}', Turno: '{turno}', Código: '{codigo}'")
                
                if nombre and tarjeta and turno and codigo:
                    # Verificar si el código ya existe
                    existing = supabase.table('usuarios').select("id").eq('codigo', codigo).execute()
                    if existing.data:
                        mensaje = f"Ya existe un usuario con el código {codigo}"
                        tipo_mensaje = "error"
                    else:
                        # DEBUG: Imprimir valores exactos antes de crear
                        print(f"🔍 VALORES EXACTOS A INSERTAR:")
                        print(f"   nombre: '{nombre}' (tipo: {type(nombre)})")
                        print(f"   tarjeta: '{tarjeta}' (tipo: {type(tarjeta)})")
                        print(f"   turno: '{turno}' (tipo: {type(turno)})")
                        print(f"   codigo: '{codigo}' (tipo: {type(codigo)})")
                        
                        # Crear usuario
                        try:
                            result = supabase_admin.table('usuarios').insert({
                                'nombre': nombre,
                                'tarjeta': tarjeta,
                                'turno': turno,
                                'codigo': codigo
                            }).execute()
                            
                            print(f"✅ Usuario creado exitosamente: {result}")
                            mensaje = f"Usuario {nombre} creado exitosamente"
                            tipo_mensaje = "success"
                            
                        except Exception as create_error:
                            print(f"❌ ERROR ESPECÍFICO AL CREAR: {create_error}")
                            if "usuarios_turno_check" in str(create_error):
                                # Error de restricción de turno - la BD debería estar corregida
                                mensaje = f"Error de restricción de turno: '{turno}' no está permitido. Valores válidos: 'Full', 'Part Time', 'Llamado'"
                                print("⚠️ Error de restricción - revisar que la BD esté actualizada")
                            else:
                                mensaje = f"Error al crear usuario: {str(create_error)}"
                            tipo_mensaje = "error"
                else:
                    mensaje = "Todos los campos son obligatorios"
                    tipo_mensaje = "error"
                    print(f"❌ Campos faltantes - Nombre: {bool(nombre)}, Tarjeta: {bool(tarjeta)}, Turno: {bool(turno)}, Código: {bool(codigo)}")
                    
            elif action == 'delete':
                # Eliminar usuario
                user_id = request.form.get('user_id')
                print(f"🗑️ Eliminando usuario ID: {user_id}")
                
                if user_id:
                    # Obtener nombre del usuario antes de eliminar
                    user_info = supabase.table('usuarios').select("nombre").eq('id', user_id).execute()
                    nombre_usuario = user_info.data[0]['nombre'] if user_info.data else "Usuario"
                    
                    # Eliminar usuario
                    result = supabase_admin.table('usuarios').delete().eq('id', user_id).execute()
                    print(f"✅ Usuario eliminado: {result}")
                    mensaje = f"Usuario {nombre_usuario} eliminado exitosamente"
                    tipo_mensaje = "success"
                else:
                    mensaje = "ID de usuario no válido"
                    tipo_mensaje = "error"
            else:
                mensaje = "Acción no válida"
                tipo_mensaje = "error"
                print(f"❌ Acción no reconocida: '{action}'")
                    
        except Exception as e:
            print(f"❌ Error en base_datos: {e}")
            mensaje = f"Error: {str(e)}"
            tipo_mensaje = "error"
    
    # Obtener todos los usuarios
    try:
        response = supabase.table('usuarios').select("*").order('nombre').execute()
        usuarios = response.data
        print(f"📊 Usuarios obtenidos: {len(usuarios)}")
    except Exception as e:
        usuarios = []
        print(f"❌ Error al obtener usuarios: {e}")
        if not mensaje:  # Solo mostrar este error si no hay otro mensaje
            mensaje = "Error al cargar la lista de usuarios"
            tipo_mensaje = "error"
    
    return render_template('base_datos.html', usuarios=usuarios, mensaje=mensaje, tipo_mensaje=tipo_mensaje)

# Editar usuario
@app.route('/editar_usuario/<user_id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(user_id):
    mensaje = None
    tipo_mensaje = None
    
    if request.method == 'POST':
        try:
            # Actualizar usuario
            nombre = request.form.get('nombre', '').strip()
            tarjeta = request.form.get('tarjeta', '').strip()
            turno = request.form.get('turno', '').strip()
            codigo = request.form.get('codigo', '').strip().upper()
            
            print(f"🔄 Actualizando usuario ID: {user_id}")
            print(f"   Nuevos valores - Nombre: '{nombre}', Tarjeta: '{tarjeta}', Turno: '{turno}', Código: '{codigo}'")
            
            if nombre and tarjeta and turno and codigo:
                try:
                    result = supabase_admin.table('usuarios').update({
                        'nombre': nombre,
                        'tarjeta': tarjeta,
                        'turno': turno,
                        'codigo': codigo
                    }).eq('id', user_id).execute()
                    
                    print(f"✅ Usuario actualizado exitosamente: {result}")
                    return redirect(url_for('base_datos'))
                    
                except Exception as update_error:
                    print(f"❌ ERROR AL ACTUALIZAR: {update_error}")
                    if "usuarios_turno_check" in str(update_error):
                        mensaje = f"""
                        ERROR DE RESTRICCIÓN DE BASE DE DATOS
                        
                        El turno '{turno}' no está permitido por la restricción de la base de datos.
                        
                        SOLUCIÓN: Ejecuta estos comandos en Supabase SQL Editor:
                        
                        ALTER TABLE usuarios DROP CONSTRAINT IF EXISTS usuarios_turno_check;
                        ALTER TABLE usuarios ADD CONSTRAINT usuarios_turno_check CHECK (turno IN ('Full', 'Part Time', 'Llamado'));
                        """
                    else:
                        mensaje = f"Error al actualizar usuario: {str(update_error)}"
                    tipo_mensaje = "error"
            else:
                mensaje = "Todos los campos son obligatorios"
                tipo_mensaje = "error"
                
        except Exception as e:
            print(f"Error general al actualizar usuario: {e}")
            mensaje = f"Error: {str(e)}"
            tipo_mensaje = "error"
    
    # Obtener usuario
    try:
        response = supabase.table('usuarios').select("*").eq('id', user_id).execute()
        usuario = response.data[0] if response.data else None
        
        if not usuario:
            return redirect(url_for('base_datos'))
            
        return render_template('editar_usuario.html', usuario=usuario, mensaje=mensaje, tipo_mensaje=tipo_mensaje)
    except Exception as e:
        print(f"Error al obtener usuario: {e}")
        return redirect(url_for('base_datos'))

# Ver registros
@app.route('/registros')
@login_required
def registros():
    # Obtener parámetros de filtro con múltiples nombres posibles
    fecha_inicio = request.args.get('fecha_inicio') or request.args.get('jornada_inicio', '')
    fecha_fin = request.args.get('fecha_fin') or request.args.get('jornada_fin', '')
    usuario_id = request.args.get('usuario_id', '')
    usuario_nombre = request.args.get('usuario', '')
    filtro_rapido = request.args.get('filtro_rapido', '')
    tipo_descanso = request.args.get('tipo', '')
    
    print(f"🔍 Parámetros de filtro recibidos:")
    print(f"   fecha_inicio: '{fecha_inicio}'")
    print(f"   fecha_fin: '{fecha_fin}'")
    print(f"   usuario_id: '{usuario_id}'")
    print(f"   usuario_nombre: '{usuario_nombre}'")
    print(f"   filtro_rapido: '{filtro_rapido}'")
    print(f"   tipo_descanso: '{tipo_descanso}'")
    
    # Procesar filtros rápidos
    if filtro_rapido:
        if filtro_rapido == 'hoy':
            fecha_inicio = date.today().isoformat()
            fecha_fin = date.today().isoformat()
        elif filtro_rapido == 'ayer':
            ayer = date.today() - timedelta(days=1)
            fecha_inicio = ayer.isoformat()
            fecha_fin = ayer.isoformat()
        elif filtro_rapido == 'semana':
            fecha_inicio = (date.today() - timedelta(days=7)).isoformat()
            fecha_fin = date.today().isoformat()
        elif filtro_rapido == 'mes':
            fecha_inicio = (date.today() - timedelta(days=30)).isoformat()
            fecha_fin = date.today().isoformat()
        print(f"   Filtro rápido aplicado: {fecha_inicio} a {fecha_fin}")
    
    # Si no hay fechas, usar últimos 7 días
    if not fecha_inicio:
        fecha_inicio = (date.today() - timedelta(days=7)).isoformat()
    if not fecha_fin:
        fecha_fin = date.today().isoformat()
    
    try:
        # Construir query base
        query = supabase.table('tiempos_descanso').select("*, usuarios(id, nombre, codigo)")
        
        # Aplicar filtros de fecha
        query = query.gte('fecha', fecha_inicio).lte('fecha', fecha_fin)
        print(f"   Filtro de fecha aplicado: {fecha_inicio} a {fecha_fin}")
        
        # Filtro por usuario (puede ser por ID o por nombre)
        if usuario_id:
            query = query.eq('usuario_id', usuario_id)
            print(f"   Filtro por usuario_id: {usuario_id}")
        elif usuario_nombre:
            # Buscar el ID del usuario por su nombre
            user_response = supabase.table('usuarios').select("id").eq('nombre', usuario_nombre).execute()
            if user_response.data:
                usuario_id = user_response.data[0]['id']
                query = query.eq('usuario_id', usuario_id)
                print(f"   Filtro por usuario_nombre '{usuario_nombre}' → ID: {usuario_id}")
            else:
                print(f"   ⚠️ Usuario '{usuario_nombre}' no encontrado")
        
        # Filtro por tipo de descanso
        if tipo_descanso:
            query = query.eq('tipo', tipo_descanso)
            print(f"   Filtro por tipo: {tipo_descanso}")
        
        # Ejecutar query
        response = query.order('fecha', desc=True).order('inicio', desc=True).execute()
        registros = response.data or []
        
        print(f"📊 Registros obtenidos después de filtros: {len(registros)}")
        
        # Formatear registros para mostrar
        for r in registros:
            r['fecha_formateada'] = datetime.fromisoformat(r['fecha']).strftime('%d/%m/%Y')
            r['duracion_formateada'] = f"{r['duracion_minutos']} min"
        
        # Obtener lista de usuarios para el filtro
        response_usuarios = supabase.table('usuarios').select("id, nombre").order('nombre').execute()
        usuarios = response_usuarios.data or []
        
        # Calcular estadísticas básicas
        total_registros = len(registros)
        total_descansos = len([r for r in registros if r['tipo'] == 'DESCANSO'])
        total_comidas = len([r for r in registros if r['tipo'] == 'COMIDA'])
        tiempo_total = sum(r['duracion_minutos'] for r in registros)
        
        estadisticas = {
            'total_registros': total_registros,
            'total_descansos': total_descansos,
            'total_comidas': total_comidas,
            'tiempo_total': tiempo_total,
            'promedio_duracion': round(tiempo_total / total_registros, 1) if total_registros > 0 else 0
        }
        
        # Preparar objeto de filtros para el template
        filtros_aplicados = {
            'filtro_rapido': filtro_rapido,
            'jornada_inicio': fecha_inicio,
            'jornada_fin': fecha_fin,
            'usuario': usuario_nombre,
            'tipo': tipo_descanso
        }
        
        print(f"✅ Renderizando template con {len(registros)} registros")
        
    except Exception as e:
        print(f"❌ Error al obtener registros: {e}")
        print(f"📍 Stack trace: {traceback.format_exc()}")
        registros = []
        usuarios = []
        estadisticas = {
            'total_registros': 0,
            'total_descansos': 0,
            'total_comidas': 0,
            'tiempo_total': 0,
            'promedio_duracion': 0
        }
        filtros_aplicados = {}
    
    return render_template('registros.html',
                         registros=registros,
                         usuarios=usuarios,
                         usuarios_disponibles=usuarios,  # Para el select del template
                         fecha_inicio=fecha_inicio,
                         fecha_fin=fecha_fin,
                         usuario_id=usuario_id,
                         estadisticas=estadisticas,
                         filtros=filtros_aplicados)

# Reportes y estadísticas
@app.route('/reportes')
@login_required
def reportes():
    # Obtener parámetros
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')
    
    # Si no hay fechas, usar último mes
    if not fecha_inicio:
        fecha_inicio = (date.today() - timedelta(days=30)).isoformat()
    if not fecha_fin:
        fecha_fin = date.today().isoformat()
    
    try:
        # Obtener todos los registros del período con manejo de errores mejorado
        print(f"🔍 Obteniendo reportes para período: {fecha_inicio} a {fecha_fin}")
        
        response = supabase.table('tiempos_descanso').select("*, usuarios(nombre, codigo)")\
            .gte('fecha', fecha_inicio)\
            .lte('fecha', fecha_fin)\
            .execute()
        
        registros = response.data if response.data else []
        print(f"📊 Registros obtenidos: {len(registros)}")
        
        # Filtrar registros con datos válidos
        registros_validos = []
        for r in registros:
            if r and r.get('usuarios') and r.get('usuarios', {}).get('nombre'):
                registros_validos.append(r)
            else:
                print(f"⚠️ Registro con datos incompletos ignorado: {r.get('id', 'ID desconocido')}")
        
        print(f"✅ Registros válidos para procesar: {len(registros_validos)}")
        registros = registros_validos
        
        # === ESTADÍSTICAS DE HOY ===
        fecha_hoy = date.today().isoformat()
        registros_hoy = [r for r in registros if r['fecha'] == fecha_hoy]
        
        if registros_hoy:
            total_descansos_hoy = len([r for r in registros_hoy if r['tipo'] == 'DESCANSO'])
            total_comidas_hoy = len([r for r in registros_hoy if r['tipo'] == 'COMIDA'])
            total_minutos_hoy = sum(r['duracion_minutos'] for r in registros_hoy)
            minutos_descanso_hoy = sum(r['duracion_minutos'] for r in registros_hoy if r['tipo'] == 'DESCANSO')
            minutos_comida_hoy = sum(r['duracion_minutos'] for r in registros_hoy if r['tipo'] == 'COMIDA')
            
            stats_hoy = {
                'total_descansos': total_descansos_hoy + total_comidas_hoy,
                'total_minutos': total_minutos_hoy,
                'promedio_minutos': round(total_minutos_hoy / len(registros_hoy), 1) if registros_hoy else 0,
                'total_comidas': total_comidas_hoy,
                'total_descansos_cortos': total_descansos_hoy,
                'minutos_comida': minutos_comida_hoy,
                'minutos_descanso': minutos_descanso_hoy
            }
        else:
            stats_hoy = {
                'total_descansos': 0,
                'total_minutos': 0,
                'promedio_minutos': 0,
                'total_comidas': 0,
                'total_descansos_cortos': 0,
                'minutos_comida': 0,
                'minutos_descanso': 0
            }
        
        # === ESTADÍSTICAS DE LA SEMANA ===
        fecha_inicio_semana = (date.today() - timedelta(days=7)).isoformat()
        registros_semana = [r for r in registros if r['fecha'] >= fecha_inicio_semana]
        
        if registros_semana:
            total_minutos_semana = sum(r['duracion_minutos'] for r in registros_semana)
            
            stats_semana = {
                'total_descansos': len(registros_semana),
                'total_minutos': total_minutos_semana,
                'promedio_minutos': round(total_minutos_semana / len(registros_semana), 1) if registros_semana else 0
            }
        else:
            stats_semana = {
                'total_descansos': 0,
                'total_minutos': 0,
                'promedio_minutos': 0
            }
        
        # Calcular estadísticas generales (código existente)
        stats_por_usuario = {}
        stats_por_dia = {}
        total_descansos = 0
        total_comidas = 0
        tiempo_total_descansos = 0
        tiempo_total_comidas = 0
        
        # Procesar registros con manejo de errores
        usuarios_info = {}  # Para almacenar info de usuarios
        
        for r in registros:
            try:
                usuario_data = r.get('usuarios', {})
                usuario_nombre = usuario_data.get('nombre', 'Usuario Desconocido') if usuario_data else 'Usuario Desconocido'
                usuario_codigo = usuario_data.get('codigo', 'N/A') if usuario_data else 'N/A'
                fecha = r.get('fecha', date.today().isoformat())
                tipo = r.get('tipo', 'DESCANSO')
                duracion = r.get('duracion_minutos', 0)
                
                # Almacenar info del usuario
                if usuario_nombre != 'Usuario Desconocido':
                    usuarios_info[usuario_nombre] = usuario_codigo
                
                # Validar datos
                if not usuario_nombre or usuario_nombre == 'Usuario Desconocido':
                    print(f"⚠️ Usuario sin nombre en registro ID: {r.get('id', 'desconocido')}")
                    continue
                
                if duracion <= 0:
                    print(f"⚠️ Duración inválida ({duracion}) en registro ID: {r.get('id', 'desconocido')}")
                    continue
                
                # Stats por usuario
                if usuario_nombre not in stats_por_usuario:
                    stats_por_usuario[usuario_nombre] = {
                        'descansos': 0,
                        'comidas': 0,
                        'tiempo_descansos': 0,
                        'tiempo_comidas': 0,
                        'tiempo_total': 0,
                        'exceso_total': 0  # Para calcular usuarios que más se exceden
                    }
                
                # Stats por día
                if fecha not in stats_por_dia:
                    stats_por_dia[fecha] = {
                        'descansos': 0,
                        'comidas': 0,
                        'usuarios_unicos': set()
                    }
                
                # Calcular exceso
                exceso = 0
                if tipo == 'DESCANSO' and duracion > 20:
                    exceso = duracion - 20
                elif tipo == 'COMIDA' and duracion > 40:
                    exceso = duracion - 40
                
                # Actualizar contadores
                if tipo == 'DESCANSO':
                    stats_por_usuario[usuario_nombre]['descansos'] += 1
                    stats_por_usuario[usuario_nombre]['tiempo_descansos'] += duracion
                    stats_por_dia[fecha]['descansos'] += 1
                    total_descansos += 1
                    tiempo_total_descansos += duracion
                else:
                    stats_por_usuario[usuario_nombre]['comidas'] += 1
                    stats_por_usuario[usuario_nombre]['tiempo_comidas'] += duracion
                    stats_por_dia[fecha]['comidas'] += 1
                    total_comidas += 1
                    tiempo_total_comidas += duracion
                
                stats_por_usuario[usuario_nombre]['tiempo_total'] += duracion
                stats_por_usuario[usuario_nombre]['exceso_total'] += exceso
                stats_por_dia[fecha]['usuarios_unicos'].add(usuario_nombre)
                
            except Exception as e_registro:
                print(f"❌ Error procesando registro ID {r.get('id', 'desconocido')}: {e_registro}")
                continue
        
        # Convertir sets a conteos
        for fecha in stats_por_dia:
            stats_por_dia[fecha]['usuarios_unicos'] = len(stats_por_dia[fecha]['usuarios_unicos'])
        
        # Ordenar usuarios por tiempo total (top 10)
        top_usuarios = sorted(stats_por_usuario.items(), 
                            key=lambda x: x[1]['exceso_total'], 
                            reverse=True)[:10]
        
        # Formatear top usuarios para el template
        top_usuarios_formateado = []
        for i, (nombre, stats) in enumerate(top_usuarios):
            if stats['exceso_total'] > 0:  # Solo mostrar usuarios con exceso
                codigo_usuario = usuarios_info.get(nombre, nombre[:3].upper())
                top_usuarios_formateado.append({
                    'posicion': i + 1,
                    'nombre': nombre,
                    'codigo': codigo_usuario,
                    'total_descansos': stats['descansos'] + stats['comidas'],
                    'total_comidas': stats['comidas'],
                    'total_descansos_cortos': stats['descansos'],
                    'total_minutos': stats['tiempo_total'],  # ← Esta es la clave que falta
                    'tiempo_total': stats['tiempo_total'],
                    'exceso_total': stats['exceso_total'],
                    'exceso_comidas': max(0, stats['tiempo_comidas'] - (stats['comidas'] * 40)) if stats['comidas'] > 0 else 0,
                    'comidas_con_exceso': len([c for c in range(stats['comidas']) if (stats['tiempo_comidas'] / stats['comidas']) > 40]) if stats['comidas'] > 0 else 0,
                    'exceso_descansos': max(0, stats['tiempo_descansos'] - (stats['descansos'] * 20)) if stats['descansos'] > 0 else 0,
                    'descansos_con_exceso': len([d for d in range(stats['descansos']) if (stats['tiempo_descansos'] / stats['descansos']) > 20]) if stats['descansos'] > 0 else 0
                })
        
        # Preparar datos para gráficos
        fechas_ordenadas = sorted(stats_por_dia.keys())
        datos_grafico = {
            'fechas': [datetime.fromisoformat(f).strftime('%d/%m') for f in fechas_ordenadas],
            'descansos': [stats_por_dia[f]['descansos'] for f in fechas_ordenadas],
            'comidas': [stats_por_dia[f]['comidas'] for f in fechas_ordenadas]
        }
        
        # Estadísticas generales
        estadisticas = {
            'total_descansos': total_descansos,
            'total_comidas': total_comidas,
            'tiempo_total_descansos': tiempo_total_descansos,
            'tiempo_total_comidas': tiempo_total_comidas,
            'promedio_descanso': round(tiempo_total_descansos / total_descansos, 1) if total_descansos > 0 else 0,
            'promedio_comida': round(tiempo_total_comidas / total_comidas, 1) if total_comidas > 0 else 0
        }
        
    except Exception as e:
        print(f"❌ Error detallado al generar reportes: {e}")
        print(f"📊 Tipo de error: {type(e).__name__}")
        print(f"📍 Stack trace: {traceback.format_exc()}")
        
        # Valores por defecto en caso de error
        stats_hoy = {
            'total_descansos': 0,
            'total_minutos': 0,
            'promedio_minutos': 0,
            'total_comidas': 0,
            'total_descansos_cortos': 0,
            'minutos_comida': 0,
            'minutos_descanso': 0
        }
        stats_semana = {
            'total_descansos': 0,
            'total_minutos': 0,
            'promedio_minutos': 0
        }
        estadisticas = {
            'total_descansos': 0,
            'total_comidas': 0,
            'tiempo_total_descansos': 0,
            'tiempo_total_comidas': 0,
            'promedio_descanso': 0,
            'promedio_comida': 0
        }
        top_usuarios_formateado = []
        datos_grafico = {'fechas': [], 'descansos': [], 'comidas': []}
    
    return render_template('reportes.html',
                         estadisticas=estadisticas,
                         top_usuarios=top_usuarios_formateado,
                         stats_hoy=stats_hoy,
                         stats_semana=stats_semana,
                         fecha_hoy=date.today().strftime('%d/%m/%Y'),
                         datos_grafico=datos_grafico,
                         fecha_inicio=fecha_inicio,
                         fecha_fin=fecha_fin)

# Versión simplificada de reportes para debugging
@app.route('/reportes_simple')
@login_required
def reportes_simple():
    """Versión simplificada de reportes para identificar problemas"""
    fecha_inicio = request.args.get('fecha_inicio', (date.today() - timedelta(days=30)).isoformat())
    fecha_fin = request.args.get('fecha_fin', date.today().isoformat())
    
    try:
        print(f"🔍 Reportes simple - Período: {fecha_inicio} a {fecha_fin}")
        
        # Consulta básica sin JOIN complicado
        response = supabase.table('tiempos_descanso').select("*")\
            .gte('fecha', fecha_inicio)\
            .lte('fecha', fecha_fin)\
            .execute()
        
        registros_raw = response.data or []
        print(f"📊 Registros obtenidos: {len(registros_raw)}")
        
        # Estadísticas básicas
        total_registros = len(registros_raw)
        total_descansos = len([r for r in registros_raw if r.get('tipo') == 'DESCANSO'])
        total_comidas = len([r for r in registros_raw if r.get('tipo') == 'COMIDA'])
        tiempo_total = sum(r.get('duracion_minutos', 0) for r in registros_raw)
        
        estadisticas = {
            'total_descansos': total_descansos,
            'total_comidas': total_comidas,
            'tiempo_total_descansos': sum(r.get('duracion_minutos', 0) for r in registros_raw if r.get('tipo') == 'DESCANSO'),
            'tiempo_total_comidas': sum(r.get('duracion_minutos', 0) for r in registros_raw if r.get('tipo') == 'COMIDA'),
            'promedio_descanso': 0,
            'promedio_comida': 0
        }
        
        # Calcular promedios
        if total_descansos > 0:
            estadisticas['promedio_descanso'] = round(estadisticas['tiempo_total_descansos'] / total_descansos, 1)
        if total_comidas > 0:
            estadisticas['promedio_comida'] = round(estadisticas['tiempo_total_comidas'] / total_comidas, 1)
        
        # Stats de hoy
        fecha_hoy = date.today().isoformat()
        registros_hoy = [r for r in registros_raw if r.get('fecha') == fecha_hoy]
        
        stats_hoy = {
            'total_descansos': len(registros_hoy),
            'total_minutos': sum(r.get('duracion_minutos', 0) for r in registros_hoy),
            'promedio_minutos': round(sum(r.get('duracion_minutos', 0) for r in registros_hoy) / len(registros_hoy), 1) if registros_hoy else 0,
            'total_comidas': len([r for r in registros_hoy if r.get('tipo') == 'COMIDA']),
            'total_descansos_cortos': len([r for r in registros_hoy if r.get('tipo') == 'DESCANSO']),
            'minutos_comida': sum(r.get('duracion_minutos', 0) for r in registros_hoy if r.get('tipo') == 'COMIDA'),
            'minutos_descanso': sum(r.get('duracion_minutos', 0) for r in registros_hoy if r.get('tipo') == 'DESCANSO')
        }
        
        # Stats de la semana
        fecha_inicio_semana = (date.today() - timedelta(days=7)).isoformat()
        registros_semana = [r for r in registros_raw if r.get('fecha', '') >= fecha_inicio_semana]
        
        stats_semana = {
            'total_descansos': len(registros_semana),
            'total_minutos': sum(r.get('duracion_minutos', 0) for r in registros_semana),
            'promedio_minutos': round(sum(r.get('duracion_minutos', 0) for r in registros_semana) / len(registros_semana), 1) if registros_semana else 0
        }
        
        # Datos de gráfico básicos
        datos_grafico = {
            'fechas': ['Últimos 7 días'],
            'descansos': [len([r for r in registros_semana if r.get('tipo') == 'DESCANSO'])],
            'comidas': [len([r for r in registros_semana if r.get('tipo') == 'COMIDA'])]
        }
        
        return render_template('reportes.html',
                             estadisticas=estadisticas,
                             top_usuarios=[],  # Vacío por ahora
                             stats_hoy=stats_hoy,
                             stats_semana=stats_semana,
                             fecha_hoy=date.today().strftime('%d/%m/%Y'),
                             datos_grafico=datos_grafico,
                             fecha_inicio=fecha_inicio,
                             fecha_fin=fecha_fin)
        
    except Exception as e:
        print(f"❌ Error en reportes simple: {e}")
        print(f"📍 Stack trace: {traceback.format_exc()}")
        return render_template('error.html', error=f'Error en reportes: {str(e)}')

# Exportar a CSV - Versión mejorada
@app.route('/exportar_csv')
@login_required
def exportar_csv():
    fecha_inicio = request.args.get('fecha_inicio', (date.today() - timedelta(days=30)).isoformat())
    fecha_fin = request.args.get('fecha_fin', date.today().isoformat())
    tipo_reporte = request.args.get('tipo', 'completo')  # completo, resumen, estadisticas
    formato = request.args.get('formato', 'csv')  # csv, excel
    
    try:
        print(f"📊 Exportando {tipo_reporte} en formato {formato} para período: {fecha_inicio} a {fecha_fin}")
        
        if tipo_reporte == 'estadisticas':
            return exportar_estadisticas_csv(fecha_inicio, fecha_fin, formato)
        elif tipo_reporte == 'resumen':
            return exportar_resumen_csv(fecha_inicio, fecha_fin, formato)
        else:
            return exportar_completo_csv(fecha_inicio, fecha_fin, formato)
            
    except Exception as e:
        print(f"❌ Error al exportar CSV: {e}")
        print(f"📍 Stack trace: {traceback.format_exc()}")
        return redirect(url_for('registros'))

def exportar_completo_csv(fecha_inicio, fecha_fin, formato='csv'):
    """Exportar todos los registros detallados"""
    try:
        # Obtener registros con manejo robusto de errores
        response = supabase.table('tiempos_descanso').select("*, usuarios(nombre, codigo, turno)")\
            .gte('fecha', fecha_inicio)\
            .lte('fecha', fecha_fin)\
            .order('fecha', desc=True)\
            .order('inicio', desc=True)\
            .execute()
        
        registros = response.data or []
        print(f"📊 Registros obtenidos para exportación: {len(registros)}")
        
        # Crear CSV en memoria
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';', quotechar='"')
        
        # Encabezados mejorados
        writer.writerow([
            'Fecha',
            'Día de la Semana', 
            'Nombre Completo',
            'Código',
            'Turno',
            'Tipo de Descanso',
            'Hora Entrada',
            'Hora Salida',
            'Duración (minutos)',
            'Duración (horas)',
            'Exceso (minutos)',
            'Estado',
            'Observaciones'
        ])
        
        # Datos con información enriquecida
        for r in registros:
            try:
                fecha_obj = datetime.fromisoformat(r['fecha'])
                usuario_data = r.get('usuarios', {})
                duracion = r.get('duracion_minutos', 0)
                tipo = r.get('tipo', 'DESCANSO')
                
                # Calcular exceso
                limite = 40 if tipo == 'COMIDA' else 20
                exceso = max(0, duracion - limite)
                
                # Determinar estado
                if exceso > 30:
                    estado = 'EXCESO ALTO'
                elif exceso > 0:
                    estado = 'CON EXCESO'
                else:
                    estado = 'NORMAL'
                
                # Observaciones
                observaciones = []
                if exceso > 0:
                    observaciones.append(f'Excedió {exceso} min del límite')
                if duracion < 5:
                    observaciones.append('Duración muy corta')
                
                writer.writerow([
                    fecha_obj.strftime('%d/%m/%Y'),
                    fecha_obj.strftime('%A').capitalize(),
                    usuario_data.get('nombre', 'Usuario Desconocido'),
                    usuario_data.get('codigo', 'N/A'),
                    usuario_data.get('turno', 'N/A'),
                    tipo,
                    r.get('inicio', 'N/A'),
                    r.get('fin', 'N/A'),
                    duracion,
                    round(duracion / 60, 2),
                    exceso,
                    estado,
                    '; '.join(observaciones) if observaciones else 'Sin observaciones'
                ])
                
            except Exception as e_row:
                print(f"⚠️ Error procesando registro ID {r.get('id', 'desconocido')}: {e_row}")
                continue
        
        # Preparar respuesta
        output.seek(0)
        filename = f'descansos_completo_{fecha_inicio}_{fecha_fin}.csv'
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),  # UTF-8 con BOM para Excel
            mimetype='text/csv; charset=utf-8',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"❌ Error en exportación completa: {e}")
        raise e

def exportar_resumen_csv(fecha_inicio, fecha_fin, formato='csv'):
    """Exportar resumen por usuario"""
    try:
        # Obtener datos
        response = supabase.table('tiempos_descanso').select("*, usuarios(nombre, codigo, turno)")\
            .gte('fecha', fecha_inicio)\
            .lte('fecha', fecha_fin)\
            .execute()
        
        registros = response.data or []
        
        # Procesar estadísticas por usuario
        stats_usuarios = {}
        
        for r in registros:
            try:
                usuario_data = r.get('usuarios', {})
                usuario_nombre = usuario_data.get('nombre', 'Usuario Desconocido')
                
                if usuario_nombre not in stats_usuarios:
                    stats_usuarios[usuario_nombre] = {
                        'codigo': usuario_data.get('codigo', 'N/A'),
                        'turno': usuario_data.get('turno', 'N/A'),
                        'total_descansos': 0,
                        'total_comidas': 0,
                        'tiempo_descansos': 0,
                        'tiempo_comidas': 0,
                        'exceso_descansos': 0,
                        'exceso_comidas': 0,
                        'dias_activos': set()
                    }
                
                tipo = r.get('tipo', 'DESCANSO')
                duracion = r.get('duracion_minutos', 0)
                fecha = r.get('fecha', '')
                
                # Actualizar estadísticas
                if tipo == 'DESCANSO':
                    stats_usuarios[usuario_nombre]['total_descansos'] += 1
                    stats_usuarios[usuario_nombre]['tiempo_descansos'] += duracion
                    if duracion > 20:
                        stats_usuarios[usuario_nombre]['exceso_descansos'] += (duracion - 20)
                else:
                    stats_usuarios[usuario_nombre]['total_comidas'] += 1
                    stats_usuarios[usuario_nombre]['tiempo_comidas'] += duracion
                    if duracion > 40:
                        stats_usuarios[usuario_nombre]['exceso_comidas'] += (duracion - 40)
                
                stats_usuarios[usuario_nombre]['dias_activos'].add(fecha)
                
            except Exception as e_user:
                print(f"⚠️ Error procesando usuario en registro: {e_user}")
                continue
        
        # Crear CSV
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';', quotechar='"')
        
        # Encabezados
        writer.writerow([
            'Nombre',
            'Código',
            'Turno',
            'Días Activos',
            'Total Descansos',
            'Total Comidas',
            'Tiempo Total Descansos (min)',
            'Tiempo Total Comidas (min)',
            'Tiempo Total (horas)',
            'Promedio Descanso (min)',
            'Promedio Comida (min)',
            'Exceso Descansos (min)',
            'Exceso Comidas (min)',
            'Exceso Total (min)',
            'Eficiencia (%)',
            'Estado General'
        ])
        
        # Datos resumidos
        for nombre, stats in stats_usuarios.items():
            try:
                # Convertir set a conteo
                dias_activos = len(stats['dias_activos'])
                
                # Calcular promedios
                promedio_descanso = round(stats['tiempo_descansos'] / stats['total_descansos'], 1) if stats['total_descansos'] > 0 else 0
                promedio_comida = round(stats['tiempo_comidas'] / stats['total_comidas'], 1) if stats['total_comidas'] > 0 else 0
                
                # Tiempo total
                tiempo_total_min = stats['tiempo_descansos'] + stats['tiempo_comidas']
                tiempo_total_horas = round(tiempo_total_min / 60, 2)
                
                # Exceso total
                exceso_total = stats['exceso_descansos'] + stats['exceso_comidas']
                
                # Eficiencia (menos exceso = más eficiente)
                tiempo_esperado = (stats['total_descansos'] * 20) + (stats['total_comidas'] * 40)
                eficiencia = round((tiempo_esperado / tiempo_total_min * 100), 1) if tiempo_total_min > 0 else 100
                
                # Estado general
                if exceso_total > 120:  # Más de 2 horas de exceso
                    estado = 'CRÍTICO'
                elif exceso_total > 60:  # Más de 1 hora de exceso
                    estado = 'ALTO EXCESO'
                elif exceso_total > 30:  # Más de 30 min de exceso
                    estado = 'MODERADO EXCESO'
                elif exceso_total > 0:
                    estado = 'LEVE EXCESO'
                else:
                    estado = 'ÓPTIMO'
                
                writer.writerow([
                    nombre,
                    stats['codigo'],
                    stats['turno'],
                    dias_activos,
                    stats['total_descansos'],
                    stats['total_comidas'],
                    stats['tiempo_descansos'],
                    stats['tiempo_comidas'],
                    tiempo_total_horas,
                    promedio_descanso,
                    promedio_comida,
                    stats['exceso_descansos'],
                    stats['exceso_comidas'],
                    exceso_total,
                    eficiencia,
                    estado
                ])
                
            except Exception as e_summary:
                print(f"⚠️ Error creando resumen para {nombre}: {e_summary}")
                continue
        
        # Preparar respuesta
        output.seek(0)
        filename = f'resumen_usuarios_{fecha_inicio}_{fecha_fin}.csv'
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            mimetype='text/csv; charset=utf-8',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"❌ Error en exportación resumen: {e}")
        raise e

def exportar_estadisticas_csv(fecha_inicio, fecha_fin, formato='csv'):
    """Exportar estadísticas generales del período"""
    try:
        # Obtener datos
        response = supabase.table('tiempos_descanso').select("*, usuarios(nombre, codigo, turno)")\
            .gte('fecha', fecha_inicio)\
            .lte('fecha', fecha_fin)\
            .execute()
        
        registros = response.data or []
        
        # Crear CSV
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';', quotechar='"')
        
        # Estadísticas generales
        total_registros = len(registros)
        total_descansos = len([r for r in registros if r.get('tipo') == 'DESCANSO'])
        total_comidas = len([r for r in registros if r.get('tipo') == 'COMIDA'])
        
        tiempo_total_descansos = sum(r.get('duracion_minutos', 0) for r in registros if r.get('tipo') == 'DESCANSO')
        tiempo_total_comidas = sum(r.get('duracion_minutos', 0) for r in registros if r.get('tipo') == 'COMIDA')
        
        # Escribir estadísticas generales
        writer.writerow(['ESTADÍSTICAS GENERALES'])
        writer.writerow(['Período', f'{fecha_inicio} a {fecha_fin}'])
        writer.writerow(['Fecha de exportación', datetime.now().strftime('%d/%m/%Y %H:%M:%S')])
        writer.writerow([])
        
        writer.writerow(['RESUMEN GENERAL'])
        writer.writerow(['Total de registros', total_registros])
        writer.writerow(['Total descansos', total_descansos])
        writer.writerow(['Total comidas', total_comidas])
        writer.writerow(['Tiempo total descansos (min)', tiempo_total_descansos])
        writer.writerow(['Tiempo total comidas (min)', tiempo_total_comidas])
        writer.writerow(['Tiempo total (horas)', round((tiempo_total_descansos + tiempo_total_comidas) / 60, 2)])
        writer.writerow([])
        
        # Promedios
        writer.writerow(['PROMEDIOS'])
        writer.writerow(['Promedio descanso (min)', round(tiempo_total_descansos / total_descansos, 1) if total_descansos > 0 else 0])
        writer.writerow(['Promedio comida (min)', round(tiempo_total_comidas / total_comidas, 1) if total_comidas > 0 else 0])
        writer.writerow([])
        
        # Estadísticas por día
        writer.writerow(['ESTADÍSTICAS POR DÍA'])
        writer.writerow(['Fecha', 'Día', 'Descansos', 'Comidas', 'Total', 'Usuarios Únicos'])
        
        # Agrupar por fecha
        stats_por_dia = {}
        for r in registros:
            try:
                fecha = r.get('fecha', '')
                if fecha not in stats_por_dia:
                    stats_por_dia[fecha] = {
                        'descansos': 0,
                        'comidas': 0,
                        'usuarios': set()
                    }
                
                tipo = r.get('tipo', 'DESCANSO')
                usuario_data = r.get('usuarios', {})
                usuario_nombre = usuario_data.get('nombre', 'Desconocido')
                
                if tipo == 'DESCANSO':
                    stats_por_dia[fecha]['descansos'] += 1
                else:
                    stats_por_dia[fecha]['comidas'] += 1
                
                stats_por_dia[fecha]['usuarios'].add(usuario_nombre)
                
            except Exception as e_day:
                print(f"⚠️ Error procesando día: {e_day}")
                continue
        
        for fecha in sorted(stats_por_dia.keys()):
            try:
                fecha_obj = datetime.fromisoformat(fecha)
                stats = stats_por_dia[fecha]
                
                writer.writerow([
                    fecha_obj.strftime('%d/%m/%Y'),
                    fecha_obj.strftime('%A').capitalize(),
                    stats['descansos'],
                    stats['comidas'],
                    stats['descansos'] + stats['comidas'],
                    len(stats['usuarios'])
                ])
                
            except Exception as e_day_write:
                print(f"⚠️ Error escribiendo día {fecha}: {e_day_write}")
                continue
        
        # Preparar respuesta
        output.seek(0)
        filename = f'estadisticas_{fecha_inicio}_{fecha_fin}.csv'
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            mimetype='text/csv; charset=utf-8',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"❌ Error en exportación estadísticas: {e}")
        raise e

# Middleware para verificar sesión activa
@app.before_request
def check_session():
    if 'admin_id' in session:
        # Verificar tiempo de inactividad
        if 'last_activity' in session:
            last_activity = datetime.fromisoformat(session['last_activity'])
            if datetime.now() - last_activity > timedelta(minutes=30):
                session.clear()
                return redirect(url_for('login'))
        
        # Actualizar última actividad
        session['last_activity'] = datetime.now().isoformat()

# Manejo de errores
@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error='Página no encontrada'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error='Error interno del servidor'), 500

# Ruta simple para ver usuarios en descanso
@app.route('/ver_descansos')
def ver_descansos():
    """Ver usuarios en descanso en formato simple"""
    try:
        # Obtener descansos activos
        descansos_response = supabase.table('descansos').select("*").execute()
        
        html = "<h1>🔍 Diagnóstico de Usuarios en Descanso</h1>"
        html += f"<p><strong>Fecha/Hora:</strong> {datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}</p>"
        html += f"<p><strong>Descansos activos en BD:</strong> {len(descansos_response.data)}</p>"
        
        if descansos_response.data:
            html += "<h2>📋 Descansos Activos:</h2><ul>"
            
            for d in descansos_response.data:
                html += f"<li><strong>ID:</strong> {d['id']}<br>"
                html += f"<strong>Usuario ID:</strong> {d['usuario_id']}<br>"
                html += f"<strong>Inicio:</strong> {d['inicio']}<br>"
                
                # Buscar información del usuario
                user_response = supabase.table('usuarios').select("nombre, codigo").eq('id', d['usuario_id']).execute()
                
                if user_response.data:
                    usuario = user_response.data[0]
                    html += f"<strong>Usuario:</strong> {usuario['nombre']} ({usuario['codigo']})<br>"
                    
                    # Calcular tiempo
                    try:
                        inicio = datetime.fromisoformat(d['inicio'].replace('Z', '+00:00'))
                        ahora = get_current_time()
                        tiempo_transcurrido = int((ahora - inicio).total_seconds() / 60)
                        
                        html += f"<strong>Tiempo transcurrido:</strong> {tiempo_transcurrido} minutos<br>"
                        html += f"<strong>Tipo probable:</strong> {'COMIDA' if tiempo_transcurrido >= 20 else 'DESCANSO'}<br>"
                        
                    except Exception as e:
                        html += f"<strong>Error calculando tiempo:</strong> {e}<br>"
                else:
                    html += f"<strong>⚠️ Usuario no encontrado para ID {d['usuario_id']}</strong><br>"
                
                html += "</li><br>"
            
            html += "</ul>"
        else:
            html += "<p>❌ No hay descansos activos</p>"
        
        # Añadir enlaces útiles
        html += "<hr><h2>🔧 Enlaces de Diagnóstico:</h2>"
        html += "<ul>"
        html += "<li><a href='/debug_descansos'>Diagnóstico JSON completo</a></li>"
        html += "<li><a href='/status'>Estado de conexión</a></li>"
        html += "<li><a href='/'>Volver a la aplicación principal</a></li>"
        html += "</ul>"
        
        return html
        
    except Exception as e:
        return f"<h1>❌ Error</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>"

# Ruta para diagnosticar usuarios en descanso
@app.route('/debug_descansos')
def debug_descansos():
    """Diagnosticar por qué no se muestran los usuarios en descanso"""
    try:
        resultado = []
        resultado.append("=== DIAGNÓSTICO DE USUARIOS EN DESCANSO ===")
        
        # 1. Verificar tabla descansos
        resultado.append("\n1️⃣ CONSULTANDO TABLA DESCANSOS")
        descansos_response = supabase.table('descansos').select("*").execute()
        resultado.append(f"✓ Descansos activos encontrados: {len(descansos_response.data)}")
        
        if descansos_response.data:
            resultado.append("📋 Lista detallada de descansos:")
            for i, d in enumerate(descansos_response.data):
                resultado.append(f"   {i+1}. ID: {d['id']}")
                resultado.append(f"      Usuario ID: {d['usuario_id']}")
                resultado.append(f"      Inicio: {d['inicio']}")
                resultado.append(f"      Tipo: {d.get('tipo', 'No definido')}")
        else:
            resultado.append("⚠️ No hay descansos activos en la tabla")
        
        # 2. Verificar tabla usuarios
        resultado.append("\n2️⃣ CONSULTANDO TABLA USUARIOS")
        usuarios_response = supabase.table('usuarios').select("*").execute()
        resultado.append(f"✓ Total usuarios en BD: {len(usuarios_response.data)}")
        
        if usuarios_response.data:
            resultado.append("👥 Primeros 5 usuarios:")
            for i, u in enumerate(usuarios_response.data[:5]):
                resultado.append(f"   {i+1}. ID: {u['id']} - {u['nombre']} (Código: {u['codigo']})")
        
        # 3. Cruzar datos
        if descansos_response.data and usuarios_response.data:
            resultado.append("\n3️⃣ CRUZANDO DATOS")
            
            usuarios_dict = {u['id']: u for u in usuarios_response.data}
            usuarios_en_descanso_debug = []
            
            for d in descansos_response.data:
                usuario_id = d['usuario_id']
                resultado.append(f"\n🔍 Procesando descanso ID {d['id']}:")
                resultado.append(f"   Usuario ID buscado: {usuario_id}")
                
                if usuario_id in usuarios_dict:
                    usuario = usuarios_dict[usuario_id]
                    resultado.append(f"   ✅ Usuario encontrado: {usuario['nombre']} ({usuario['codigo']})")
                    
                    # Calcular tiempo
                    try:
                        inicio = datetime.fromisoformat(d['inicio'].replace('Z', '+00:00'))
                        ahora = get_current_time()
                        tiempo_transcurrido = int((ahora - inicio).total_seconds() / 60)
                        tiempo_maximo = 40 if tiempo_transcurrido >= 20 else 20
                        tiempo_restante = max(0, tiempo_maximo - tiempo_transcurrido)
                        tipo_probable = 'COMIDA' if tiempo_transcurrido >= 20 else 'DESCANSO'
                        
                        resultado.append(f"   ⏰ Tiempo transcurrido: {tiempo_transcurrido} min")
                        resultado.append(f"   📋 Tipo: {tipo_probable}")
                        resultado.append(f"   ⏳ Tiempo restante: {tiempo_restante} min")
                        
                        usuarios_en_descanso_debug.append({
                            'nombre': usuario['nombre'],
                            'codigo': usuario['codigo'],
                            'tiempo_transcurrido': tiempo_transcurrido,
                            'tiempo_restante': tiempo_restante,
                            'tipo_probable': tipo_probable
                        })
                        resultado.append(f"   ✅ Usuario agregado a lista de descansos")
                        
                    except Exception as e_tiempo:
                        resultado.append(f"   ❌ Error calculando tiempo: {e_tiempo}")
                        
                else:
                    resultado.append(f"   ❌ PROBLEMA: Usuario ID {usuario_id} no existe en tabla usuarios")
                    resultado.append(f"      Esto indica datos inconsistentes")
            
            resultado.append(f"\n📊 RESUMEN:")
            resultado.append(f"   Descansos en BD: {len(descansos_response.data)}")
            resultado.append(f"   Usuarios procesados exitosamente: {len(usuarios_en_descanso_debug)}")
            resultado.append(f"   Diferencia: {len(descansos_response.data) - len(usuarios_en_descanso_debug)}")
            
            if usuarios_en_descanso_debug:
                resultado.append(f"\n👥 USUARIOS QUE DEBERÍAN APARECER:")
                for u in usuarios_en_descanso_debug:
                    resultado.append(f"   - {u['nombre']} ({u['codigo']}) - {u['tiempo_transcurrido']} min")
            
            return jsonify({
                'diagnostico': resultado,
                'datos': {
                    'descansos_activos': len(descansos_response.data),
                    'usuarios_totales': len(usuarios_response.data),
                    'usuarios_en_descanso': len(usuarios_en_descanso_debug),
                    'descansos_raw': descansos_response.data,
                    'usuarios_procesados': usuarios_en_descanso_debug
                }
            })
        else:
            resultado.append("\n❌ No se pueden cruzar datos - faltan descansos o usuarios")
            return jsonify({
                'diagnostico': resultado, 
                'error': 'Datos insuficientes',
                'datos': {
                    'descansos_activos': len(descansos_response.data) if descansos_response.data else 0,
                    'usuarios_totales': len(usuarios_response.data) if usuarios_response.data else 0,
                    'usuarios_en_descanso': 0,
                    'descansos_raw': descansos_response.data if descansos_response.data else [],
                    'usuarios_procesados': []
                }
            })
            
    except Exception as e:
        resultado.append(f"\n❌ ERROR: {str(e)}")
        import traceback
        resultado.append(f"Stack trace: {traceback.format_exc()}")
        return jsonify({
            'diagnostico': resultado, 
            'error': str(e),
            'datos': {
                'descansos_activos': 0,
                'usuarios_totales': 0,
                'usuarios_en_descanso': 0,
                'descansos_raw': [],
                'usuarios_procesados': []
            }
        })

# Ruta para simular flujo completo
@app.route('/test_flujo_completo/<codigo>')
def test_flujo_completo(codigo):
    """Simular flujo completo: entrada + salida"""
    try:
        resultado = []
        resultado.append(f"=== TEST FLUJO COMPLETO: {codigo} ===")
        
        # 1. Buscar usuario
        user_response = supabase.table('usuarios').select('*').eq('codigo', codigo.upper()).execute()
        if not user_response.data:
            return jsonify({'error': f'Usuario con código {codigo} no encontrado'}), 404
        
        usuario = user_response.data[0]
        resultado.append(f"✓ Usuario: {usuario['nombre']} (ID: {usuario['id']})")
        
        # 2. Limpiar descansos previos
        clean_response = supabase_admin.table('descansos').delete().eq('usuario_id', usuario['id']).execute()
        resultado.append(f"✓ Limpieza: {len(clean_response.data) if clean_response.data else 0} descansos eliminados")
        
        # 3. SIMULAR ENTRADA
        resultado.append(f"--- SIMULANDO ENTRADA ---")
        entrada_response = supabase_admin.table('descansos').insert({
            'usuario_id': usuario['id'],
            'inicio': get_current_time().isoformat(),
            'tipo': 'Pendiente'
        }).execute()
        
        if not entrada_response.data:
            return jsonify({'error': 'No se pudo registrar entrada', 'log': resultado}), 500
        
        descanso_id = entrada_response.data[0]['id']
        resultado.append(f"✓ Entrada registrada (ID: {descanso_id})")
        
        # 4. Simular tiempo
        import time
        time.sleep(3)
        resultado.append(f"✓ Tiempo simulado (3 segundos)")
        
        # 5. SIMULAR SALIDA
        resultado.append(f"--- SIMULANDO SALIDA ---")
        
        # Buscar el descanso recién creado
        descanso_response = supabase.table('descansos').select('*').eq('id', descanso_id).execute()
        if not descanso_response.data:
            return jsonify({'error': 'Descanso creado no encontrado', 'log': resultado}), 500
        
        descanso_activo = descanso_response.data[0]
        
        # Cerrar usando función helper
        success, mensaje, detalle = cerrar_descanso_usuario(usuario['id'], descanso_activo)
        
        resultado.append(f"{'✓' if success else '✗'} Cierre: {mensaje}")
        
        # 6. Verificación final completa
        resultado.append(f"--- VERIFICACIÓN FINAL ---")
        final_descansos = supabase.table('descansos').select('*').eq('usuario_id', usuario['id']).execute()
        final_tiempos = supabase.table('tiempos_descanso').select('*').eq('usuario_id', usuario['id']).order('id', desc=True).limit(1).execute()
        
        resultado.append(f"✓ Descansos activos: {len(final_descansos.data)}")
        resultado.append(f"✓ Registros en historial: {len(final_tiempos.data)}")
        
        if final_tiempos.data:
            ultimo = final_tiempos.data[0]
            resultado.append(f"✓ Último registro: {ultimo['tipo']} - {ultimo['duracion_minutos']} min")
        
        return jsonify({
            'success': success,
            'usuario': usuario['nombre'],
            'codigo': codigo,
            'operacion_completa': success and len(final_descansos.data) == 0 and len(final_tiempos.data) > 0,
            'detalle': detalle,
            'log': resultado
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'codigo': codigo,
            'log': resultado if 'resultado' in locals() else []
        }), 500

# Ruta específica para probar cierre de descanso por código de usuario
@app.route('/test_close_by_code/<codigo>')
def test_close_by_code(codigo):
    """Probar cerrar descanso usando código de usuario"""
    try:
        resultado = []
        resultado.append(f"=== TEST CIERRE POR CÓDIGO: {codigo} ===")
        
        # 1. Buscar usuario
        user_response = supabase.table('usuarios').select('*').eq('codigo', codigo.upper()).execute()
        if not user_response.data:
            return jsonify({'error': f'Usuario con código {codigo} no encontrado'}), 404
        
        usuario = user_response.data[0]
        resultado.append(f"✓ Usuario encontrado: {usuario['nombre']} (ID: {usuario['id']})")
        
        # 2. Buscar descanso activo
        descanso_response = supabase.table('descansos').select('*').eq('usuario_id', usuario['id']).execute()
        
        if not descanso_response.data:
            resultado.append(f"⚠️ Usuario no tiene descanso activo")
            return jsonify({
                'info': 'Usuario sin descanso activo',
                'usuario': usuario['nombre'],
                'log': resultado
            })
        
        descanso_activo = descanso_response.data[0]
        resultado.append(f"✓ Descanso activo encontrado: ID {descanso_activo['id']}")
        resultado.append(f"   Inicio: {descanso_activo['inicio']}")
        
        # 3. Cerrar descanso usando función helper
        success, mensaje, detalle = cerrar_descanso_usuario(usuario['id'], descanso_activo)
        
        resultado.append(f"{'✓' if success else '✗'} Resultado: {mensaje}")
        if detalle:
            resultado.append(f"   Detalles: {detalle}")
        
        return jsonify({
            'success': success,
            'usuario': usuario['nombre'],
            'codigo': codigo,
            'mensaje': mensaje,
            'detalle': detalle,
            'log': resultado
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'codigo': codigo,
            'log': resultado if 'resultado' in locals() else []
        }), 500

# Ruta para probar operaciones básicas
@app.route('/test_operation/<int:usuario_id>')
def test_operation(usuario_id):
    """Probar registrar y cerrar un descanso para un usuario específico"""
    try:
        resultado = []
        
        # 1. Verificar usuario
        user_response = supabase.table('usuarios').select('*').eq('id', usuario_id).execute()
        if not user_response.data:
            return jsonify({'error': f'Usuario {usuario_id} no encontrado'}), 404
        
        usuario = user_response.data[0]
        resultado.append(f"✓ Usuario encontrado: {usuario['nombre']}")
        
        # 2. Limpiar descansos previos
        clean_response = supabase_admin.table('descansos').delete().eq('usuario_id', usuario_id).execute()
        resultado.append(f"✓ Limpieza: {len(clean_response.data) if clean_response.data else 0} descansos eliminados")
        
        # 3. Crear descanso
        crear_response = supabase_admin.table('descansos').insert({
            'usuario_id': usuario_id,
            'inicio': get_current_time().isoformat(),
            'tipo': 'Pendiente'
        }).execute()
        
        if not crear_response.data:
            resultado.append("✗ Error creando descanso")
            return jsonify({'error': 'No se pudo crear descanso', 'log': resultado}), 500
        
        descanso_id = crear_response.data[0]['id']
        resultado.append(f"✓ Descanso creado (ID: {descanso_id})")
        
        # 4. Simular tiempo
        import time
        time.sleep(2)
        
        # 5. Cerrar descanso
        descanso = crear_response.data[0]
        inicio = datetime.fromisoformat(descanso['inicio'].replace('Z', '+00:00'))
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
        
        if not tiempo_response.data:
            resultado.append("✗ Error registrando tiempo")
            return jsonify({'error': 'No se pudo registrar tiempo', 'log': resultado}), 500
        
        # Eliminar descanso activo
        delete_response = supabase_admin.table('descansos').delete().eq('id', descanso_id).execute()
        
        resultado.append(f"✓ Tiempo registrado: {tipo} - {duracion_minutos} min")
        resultado.append(f"✓ Descanso eliminado: {len(delete_response.data) if delete_response.data else 0}")
        
        return jsonify({
            'success': True,
            'usuario': usuario['nombre'],
            'operacion': f'{tipo} de {duracion_minutos} minutos',
            'log': resultado
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'log': resultado if 'resultado' in locals() else []
        }), 500

# Ruta de estado de conexión
@app.route('/status')
def status():
    """Mostrar el estado actual de la conexión y sistema"""
    try:
        # Probar conexión actual
        test_users = supabase.table('usuarios').select('*').limit(3).execute()
        test_descansos = supabase.table('descansos').select('*').execute()
        test_tiempos = supabase.table('tiempos_descanso').select('*').limit(3).execute()
        
        status_info = {
            'timestamp': get_current_time().strftime('%Y-%m-%d %H:%M:%S'),
            'conexion': conexion_supabase_status,
            'tablas': {
                'usuarios': len(test_users.data) if test_users.data else 0,
                'descansos_activos': len(test_descansos.data) if test_descansos.data else 0,
                'tiempos_registrados': len(test_tiempos.data) if test_tiempos.data else 0
            },
            'usuarios_muestra': test_users.data if test_users.data else [],
            'descansos_activos_muestra': test_descansos.data if test_descansos.data else []
        }
        
        return jsonify(status_info)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'conexion': conexion_supabase_status,
            'timestamp': get_current_time().strftime('%Y-%m-%d %H:%M:%S')
        }), 500

# Ruta de debug (solo para desarrollo)
@app.route('/debug')
def debug():
    if not app.debug:
        return "Debug deshabilitado", 404
    
    debug_info = []
    
    try:
        # Probar conexión básica
        debug_info.append("=== PRUEBAS DE CONEXIÓN ===")
        
        # 1. Verificar usuarios
        users_response = supabase.table('usuarios').select("*").execute()
        debug_info.append(f"✅ Usuarios encontrados: {len(users_response.data)}")
        
        # 2. Verificar descansos activos
        breaks_response = supabase.table('descansos').select("*").execute()
        debug_info.append(f"✅ Descansos activos: {len(breaks_response.data)}")
        
        # 3. Verificar tiempos de descanso
        times_response = supabase.table('tiempos_descanso').select("*").execute()
        debug_info.append(f"✅ Registros históricos: {len(times_response.data)}")
        
        # 4. Verificar administradores
        admin_response = supabase.table('administradores').select("*").execute()
        debug_info.append(f"✅ Administradores: {len(admin_response.data)}")
        
        # 5. Mostrar estructura de un usuario si existe
        if users_response.data:
            debug_info.append("\n=== ESTRUCTURA USUARIO ===")
            user = users_response.data[0]
            for key, value in user.items():
                debug_info.append(f"{key}: {value}")
        
        # 6. Mostrar estructura de un descanso si existe
        if breaks_response.data:
            debug_info.append("\n=== ESTRUCTURA DESCANSO ===")
            break_item = breaks_response.data[0]
            for key, value in break_item.items():
                debug_info.append(f"{key}: {value}")
                
        debug_info.append("\n=== PRUEBA DE ESCRITURA ===")
        
        # 7. Probar escritura con admin client
        test_response = supabase_admin.table('usuarios').select("*").limit(1).execute()
        debug_info.append(f"✅ Cliente admin funciona: {len(test_response.data)} registros")
        
    except Exception as e:
        debug_info.append(f"❌ Error en debug: {str(e)}")
    
    return "<pre>" + "\n".join(debug_info) + "</pre>"

# Ruta para probar cerrar descanso específico
@app.route('/debug/close/<descanso_id>')
def debug_close_break(descanso_id):
    if not app.debug:
        return "Debug deshabilitado", 404
    
    debug_info = []
    
    try:
        debug_info.append(f"=== INTENTANDO CERRAR DESCANSO {descanso_id} ===")
        
        # 1. Buscar el descanso
        response = supabase.table('descansos').select("*").eq('id', descanso_id).execute()
        if not response.data:
            debug_info.append("❌ Descanso no encontrado")
            return "<pre>" + "\n".join(debug_info) + "</pre>"
        
        descanso = response.data[0]
        debug_info.append(f"✅ Descanso encontrado: {descanso}")
        
        # 2. Buscar el usuario
        user_response = supabase.table('usuarios').select("*").eq('id', descanso['usuario_id']).execute()
        if not user_response.data:
            debug_info.append("❌ Usuario no encontrado")
            return "<pre>" + "\n".join(debug_info) + "</pre>"
        
        usuario = user_response.data[0]
        debug_info.append(f"✅ Usuario encontrado: {usuario['nombre']}")
        
        # 3. Calcular duración
        inicio = datetime.fromisoformat(descanso['inicio'].replace('Z', '+00:00'))
        fin = get_current_time()
        duracion_minutos = int((fin - inicio).total_seconds() / 60)
        tipo = 'COMIDA' if duracion_minutos >= 30 else 'DESCANSO'
        
        debug_info.append(f"⏱️ Duración: {duracion_minutos} minutos, Tipo: {tipo}")
        
        # 4. Insertar en tiempos_descanso
        insert_data = {
            'usuario_id': usuario['id'],
            'tipo': tipo,
            'fecha': inicio.date().isoformat(),
            'inicio': inicio.time().isoformat(),
            'fin': fin.time().isoformat(),
            'duracion_minutos': duracion_minutos
        }
        debug_info.append(f"📝 Datos a insertar: {insert_data}")
        
        insert_response = supabase_admin.table('tiempos_descanso').insert(insert_data).execute()
        debug_info.append(f"✅ Inserción exitosa: {insert_response.data}")
        
        # 5. Eliminar de descansos
        delete_response = supabase_admin.table('descansos').delete().eq('id', descanso_id).execute()
        debug_info.append(f"🗑️ Eliminación exitosa: {delete_response.data}")
        
        debug_info.append("🎉 PROCESO COMPLETADO EXITOSAMENTE")
        
    except Exception as e:
        debug_info.append(f"❌ Error: {str(e)}")
        import traceback
        debug_info.append(f"Stack trace: {traceback.format_exc()}")
    
    return "<pre>" + "\n".join(debug_info) + "</pre>"

# Health check para Render
@app.route('/health')
def health_check():
    """Health check endpoint para Render"""
    try:
        # Verificar conexión a Supabase
        test_response = supabase.table('usuarios').select("id").limit(1).execute()
        return {"status": "healthy", "database": "connected"}, 200
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 500

# Ruta de debug específica para reportes
@app.route('/debug_reportes')
def debug_reportes():
    """Diagnóstico específico para la función de reportes"""
    try:
        debug_info = []
        debug_info.append("=== DEBUG REPORTES ===")
        
        # Probar conexión básica
        debug_info.append("1. Probando conexión a Supabase...")
        test_response = supabase.table('usuarios').select("id").limit(1).execute()
        debug_info.append(f"✅ Conexión OK - {len(test_response.data)} usuarios encontrados")
        
        # Probar consulta de tiempos_descanso
        debug_info.append("2. Probando tabla tiempos_descanso...")
        fecha_inicio = (date.today() - timedelta(days=7)).isoformat()
        fecha_fin = date.today().isoformat()
        
        # Consulta básica sin JOIN
        basic_response = supabase.table('tiempos_descanso').select("*").limit(5).execute()
        debug_info.append(f"✅ Consulta básica OK - {len(basic_response.data)} registros")
        
        if basic_response.data:
            debug_info.append("📋 Estructura de registro:")
            sample = basic_response.data[0]
            for key, value in sample.items():
                debug_info.append(f"   {key}: {type(value).__name__} = {value}")
        
        # Probar consulta con JOIN
        debug_info.append("3. Probando consulta con JOIN...")
        try:
            join_response = supabase.table('tiempos_descanso').select("*, usuarios(nombre, codigo)").limit(3).execute()
            debug_info.append(f"✅ JOIN OK - {len(join_response.data)} registros")
            
            if join_response.data:
                debug_info.append("📋 Estructura con JOIN:")
                sample_join = join_response.data[0]
                debug_info.append(f"   usuarios: {sample_join.get('usuarios', 'NO ENCONTRADO')}")
                
        except Exception as e_join:
            debug_info.append(f"❌ Error en JOIN: {e_join}")
        
        # Probar consulta con filtros de fecha
        debug_info.append("4. Probando consulta con filtros de fecha...")
        try:
            filtered_response = supabase.table('tiempos_descanso').select("*, usuarios(nombre, codigo)")\
                .gte('fecha', fecha_inicio)\
                .lte('fecha', fecha_fin)\
                .execute()
            debug_info.append(f"✅ Filtros OK - {len(filtered_response.data)} registros en período")
            
        except Exception as e_filter:
            debug_info.append(f"❌ Error en filtros: {e_filter}")
        
        debug_info.append("5. Verificando estructura de datos...")
        if filtered_response.data:
            for i, record in enumerate(filtered_response.data[:3]):
                debug_info.append(f"   Registro {i+1}:")
                debug_info.append(f"     ID: {record.get('id', 'NO ID')}")
                debug_info.append(f"     Fecha: {record.get('fecha', 'NO FECHA')}")
                debug_info.append(f"     Tipo: {record.get('tipo', 'NO TIPO')}")
                debug_info.append(f"     Duración: {record.get('duracion_minutos', 'NO DURACIÓN')}")
                debug_info.append(f"     Usuario: {record.get('usuarios', 'NO USUARIO')}")
        
        return jsonify({
            'success': True,
            'debug_info': debug_info,
            'sample_data': {
                'basic_count': len(basic_response.data) if basic_response.data else 0,
                'join_count': len(join_response.data) if 'join_response' in locals() and join_response.data else 0,
                'filtered_count': len(filtered_response.data) if 'filtered_response' in locals() and filtered_response.data else 0
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'debug_info': debug_info if 'debug_info' in locals() else [],
            'traceback': traceback.format_exc()
        })

# Ruta de prueba para parsing de tarjetas
@app.route('/test_card_parsing', methods=['GET', 'POST'])
def test_card_parsing():
    """Ruta para probar el parsing de tarjetas de banda magnética"""
    
    if request.method == 'POST':
        raw_data = request.form.get('raw_data', '').strip()
        
        if raw_data:
            try:
                # Usar las funciones de tarjeta_utils para debugging
                card_info = get_card_info(raw_data)
                debug_info = debug_card_parsing(raw_data)
                
                # Intentar parsing básico
                parsed_code = parse_card_data(raw_data)
                is_valid = validate_card_format(parsed_code)
                
                result = {
                    'success': True,
                    'raw_data': raw_data,
                    'parsed_code': parsed_code,
                    'is_valid': is_valid,
                    'card_info': card_info,
                    'debug_info': debug_info
                }
                
                print(f"🧪 Test de parsing de tarjeta:")
                print(f"   Datos entrada: '{raw_data}'")
                print(f"   Código parseado: '{parsed_code}'")
                print(f"   Es válido: {is_valid}")
                print(f"   Información: {card_info}")
                
                return jsonify(result)
                
            except Exception as e:
                error_result = {
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'raw_data': raw_data,
                    'traceback': traceback.format_exc()
                }
                
                print(f"❌ Error en test de parsing: {e}")
                return jsonify(error_result)
        else:
            return jsonify({
                'success': False,
                'error': 'No se proporcionaron datos de tarjeta',
                'raw_data': ''
            })
    
    # GET request - mostrar formulario de prueba
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Parsing de Tarjetas</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .form-group { margin: 15px 0; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
            button { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
            button:hover { background: #0056b3; }
            .result { margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 4px; }
            .example { background: #e9ecef; padding: 10px; margin: 10px 0; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧪 Test Parsing de Tarjetas de Banda Magnética</h1>
            
            <form method="POST">
                <div class="form-group">
                    <label for="raw_data">Datos de Tarjeta (pegar aquí los datos del lector):</label>
                    <textarea id="raw_data" name="raw_data" rows="4" placeholder="Pegar datos de la tarjeta aquí..."></textarea>
                </div>
                
                <button type="submit">🔍 Probar Parsing</button>
            </form>
            
            <div class="example">
                <h3>📋 Ejemplos de formatos soportados:</h3>
                <ul>
                    <li><strong>Track 1:</strong> %B123456789^DOE/JOHN^2512101?</li>
                    <li><strong>Track 2:</strong> ;123456789=2512101?</li>
                    <li><strong>Numérico:</strong> 123456789</li>
                    <li><strong>Con prefijo:</strong> EMPL123456</li>
                </ul>
            </div>
            
            <div class="result">
                <h3>ℹ️ Instrucciones:</h3>
                <ol>
                    <li>Pase una tarjeta por el lector</li>
                    <li>Copie los datos que aparecen</li>
                    <li>Péguelos en el campo de texto</li>
                    <li>Haga clic en "Probar Parsing"</li>
                    <li>Revise los resultados en formato JSON</li>
                </ol>
            </div>
        </div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
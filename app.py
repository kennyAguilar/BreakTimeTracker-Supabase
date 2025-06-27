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
    print("🔧 Iniciando conexión a Supabase...")
    
    # Verificar variables de entorno
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_anon_key = os.getenv('SUPABASE_ANON_KEY')
    supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    print(f"📊 SUPABASE_URL: {'✓ Configurada' if supabase_url else '✗ NO ENCONTRADA'}")
    print(f"📊 SUPABASE_ANON_KEY: {'✓ Configurada' if supabase_anon_key else '✗ NO ENCONTRADA'}")
    print(f"📊 SUPABASE_SERVICE_KEY: {'✓ Configurada' if supabase_service_key else '✗ NO ENCONTRADA'}")
    
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
    
    # Intentar crear clientes
    print("🔗 Creando cliente público...")
    supabase: Client = create_client(supabase_url, supabase_anon_key)
    
    print("🔗 Creando cliente administrativo...")
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

# Zona horaria
tz = pytz.timezone('America/Punta_Arenas')

# Decorador para rutas protegidas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Función auxiliar para obtener hora actual en Punta Arenas
def get_current_time():
    return datetime.now(tz)

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
        fin = get_current_time()
        duracion_minutos = int((fin - inicio).total_seconds() / 60)
        tipo = 'COMIDA' if duracion_minutos >= 30 else 'DESCANSO'
        
        print(f"   Duración: {duracion_minutos} min → {tipo}")
        
        # Preparar datos para tiempos_descanso
        tiempo_data = {
            'usuario_id': usuario_id,
            'tipo': tipo,
            'fecha': inicio.date().isoformat(),
            'inicio': inicio.time().isoformat(),
            'fin': fin.time().isoformat(),
            'duracion_minutos': duracion_minutos
        }
        
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
        delete_response = supabase_admin.table('descansos').delete().eq('id', descanso_activo['id']).select("*").execute()
        
        if delete_response.error or not delete_response.data:
            print(f"   ❌ ERROR: Falló eliminación de descanso activo: {delete_response.error or 'sin data'}")
        else:
            print(f"   ✅ Descanso eliminado: {len(delete_response.data)} registros")

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
    mensaje, tipo_mensaje = None, None

    if request.method == 'POST':
        entrada = request.form.get('entrada','').strip()
        if entrada:
            try:
                # 1) Buscar usuario
                resp = supabase.table('usuarios').select('*')\
                              .or_(f"tarjeta.eq.{entrada},codigo.eq.{entrada.upper()}")\
                              .execute()
                usuario = resp.data[0] if resp.data else None

                if not usuario:
                    mensaje, tipo_mensaje = 'Usuario no encontrado', 'error'
                else:
                    # 2) Verificar descanso activo
                    resp2 = supabase_admin.table('descansos')\
                                   .select('*')\
                                   .eq('usuario_id', usuario['id']).execute()
                    descanso = resp2.data[0] if resp2.data else None

                    if descanso:
                        # 3) Cerrar descanso
                        success, msg, _ = cerrar_descanso_usuario(usuario['id'], descanso)
                        mensaje = f"{usuario['nombre']} - Salida registrada ({msg})"
                        tipo_mensaje = 'salida' if success else 'error'
                    else:
                        # 4) Abrir descanso
                        supabase_admin.table('descansos').insert({
                            'usuario_id': usuario['id'],
                            'inicio': get_current_time().isoformat(),
                            'tipo': 'Pendiente'
                        }).execute()
                        mensaje, tipo_mensaje = f"{usuario['nombre']} - Entrada registrada", 'entrada'
            except Exception as e:
                mensaje, tipo_mensaje = f"Error interno: {e}", 'error'

    # Obtener usuarios en descanso con información de usuario
    usuarios_en_descanso = []
    try:
        print(f"\n🔍 === OBTENIENDO USUARIOS EN DESCANSO ===")
        
        # Primero obtener todos los descansos activos
        print(f"📊 Consultando tabla 'descansos' con cliente admin...")
        response = supabase_admin.table('descansos').select("*").execute()
        descansos_activos = response.data
        
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
                        inicio = datetime.fromisoformat(d['inicio'].replace('Z', '+00:00'))
                        ahora = get_current_time()
                        tiempo_transcurrido = int((ahora - inicio).total_seconds() / 60)
                        
                        print(f"   ⏰ Tiempo transcurrido: {tiempo_transcurrido} minutos")
                        print(f"      Inicio: {inicio.strftime('%H:%M:%S')}")
                        print(f"      Ahora: {ahora.strftime('%H:%M:%S')}")
                        
                        # Determinar tiempo máximo y tipo según el tiempo transcurrido
                        tiempo_maximo = 40 if tiempo_transcurrido >= 20 else 20
                        tiempo_restante = max(0, tiempo_maximo - tiempo_transcurrido)
                        tipo = 'Comida' if tiempo_transcurrido >= 20 else 'Descanso'

                        print(f"   📋 Tipo: {tipo}")
                        print(f"   ⏳ Tiempo restante: {tiempo_restante} min")

                        usuario_descanso = {
                            'nombre': usuario_info['nombre'],  # ...existing code...
                            'codigo': usuario_info['codigo'],  # ...existing code...
                            'inicio': inicio,                  # datetime para formato
                            'tipo': tipo,                      # etiqueta coincidente con template
                            'tiempo_restante': tiempo_restante # minutos restantes
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
                import traceback
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
        import traceback
        print(f"Stack trace completo: {traceback.format_exc()}")
        usuarios_en_descanso = []
    
    return render_template('index.html',
                         descansos=usuarios_en_descanso,
                         hora_actual=get_current_time().strftime('%Y-%m-%d %H:%M:%S'),
                         mensaje=mensaje,
                         tipo_mensaje=tipo_mensaje,
                         conexion_status=conexion_supabase_status)

# Login administrativo
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        clave = request.form.get('clave', '').strip()
        
        try:
            # Buscar administrador
            response = supabase.table('administradores').select("*").eq('usuario', usuario).eq('activo', True).execute()
            admin = response.data[0] if response.data else None
            
            if admin and admin['clave'] == clave:  # En producción usar bcrypt
                session.permanent = True
                session['admin_id'] = admin['id']
                session['admin_nombre'] = admin['nombre']
                session['last_activity'] = datetime.now().isoformat()
                return redirect(url_for('registros'))
            else:
                return render_template('login.html', error='Credenciales inválidas')
        except Exception as e:
            return render_template('login.html', error='Error al verificar credenciales')
    
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
    if request.method == 'POST':
        action = request.form.get('action')
        
        try:
            if action == 'add':
                # Agregar nuevo usuario
                nombre = request.form.get('nombre', '').strip()
                tarjeta = request.form.get('tarjeta', '').strip()
                turno = request.form.get('turno', '').strip()
                codigo = request.form.get('codigo', '').strip().upper()
                
                if nombre and tarjeta and turno and codigo:
                    supabase_admin.table('usuarios').insert({
                        'nombre': nombre,
                        'tarjeta': tarjeta,
                        'turno': turno,
                        'codigo': codigo
                    }).execute()
                    
            elif action == 'delete':
                # Eliminar usuario
                user_id = request.form.get('user_id')
                if user_id:
                    supabase_admin.table('usuarios').delete().eq('id', user_id).execute()
                    
        except Exception as e:
            print(f"Error en base_datos: {e}")
    
    # Obtener todos los usuarios
    try:
        response = supabase.table('usuarios').select("*").order('nombre').execute()
        usuarios = response.data
    except Exception as e:
        usuarios = []
        print(f"Error al obtener usuarios: {e}")
    
    return render_template('base_datos.html', usuarios=usuarios)

# Editar usuario
@app.route('/editar_usuario/<user_id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(user_id):
    if request.method == 'POST':
        try:
            # Actualizar usuario
            nombre = request.form.get('nombre', '').strip()
            tarjeta = request.form.get('tarjeta', '').strip()
            turno = request.form.get('turno', '').strip()
            codigo = request.form.get('codigo', '').strip().upper()
            
            if nombre and tarjeta and turno and codigo:
                supabase_admin.table('usuarios').update({
                    'nombre': nombre,
                    'tarjeta': tarjeta,
                    'turno': turno,
                    'codigo': codigo
                }).eq('id', user_id).execute()
                
                return redirect(url_for('base_datos'))
        except Exception as e:
            print(f"Error al actualizar usuario: {e}")
    
    # Obtener usuario
    try:
        response = supabase.table('usuarios').select("*").eq('id', user_id).execute()
        usuario = response.data[0] if response.data else None
        
        if not usuario:
            return redirect(url_for('base_datos'))
            
        return render_template('editar_usuario.html', usuario=usuario)
    except Exception as e:
        print(f"Error al obtener usuario: {e}")
        return redirect(url_for('base_datos'))

# Ver registros
@app.route('/registros')
@login_required
def registros():
    # Obtener parámetros de filtro
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')
    usuario_id = request.args.get('usuario_id', '')
    
    # Si no hay fechas, usar últimos 7 días
    if not fecha_inicio:
        fecha_inicio = (date.today() - timedelta(days=7)).isoformat()
    if not fecha_fin:
        fecha_fin = date.today().isoformat()
    
    try:
        # Construir query
        query = supabase.table('tiempos_descanso').select("*, usuarios(nombre, codigo)")
        
        # Aplicar filtros
        query = query.gte('fecha', fecha_inicio).lte('fecha', fecha_fin)
        
        if usuario_id:
            query = query.eq('usuario_id', usuario_id)
        
        # Ejecutar query
        response = query.order('fecha', desc=True).order('inicio', desc=True).execute()
        registros = response.data
        
        # Formatear registros para mostrar
        for r in registros:
            r['fecha_formateada'] = datetime.fromisoformat(r['fecha']).strftime('%d/%m/%Y')
            r['duracion_formateada'] = f"{r['duracion_minutos']} min"
        
        # Obtener lista de usuarios para el filtro
        response_usuarios = supabase.table('usuarios').select("id, nombre").order('nombre').execute()
        usuarios = response_usuarios.data
        
    except Exception as e:
        print(f"Error al obtener registros: {e}")
        registros = []
        usuarios = []
    
    return render_template('registros.html',
                         registros=registros,
                         usuarios=usuarios,
                         fecha_inicio=fecha_inicio,
                         fecha_fin=fecha_fin,
                         usuario_id=usuario_id)

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
        # Obtener todos los registros del período
        response = supabase.table('tiempos_descanso').select("*, usuarios(nombre, codigo)")\
            .gte('fecha', fecha_inicio)\
            .lte('fecha', fecha_fin)\
            .execute()
        registros = response.data
        
        # Calcular estadísticas
        stats_por_usuario = {}
        stats_por_dia = {}
        total_descansos = 0
        total_comidas = 0
        tiempo_total_descansos = 0
        tiempo_total_comidas = 0
        
        for r in registros:
            usuario_nombre = r['usuarios']['nombre']
            fecha = r['fecha']
            tipo = r['tipo']
            duracion = r['duracion_minutos']
            
            # Stats por usuario
            if usuario_nombre not in stats_por_usuario:
                stats_por_usuario[usuario_nombre] = {
                    'descansos': 0,
                    'comidas': 0,
                    'tiempo_descansos': 0,
                    'tiempo_comidas': 0,
                    'tiempo_total': 0
                }
            
            # Stats por día
            if fecha not in stats_por_dia:
                stats_por_dia[fecha] = {
                    'descansos': 0,
                    'comidas': 0,
                    'usuarios_unicos': set()
                }
            
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
            stats_por_dia[fecha]['usuarios_unicos'].add(usuario_nombre)
        
        # Convertir sets a conteos
        for fecha in stats_por_dia:
            stats_por_dia[fecha]['usuarios_unicos'] = len(stats_por_dia[fecha]['usuarios_unicos'])
        
        # Ordenar usuarios por tiempo total (top 10)
        top_usuarios = sorted(stats_por_usuario.items(), 
                            key=lambda x: x[1]['tiempo_total'], 
                            reverse=True)[:10]
        
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
        print(f"Error al generar reportes: {e}")
        estadisticas = {}
        top_usuarios = []
        datos_grafico = {'fechas': [], 'descansos': [], 'comidas': []}
    
    return render_template('reportes.html',
                         estadisticas=estadisticas,
                         top_usuarios=top_usuarios,
                         datos_grafico=datos_grafico,
                         fecha_inicio=fecha_inicio,
                         fecha_fin=fecha_fin)

# Exportar a CSV
@app.route('/exportar_csv')
@login_required
def exportar_csv():
    fecha_inicio = request.args.get('fecha_inicio', (date.today() - timedelta(days=30)).isoformat())
    fecha_fin = request.args.get('fecha_fin', date.today().isoformat())
    
    try:
        # Obtener registros
        response = supabase.table('tiempos_descanso').select("*, usuarios(nombre, codigo, turno)")\
            .gte('fecha', fecha_inicio)\
            .lte('fecha', fecha_fin)\
            .order('fecha', desc=True)\
            .order('inicio', desc=True)\
            .execute()
        registros = response.data
        
        # Crear CSV en memoria
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Encabezados
        writer.writerow(['Fecha', 'Nombre', 'Código', 'Turno', 'Tipo', 'Entrada', 'Salida', 'Duración (min)'])
        
        # Datos
        for r in registros:
            writer.writerow([
                datetime.fromisoformat(r['fecha']).strftime('%d/%m/%Y'),
                r['usuarios']['nombre'],
                r['usuarios']['codigo'],
                r['usuarios']['turno'],
                r['tipo'],
                r['inicio'],
                r['fin'],
                r['duracion_minutos']
            ])
        
        # Preparar respuesta
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'registros_descansos_{fecha_inicio}_{fecha_fin}.csv'
        )
        
    except Exception as e:
        print(f"Error al exportar CSV: {e}")
        return redirect(url_for('registros'))

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
        html += f"<p><strong>Fecha/Hora:</strong> {get_current_time().strftime('%Y-%m-%d %H:%M:%S')}</p>"
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
            return jsonify({'diagnostico': resultado, 'error': 'Datos insuficientes'})
            
    except Exception as e:
        resultado.append(f"\n❌ ERROR: {str(e)}")
        import traceback
        resultado.append(f"Stack trace: {traceback.format_exc()}")
        return jsonify({'diagnostico': resultado, 'error': str(e)})

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
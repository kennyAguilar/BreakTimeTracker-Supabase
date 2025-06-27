# 🕐 BreakTimeTracker - Versión Supabase

Sistema profesional de control de tiempos de descanso para empresas, ahora con **Supabase** como backend.

## 🚀 Características Principales

### Sistema de Registro
- ✅ Soporte para tarjetas RFID largas
- ✅ Códigos cortos personalizados (KA22, CB29, HP30, etc.)
- ✅ Validación automática de entrada
- ✅ Interface simple tipo "lector industrial"

### Control de Tiempos
- ✅ Descansos cortos: 20 minutos máximo
- ✅ Tiempo de comida: 40 minutos máximo
- ✅ Detección automática según duración
- ✅ Contador en tiempo real
- ✅ Zona horaria Punta Arenas (Chile)

### Panel Administrativo
- ✅ CRUD completo de usuarios
- ✅ Gestión de tarjetas y códigos
- ✅ Turnos de trabajo configurables
- ✅ Validación de datos únicos

### Reportes y Estadísticas
- ✅ Dashboard en tiempo real
- ✅ Historial completo filtrable
- ✅ Exportación a CSV
- ✅ Estadísticas por día/semana
- ✅ Top usuarios más activos

### Seguridad
- ✅ Row Level Security (RLS) de Supabase
- ✅ Sistema multi-administrador
- ✅ Auto-logout por inactividad (30 min)
- ✅ Políticas de acceso granulares

## 🛠️ Stack Tecnológico

| Componente | Tecnología | Versión |
|------------|------------|---------|
| Backend | Python Flask | 2.3.3 |
| Base de Datos | Supabase (PostgreSQL) | Latest |
| Frontend | HTML5 + TailwindCSS | 2.2.19 |
| Autenticación | Session-based + RLS | - |
| Zona Horaria | pytz | 2023.3 |

## 📋 Requisitos

- Python 3.11+
- Cuenta en [Supabase](https://supabase.com)
- Git

## 🔧 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/BreakTimeTracker-Supabase.git
cd BreakTimeTracker-Supabase
```

### 2. Crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Supabase

1. Crear proyecto en [Supabase](https://supabase.com)
2. En el SQL Editor, ejecutar el contenido de `supabase_schema.sql`
3. Obtener las credenciales:
   - Project URL
   - Anon Key
   - Service Role Key

### 5. Configurar variables de entorno

Copiar `.env.example` a `.env` y completar:

```env
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_ANON_KEY=tu-anon-key
SUPABASE_SERVICE_KEY=tu-service-role-key
SECRET_KEY=una-clave-secreta-super-segura
TZ=America/Punta_Arenas
```

### 6. Ejecutar la aplicación

```bash
python app.py
```

Acceder a: http://127.0.0.1:5000

## 🔄 Migración desde PostgreSQL/Neon

Si tienes datos en una base PostgreSQL anterior:

1. Agregar credenciales de la BD antigua en `.env`:
```env
OLD_DB_HOST=tu-host-anterior.neon.tech
OLD_DB_PORT=5432
OLD_DB_NAME=tu-db-anterior
OLD_DB_USER=tu-usuario
OLD_DB_PASSWORD=tu-password
```

2. Ejecutar script de migración:
```bash
python migrate_to_supabase.py
```

## 📱 Uso del Sistema

### Para Empleados

1. **Entrar a descanso**: Deslizar tarjeta o escribir código (ej: KA22)
2. **Ver tiempo restante**: La pantalla muestra el tiempo en tiempo real
3. **Salir de descanso**: Volver a deslizar tarjeta o escribir código

### Para Administradores

1. **Login**: Acceder a `/login` con credenciales
2. **Gestión usuarios**: Agregar, editar, eliminar empleados en `/base_datos`
3. **Ver registros**: Historial completo con filtros en `/registros`
4. **Generar reportes**: Dashboard con estadísticas en `/reportes`
5. **Exportar datos**: Descargar CSV con registros

## 📊 Estructura del Proyecto

```
BreakTimeTracker-Supabase/
├── 📄 app.py                    # Aplicación principal Flask
├── 📄 requirements.txt          # Dependencias Python
├── 📄 .env.example             # Variables de entorno ejemplo
├── 📄 .gitignore               # Archivos ignorados
├── 📄 README.md                # Este archivo
├── 📄 supabase_schema.sql      # Esquema de BD para Supabase
├── 📄 migrate_to_supabase.py   # Script de migración
├── 📁 config/
│   └── 📄 supabase_client.py  # Cliente Supabase
├── 📁 templates/               # Plantillas HTML
│   ├── 📄 index.html          # Lector principal
│   ├── 📄 login.html          # Login administrativo
│   ├── 📄 base_datos.html     # Gestión usuarios
│   ├── 📄 registros.html      # Historial
│   ├── 📄 reportes.html       # Dashboard
│   ├── 📄 editar_usuario.html # Edición usuario
│   └── 📄 error.html          # Página de errores
└── 📁 static/                 # Archivos estáticos
    └── 📄 style.css           # Estilos personalizados
```

## 🌐 API Endpoints

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/` | GET/POST | Lector principal | No |
| `/login` | GET/POST | Login administrativo | No |
| `/logout` | GET | Cerrar sesión | Sí |
| `/base_datos` | GET/POST | Gestión usuarios | Sí |
| `/editar_usuario/<id>` | GET/POST | Editar usuario | Sí |
| `/registros` | GET | Historial registros | Sí |
| `/reportes` | GET | Dashboard estadísticas | Sí |
| `/exportar_csv` | GET | Exportar CSV | Sí |

## 🚀 Deploy

### Opción 1: Render.com

1. Conectar repositorio GitHub
2. Configurar variables de entorno
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn --bind 0.0.0.0:$PORT app:app`

### Opción 2: Railway

1. Importar desde GitHub
2. Agregar variables de entorno
3. Deploy automático

### Opción 3: Vercel

1. Instalar Vercel CLI
2. Configurar `vercel.json`
3. Deploy con `vercel --prod`

## 🔒 Seguridad

- **RLS habilitado**: Políticas a nivel de base de datos
- **Service Key protegida**: Solo para operaciones admin
- **Sesiones seguras**: Auto-logout por inactividad
- **HTTPS requerido**: En producción
- **Passwords**: Usar bcrypt en producción

## 🎯 Ventajas de Supabase

1. **Realtime**: Actualizaciones instantáneas sin polling
2. **Auth integrado**: Sistema de autenticación robusto
3. **Storage**: Para fotos de empleados o documentos
4. **Dashboard visual**: Interface para gestionar datos
5. **Edge Functions**: Lógica serverless
6. **Backups automáticos**: Protección de datos

## 📈 Próximas Mejoras

- [ ] App móvil con React Native
- [ ] Notificaciones push
- [ ] Integración con sistemas de nómina
- [ ] API REST documentada
- [ ] Autenticación con Supabase Auth
- [ ] Reportes PDF automáticos
- [ ] Multi-empresa en una instancia
- [ ] Integración con lectores RFID USB

## 🤝 Contribuir

1. Fork el proyecto
2. Crear rama feature (`git checkout -b feature/NuevaCaracteristica`)
3. Commit cambios (`git commit -m 'Agregar nueva característica'`)
4. Push a la rama (`git push origin feature/NuevaCaracteristica`)
5. Abrir Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 👥 Contacto

**Tu Nombre**
- GitHub: [@tu-usuario](https://github.com/tu-usuario)
- Email: [tu-email@ejemplo.com](mailto:tu-email@ejemplo.com)

---

## 🏢 Casos de Uso

✅ Empresas manufactureras con turnos rotativos  
✅ Call centers con control estricto de tiempo  
✅ Oficinas corporativas con políticas de descanso  
✅ Retail con múltiples empleados por turno  
✅ Hospitales/clínicas con personal 24/7  

## 🐛 Reporte de Problemas

Si encuentras algún problema:

1. 📧 Crear Issue en GitHub
2. 📱 Contactar por email
3. 📋 Incluir logs y pasos para reproducir

---

⭐ **¡Si te gusta el proyecto, dale una estrella en GitHub!** ⭐

Desarrollado con ❤️ en Punta Arenas, Chile 🇨🇱
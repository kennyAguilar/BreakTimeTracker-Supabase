# BreakTimeTracker - Supabase

## Estado del Proyecto
✅ **Migración completada y proyecto limpio**

### Funcionalidades Implementadas
- Sistema de autenticación de usuarios
- Registro y gestión de descansos
- Diferentes tipos de turno: **Full**, **Part Time**, **Llamado**
- Cálculo automático de tiempo restante
- Reportes y estadísticas
- Interfaz web responsive

### Archivos Principales
- `app.py` - Aplicación Flask principal
- `config/supabase_client.py` - Configuración de Supabase
- `templates/` - Plantillas HTML
- `static/style.css` - Estilos CSS
- `requirements.txt` - Dependencias Python
- `.env` - Variables de entorno (no incluido en Git)

### Configuración de Base de Datos
La base de datos en Supabase tiene las siguientes restricciones configuradas:
- Campo `turno` acepta únicamente: 'Full', 'Part Time', 'Llamado'
- Columna `turno` expandida a VARCHAR(20) para soportar 'Part Time'
- Constraint `usuarios_turno_check` actualizado correctamente

### Correcciones Aplicadas
1. **Constraint de Turno**: Actualizado para aceptar los nuevos valores
2. **Cálculo de Tiempo**: Corregido el bug de "NaN" en tiempo restante
3. **Formularios**: Actualizados para usar los nuevos valores de turno
4. **Validación**: Implementada validación backend y frontend

### Para Ejecutar la Aplicación
```bash
# Activar entorno virtual
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno en .env:
SUPABASE_URL=tu_url_de_supabase
SUPABASE_KEY=tu_clave_de_supabase

# Ejecutar aplicación
python app.py
```

### Notas de Despliegue
- Asegúrate de que el archivo `.env` esté configurado correctamente
- La base de datos debe tener las tablas creadas según el esquema
- Los valores de turno están restringidos a nivel de base de datos

---
*Limpieza completada - Archivos de migración y prueba eliminados*

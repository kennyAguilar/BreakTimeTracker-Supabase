"""
Integración con Google Sheets para BreakTimeTracker
====================================================

Este módulo permite exportar datos directamente a Google Sheets.
Para usar esta funcionalidad, necesitas:

1. Crear un proyecto en Google Cloud Console
2. Habilitar Google Sheets API
3. Crear credenciales de servicio (archivo JSON)
4. Compartir tu hoja de cálculo con el email del servicio

Instalación de dependencias:
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

Configuración:
1. Descarga el archivo de credenciales JSON
2. Colócalo en config/google_credentials.json
3. Añade estas variables al .env:
   GOOGLE_SHEETS_ENABLED=true
   GOOGLE_SHEET_ID=tu_sheet_id_aqui
"""

import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

# Importaciones opcionales de Google Sheets
try:
    from google.auth.transport.requests import Request
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    print("⚠️ Google Sheets no está disponible. Para habilitarlo, instala: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")

class GoogleSheetsExporter:
    """Exportador de datos a Google Sheets"""
    
    def __init__(self):
        self.enabled = os.getenv('GOOGLE_SHEETS_ENABLED', 'false').lower() == 'true'
        self.sheet_id = os.getenv('GOOGLE_SHEET_ID')
        self.credentials_file = os.path.join(os.path.dirname(__file__), 'google_credentials.json')
        self.service = None
        
        if self.enabled and GOOGLE_SHEETS_AVAILABLE:
            self._initialize_service()
    
    def _initialize_service(self):
        """Inicializar servicio de Google Sheets"""
        try:
            if not os.path.exists(self.credentials_file):
                print(f"❌ Archivo de credenciales no encontrado: {self.credentials_file}")
                self.enabled = False
                return
            
            # Scopes necesarios para Google Sheets
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
            
            # Crear credenciales
            creds = Credentials.from_service_account_file(
                self.credentials_file, 
                scopes=SCOPES
            )
            
            # Construir servicio
            self.service = build('sheets', 'v4', credentials=creds)
            print("✅ Google Sheets API inicializada correctamente")
            
        except Exception as e:
            print(f"❌ Error inicializando Google Sheets: {e}")
            self.enabled = False
    
    def is_available(self) -> bool:
        """Verificar si Google Sheets está disponible"""
        return self.enabled and GOOGLE_SHEETS_AVAILABLE and self.service is not None
    
    def export_registros_completos(self, registros: List[Dict], sheet_name: str = "Registros") -> bool:
        """Exportar registros completos a Google Sheets"""
        if not self.is_available():
            return False
        
        try:
            # Preparar datos
            headers = [
                'Fecha', 'Día Semana', 'Nombre', 'Código', 'Turno', 
                'Tipo', 'Entrada', 'Salida', 'Duración (min)', 
                'Duración (h)', 'Exceso (min)', 'Estado'
            ]
            
            data = [headers]
            
            for r in registros:
                try:
                    fecha_obj = datetime.fromisoformat(r['fecha'])
                    usuario_data = r.get('usuarios', {})
                    duracion = r.get('duracion_minutos', 0)
                    tipo = r.get('tipo', 'DESCANSO')
                    
                    # Calcular exceso
                    limite = 40 if tipo == 'COMIDA' else 20
                    exceso = max(0, duracion - limite)
                    
                    # Estado
                    if exceso > 30:
                        estado = 'EXCESO ALTO'
                    elif exceso > 0:
                        estado = 'CON EXCESO'
                    else:
                        estado = 'NORMAL'
                    
                    row = [
                        fecha_obj.strftime('%d/%m/%Y'),
                        fecha_obj.strftime('%A').capitalize(),
                        usuario_data.get('nombre', 'Desconocido'),
                        usuario_data.get('codigo', 'N/A'),
                        usuario_data.get('turno', 'N/A'),
                        tipo,
                        r.get('inicio', 'N/A'),
                        r.get('fin', 'N/A'),
                        duracion,
                        round(duracion / 60, 2),
                        exceso,
                        estado
                    ]
                    
                    data.append(row)
                    
                except Exception as e_row:
                    print(f"⚠️ Error procesando registro para Sheets: {e_row}")
                    continue
            
            # Escribir a Google Sheets
            return self._write_to_sheet(data, sheet_name)
            
        except Exception as e:
            print(f"❌ Error exportando registros completos: {e}")
            return False
    
    def export_resumen_usuarios(self, stats_usuarios: Dict, sheet_name: str = "Resumen") -> bool:
        """Exportar resumen por usuarios a Google Sheets"""
        if not self.is_available():
            return False
        
        try:
            headers = [
                'Nombre', 'Código', 'Turno', 'Total Descansos', 'Total Comidas',
                'Tiempo Descansos (min)', 'Tiempo Comidas (min)', 'Tiempo Total (h)',
                'Promedio Descanso', 'Promedio Comida', 'Exceso Total (min)', 'Estado'
            ]
            
            data = [headers]
            
            for nombre, stats in stats_usuarios.items():
                try:
                    tiempo_total_min = stats['tiempo_descansos'] + stats['tiempo_comidas']
                    exceso_total = stats.get('exceso_total', 0)
                    
                    # Estado
                    if exceso_total > 120:
                        estado = 'CRÍTICO'
                    elif exceso_total > 60:
                        estado = 'ALTO EXCESO'
                    elif exceso_total > 30:
                        estado = 'MODERADO'
                    elif exceso_total > 0:
                        estado = 'LEVE EXCESO'
                    else:
                        estado = 'ÓPTIMO'
                    
                    row = [
                        nombre,
                        stats.get('codigo', 'N/A'),
                        stats.get('turno', 'N/A'),
                        stats['descansos'],
                        stats['comidas'],
                        stats['tiempo_descansos'],
                        stats['tiempo_comidas'],
                        round(tiempo_total_min / 60, 2),
                        round(stats['tiempo_descansos'] / stats['descansos'], 1) if stats['descansos'] > 0 else 0,
                        round(stats['tiempo_comidas'] / stats['comidas'], 1) if stats['comidas'] > 0 else 0,
                        exceso_total,
                        estado
                    ]
                    
                    data.append(row)
                    
                except Exception as e_user:
                    print(f"⚠️ Error procesando usuario {nombre}: {e_user}")
                    continue
            
            return self._write_to_sheet(data, sheet_name)
            
        except Exception as e:
            print(f"❌ Error exportando resumen usuarios: {e}")
            return False
    
    def _write_to_sheet(self, data: List[List], sheet_name: str) -> bool:
        """Escribir datos a una hoja específica"""
        try:
            if not self.sheet_id:
                print("❌ GOOGLE_SHEET_ID no configurado")
                return False
            
            # Verificar si la hoja existe, si no, crearla
            self._ensure_sheet_exists(sheet_name)
            
            # Limpiar hoja existente
            clear_range = f"{sheet_name}!A:Z"
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.sheet_id,
                range=clear_range
            ).execute()
            
            # Escribir nuevos datos
            range_name = f"{sheet_name}!A1"
            body = {
                'values': data
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            print(f"✅ {result.get('updatedCells')} celdas actualizadas en {sheet_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error escribiendo a Google Sheets: {e}")
            return False
    
    def _ensure_sheet_exists(self, sheet_name: str):
        """Asegurar que la hoja existe, si no, crearla"""
        try:
            # Obtener información del spreadsheet
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=self.sheet_id
            ).execute()
            
            # Verificar si la hoja ya existe
            sheets = sheet_metadata.get('sheets', [])
            sheet_exists = any(
                sheet['properties']['title'] == sheet_name 
                for sheet in sheets
            )
            
            if not sheet_exists:
                # Crear nueva hoja
                request_body = {
                    'requests': [
                        {
                            'addSheet': {
                                'properties': {
                                    'title': sheet_name
                                }
                            }
                        }
                    ]
                }
                
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.sheet_id,
                    body=request_body
                ).execute()
                
                print(f"✅ Hoja '{sheet_name}' creada")
                
        except Exception as e:
            print(f"⚠️ Error verificando/creando hoja: {e}")
    
    def create_dashboard_sheet(self, estadisticas: Dict) -> bool:
        """Crear hoja de dashboard con estadísticas generales"""
        if not self.is_available():
            return False
        
        try:
            dashboard_data = [
                ['DASHBOARD - ESTADÍSTICAS GENERALES'],
                ['Fecha de actualización', datetime.now().strftime('%d/%m/%Y %H:%M:%S')],
                [],
                ['TOTALES GENERALES'],
                ['Total Descansos', estadisticas.get('total_descansos', 0)],
                ['Total Comidas', estadisticas.get('total_comidas', 0)],
                ['Tiempo Total Descansos (min)', estadisticas.get('tiempo_total_descansos', 0)],
                ['Tiempo Total Comidas (min)', estadisticas.get('tiempo_total_comidas', 0)],
                [],
                ['PROMEDIOS'],
                ['Promedio Descanso (min)', estadisticas.get('promedio_descanso', 0)],
                ['Promedio Comida (min)', estadisticas.get('promedio_comida', 0)],
                [],
                ['INFORMACIÓN'],
                ['Este dashboard se actualiza automáticamente'],
                ['Datos exportados desde BreakTimeTracker'],
                ['Para más detalles, ver hojas "Registros" y "Resumen"']
            ]
            
            return self._write_to_sheet(dashboard_data, "Dashboard")
            
        except Exception as e:
            print(f"❌ Error creando dashboard: {e}")
            return False

# Instancia global del exportador
google_sheets_exporter = GoogleSheetsExporter()

def export_to_google_sheets(registros: List[Dict], stats_usuarios: Dict = None, estadisticas: Dict = None) -> bool:
    """
    Función principal para exportar todos los datos a Google Sheets
    
    Args:
        registros: Lista de registros completos
        stats_usuarios: Diccionario con estadísticas por usuario
        estadisticas: Diccionario con estadísticas generales
    
    Returns:
        bool: True si la exportación fue exitosa
    """
    if not google_sheets_exporter.is_available():
        print("⚠️ Google Sheets no está disponible o configurado")
        return False
    
    try:
        success = True
        
        # Exportar registros completos
        if registros:
            print("📊 Exportando registros completos...")
            success &= google_sheets_exporter.export_registros_completos(registros)
        
        # Exportar resumen por usuarios
        if stats_usuarios:
            print("📈 Exportando resumen por usuarios...")
            success &= google_sheets_exporter.export_resumen_usuarios(stats_usuarios)
        
        # Crear dashboard
        if estadisticas:
            print("📉 Creando dashboard...")
            success &= google_sheets_exporter.create_dashboard_sheet(estadisticas)
        
        if success:
            print("✅ Exportación a Google Sheets completada")
        else:
            print("⚠️ Exportación a Google Sheets completada con errores")
        
        return success
        
    except Exception as e:
        print(f"❌ Error en exportación a Google Sheets: {e}")
        return False

# Función de configuración para uso futuro
def configure_google_sheets():
    """
    Instrucciones para configurar Google Sheets
    """
    instructions = """
    📋 CONFIGURACIÓN DE GOOGLE SHEETS
    ================================
    
    1. Ve a Google Cloud Console (https://console.cloud.google.com/)
    2. Crea un nuevo proyecto o selecciona uno existente
    3. Habilita la Google Sheets API
    4. Ve a "Credenciales" y crea una cuenta de servicio
    5. Descarga el archivo JSON de credenciales
    6. Guárdalo como config/google_credentials.json
    7. Crea una hoja de cálculo en Google Sheets
    8. Comparte la hoja con el email de la cuenta de servicio (editor)
    9. Copia el ID de la hoja (está en la URL)
    10. Añade estas variables a tu .env:
        GOOGLE_SHEETS_ENABLED=true
        GOOGLE_SHEET_ID=tu_sheet_id_aqui
    
    📝 NOTAS:
    - El ID de la hoja está en la URL: /spreadsheets/d/[ID_AQUI]/edit
    - La cuenta de servicio necesita permisos de editor
    - Los datos se actualizarán automáticamente al exportar
    """
    return instructions

if __name__ == "__main__":
    # Test de configuración
    print(configure_google_sheets())
    
    if google_sheets_exporter.is_available():
        print("✅ Google Sheets está configurado y listo")
    else:
        print("❌ Google Sheets no está configurado")
        print("📋 Sigue las instrucciones de configuración arriba")

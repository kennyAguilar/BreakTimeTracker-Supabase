"""
Utilidades para parsing de tarjetas de banda magnética
=====================================================

Este módulo contiene todas las funciones necesarias para parsear datos de tarjetas
de banda magnética en diferentes formatos. Incluye validación, limpieza y extracción
de información útil para el sistema de control de descansos.

Características:
- Soporte para múltiples formatos de tarjeta
- Limpieza automática de caracteres especiales
- Validación de formato
- Extracción de códigos de empleado
- Logging detallado para debugging

Autor: Sistema BreakTimeTracker
Fecha: Julio 2025
"""

import re
import logging
from typing import Optional, Dict, Any


def parse_card_data(raw_data: str) -> str:
    """
    Parsea datos de tarjeta de banda magnética y extrae información útil.
    
    Esta función maneja múltiples formatos de tarjetas de banda magnética:
    - Formato Track 1: %B + datos + ?
    - Formato Track 2: ; + datos + ?
    - Formato mixto con múltiples tracks
    - Datos numéricos puros
    
    Args:
        raw_data (str): Datos crudos de la tarjeta leída por el lector
        
    Returns:
        str: Código limpio extraído de la tarjeta
        
    Examples:
        >>> parse_card_data("%B123456789^DOE/JOHN^2512101?")
        "123456789"
        
        >>> parse_card_data(";123456789=2512101?")
        "123456789"
        
        >>> parse_card_data("123456789")
        "123456789"
    """
    if not raw_data:
        return ""
    
    # Log de entrada para debugging
    print(f"🔍 parse_card_data - Entrada: '{raw_data}'")
    
    # Limpiar espacios en blanco al inicio y final
    cleaned_data = raw_data.strip()
    
    # Si está vacío después de limpiar, retornar vacío
    if not cleaned_data:
        print(f"⚠️ parse_card_data - Datos vacíos después de limpiar")
        return ""
    
    # Intentar diferentes patrones de parsing
    result = None
    
    # Patrón 1: Track 1 (%B...^...^...?)
    track1_match = re.search(r'%B(\d+)\^', cleaned_data)
    if track1_match:
        result = track1_match.group(1)
        print(f"✅ parse_card_data - Patrón Track 1 encontrado: '{result}'")
        return result
    
    # Patrón 2: Track 2 (;...=...?)
    track2_match = re.search(r';(\d+)=', cleaned_data)
    if track2_match:
        result = track2_match.group(1)
        print(f"✅ parse_card_data - Patrón Track 2 encontrado: '{result}'")
        return result
    
    # Patrón 3: Secuencia numérica larga (más de 6 dígitos)
    numeric_match = re.search(r'\d{6,}', cleaned_data)
    if numeric_match:
        result = numeric_match.group(0)
        print(f"✅ parse_card_data - Secuencia numérica encontrada: '{result}'")
        return result
    
    # Patrón 4: Limpiar caracteres especiales y quedarse con alfanuméricos
    alphanumeric_only = re.sub(r'[^a-zA-Z0-9]', '', cleaned_data)
    if alphanumeric_only and len(alphanumeric_only) >= 3:
        result = alphanumeric_only
        print(f"✅ parse_card_data - Datos alfanuméricos limpiados: '{result}'")
        return result
    
    # Si no se encontró ningún patrón conocido, retornar datos originales limpiados
    print(f"⚠️ parse_card_data - No se encontró patrón conocido, retornando datos originales")
    return cleaned_data


def validate_card_format(card_data: str) -> bool:
    """
    Valida si los datos de la tarjeta tienen un formato válido.
    
    Args:
        card_data (str): Datos de la tarjeta a validar
        
    Returns:
        bool: True si el formato es válido, False en caso contrario
        
    Examples:
        >>> validate_card_format("123456789")
        True
        
        >>> validate_card_format("abc")
        False
        
        >>> validate_card_format("")
        False
    """
    if not card_data:
        return False
    
    # Debe tener al menos 3 caracteres
    if len(card_data) < 3:
        return False
    
    # Debe contener al menos algunos caracteres alfanuméricos
    if not re.search(r'[a-zA-Z0-9]', card_data):
        return False
    
    # No debe ser solo caracteres especiales
    if re.match(r'^[^a-zA-Z0-9]+$', card_data):
        return False
    
    return True


def get_card_info(raw_data: str) -> Dict[str, Any]:
    """
    Extrae información completa de una tarjeta de banda magnética.
    
    Args:
        raw_data (str): Datos crudos de la tarjeta
        
    Returns:
        Dict[str, Any]: Diccionario con información extraída:
            - parsed_code: Código limpio extraído
            - is_valid: Si el formato es válido
            - track_info: Información sobre el track detectado
            - raw_length: Longitud de los datos originales
            - clean_length: Longitud de los datos limpios
            
    Examples:
        >>> get_card_info("%B123456789^DOE/JOHN^2512101?")
        {
            'parsed_code': '123456789',
            'is_valid': True,
            'track_info': 'Track 1',
            'raw_length': 28,
            'clean_length': 9
        }
    """
    if not raw_data:
        return {
            'parsed_code': '',
            'is_valid': False,
            'track_info': 'No data',
            'raw_length': 0,
            'clean_length': 0,
            'error': 'No data provided'
        }
    
    # Parsear el código
    parsed_code = parse_card_data(raw_data)
    
    # Validar formato
    is_valid = validate_card_format(parsed_code)
    
    # Detectar tipo de track
    track_info = 'Unknown'
    if '%B' in raw_data and '^' in raw_data:
        track_info = 'Track 1 (ISO/IEC 7813)'
    elif ';' in raw_data and '=' in raw_data:
        track_info = 'Track 2 (ISO/IEC 7813)'
    elif re.match(r'^\d+$', raw_data.strip()):
        track_info = 'Numeric only'
    elif re.search(r'\d{6,}', raw_data):
        track_info = 'Contains long numeric sequence'
    else:
        track_info = 'Custom format'
    
    return {
        'parsed_code': parsed_code,
        'is_valid': is_valid,
        'track_info': track_info,
        'raw_length': len(raw_data),
        'clean_length': len(parsed_code),
        'has_track1': '%B' in raw_data,
        'has_track2': ';' in raw_data,
        'numeric_sequences': re.findall(r'\d{3,}', raw_data),
        'special_chars': len(re.findall(r'[^a-zA-Z0-9]', raw_data))
    }


def extract_employee_code(card_data: str, fallback_patterns: Optional[list] = None) -> str:
    """
    Extrae específicamente el código de empleado de los datos de la tarjeta.
    
    Esta función está optimizada para extraer códigos de empleado usando
    patrones específicos de la organización.
    
    Args:
        card_data (str): Datos de la tarjeta
        fallback_patterns (list, optional): Patrones adicionales a probar
        
    Returns:
        str: Código de empleado extraído
        
    Examples:
        >>> extract_employee_code("EMPL123456")
        "123456"
        
        >>> extract_employee_code("E123456789")
        "123456789"
    """
    if not card_data:
        return ""
    
    # Primero usar el parser general
    general_parsed = parse_card_data(card_data)
    
    # Patrones específicos para códigos de empleado
    employee_patterns = [
        r'EMPL(\d+)',           # EMPL123456
        r'EMP(\d+)',            # EMP123456
        r'E(\d{6,})',           # E123456789
        r'ID(\d+)',             # ID123456
        r'USER(\d+)',           # USER123456
        r'CARD(\d+)',           # CARD123456
    ]
    
    # Agregar patrones adicionales si se proporcionan
    if fallback_patterns:
        employee_patterns.extend(fallback_patterns)
    
    # Probar patrones específicos
    for pattern in employee_patterns:
        match = re.search(pattern, card_data.upper())
        if match:
            result = match.group(1)
            print(f"✅ extract_employee_code - Patrón '{pattern}' encontrado: '{result}'")
            return result
    
    # Si no se encontró patrón específico, usar resultado general
    print(f"ℹ️ extract_employee_code - Usando parser general: '{general_parsed}'")
    return general_parsed


def clean_card_data(raw_data: str) -> str:
    """
    Limpia los datos de la tarjeta eliminando caracteres problemáticos.
    
    Args:
        raw_data (str): Datos crudos de la tarjeta
        
    Returns:
        str: Datos limpios
        
    Examples:
        >>> clean_card_data("  %B123^DOE?  ")
        "%B123^DOE?"
        
        >>> clean_card_data("123\n456\r789")
        "123456789"
    """
    if not raw_data:
        return ""
    
    # Eliminar espacios en blanco al inicio y final
    cleaned = raw_data.strip()
    
    # Eliminar saltos de línea y retornos de carro
    cleaned = re.sub(r'[\r\n\t]', '', cleaned)
    
    # Eliminar caracteres de control (excepto los específicos de banda magnética)
    cleaned = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', cleaned)
    
    return cleaned


def is_magnetic_stripe_format(data: str) -> bool:
    """
    Determina si los datos corresponden a una tarjeta de banda magnética.
    
    Args:
        data (str): Datos a verificar
        
    Returns:
        bool: True si parece ser formato de banda magnética
        
    Examples:
        >>> is_magnetic_stripe_format("%B123456789^DOE/JOHN^2512101?")
        True
        
        >>> is_magnetic_stripe_format("123456789")
        False
    """
    if not data:
        return False
    
    # Indicadores de formato de banda magnética
    magnetic_indicators = [
        r'%[A-Z]',          # Inicio de Track 1
        r';\d+=',           # Patrón de Track 2
        r'\^[A-Z/\s]+\^',   # Nombre en Track 1
        r'=\d{4}',          # Fecha de expiración en Track 2
        r'\?\s*$',          # Terminador de track
    ]
    
    # Verificar si coincide con algún indicador
    for pattern in magnetic_indicators:
        if re.search(pattern, data):
            return True
    
    return False


def debug_card_parsing(raw_data: str) -> Dict[str, Any]:
    """
    Función de debugging para analizar el parsing de tarjetas.
    
    Args:
        raw_data (str): Datos crudos de la tarjeta
        
    Returns:
        Dict[str, Any]: Información detallada de debugging
    """
    print(f"\n🔍 === DEBUG CARD PARSING ===")
    print(f"📥 Datos de entrada: '{raw_data}'")
    print(f"📏 Longitud: {len(raw_data)} caracteres")
    
    # Información básica
    debug_info = {
        'raw_data': raw_data,
        'raw_length': len(raw_data),
        'is_empty': not bool(raw_data),
        'has_whitespace': bool(re.search(r'\s', raw_data)) if raw_data else False,
        'has_special_chars': bool(re.search(r'[^a-zA-Z0-9]', raw_data)) if raw_data else False,
    }
    
    if not raw_data:
        print(f"❌ Datos vacíos")
        return debug_info
    
    # Análisis de caracteres
    print(f"🔤 Análisis de caracteres:")
    print(f"   - Contiene espacios: {debug_info['has_whitespace']}")
    print(f"   - Contiene caracteres especiales: {debug_info['has_special_chars']}")
    print(f"   - Caracteres únicos: {len(set(raw_data))}")
    
    # Verificar formato de banda magnética
    is_magnetic = is_magnetic_stripe_format(raw_data)
    debug_info['is_magnetic_stripe'] = is_magnetic
    print(f"🧲 Es formato de banda magnética: {is_magnetic}")
    
    # Probar parsing
    try:
        parsed_result = parse_card_data(raw_data)
        debug_info['parsed_result'] = parsed_result
        debug_info['parsing_success'] = True
        print(f"✅ Resultado del parsing: '{parsed_result}'")
    except Exception as e:
        debug_info['parsed_result'] = ""
        debug_info['parsing_success'] = False
        debug_info['parsing_error'] = str(e)
        print(f"❌ Error en parsing: {e}")
    
    # Obtener información completa
    try:
        card_info = get_card_info(raw_data)
        debug_info['card_info'] = card_info
        print(f"📊 Información de tarjeta: {card_info}")
    except Exception as e:
        debug_info['card_info_error'] = str(e)
        print(f"❌ Error obteniendo info de tarjeta: {e}")
    
    print(f"🔍 === FIN DEBUG ===\n")
    return debug_info


# Función de prueba para verificar el módulo
def test_card_parsing():
    """
    Función de prueba para verificar el funcionamiento del módulo.
    """
    print("🧪 === PRUEBAS DE PARSING DE TARJETAS ===\n")
    
    # Casos de prueba
    test_cases = [
        # Formato Track 1
        "%B123456789^DOE/JOHN^2512101?",
        "%B4111111111111111^DOE/JANE^25121015432112345678?",
        
        # Formato Track 2
        ";123456789=2512101?",
        ";4111111111111111=25121015432112345678?",
        
        # Formato mixto
        "%B123456789^DOE/JOHN^2512101?;123456789=2512101?",
        
        # Numérico puro
        "123456789",
        "4111111111111111",
        
        # Datos con prefijos
        "EMPL123456",
        "E123456789",
        "ID987654321",
        
        # Datos problemáticos
        "  123456789  ",
        "123\n456\r789",
        "abc123def456",
        "",
        "!@#$%^&*()",
    ]
    
    for i, test_data in enumerate(test_cases, 1):
        print(f"📋 Prueba {i}: '{test_data}'")
        
        try:
            # Parsing básico
            result = parse_card_data(test_data)
            print(f"   ✅ Resultado: '{result}'")
            
            # Validación
            is_valid = validate_card_format(result)
            print(f"   📊 Válido: {is_valid}")
            
            # Información completa
            card_info = get_card_info(test_data)
            print(f"   📄 Tipo: {card_info['track_info']}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
    
    print("🧪 === FIN PRUEBAS ===\n")


# Ejecutar pruebas si el módulo se ejecuta directamente
if __name__ == "__main__":
    test_card_parsing()

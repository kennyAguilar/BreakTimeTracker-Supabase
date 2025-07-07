"""
Módulo Core de Base de Datos
===========================

Maneja la inicialización y configuración básica de los clientes de Supabase.
"""

from typing import Optional
from supabase import Client

# Variables globales para los clientes de Supabase
_supabase_client: Optional[Client] = None
_supabase_admin: Optional[Client] = None

def initialize_db_clients(supabase_client: Client, supabase_admin: Client):
    """
    Inicializa los clientes de Supabase para uso en las utilidades
    
    Args:
        supabase_client: Cliente público de Supabase
        supabase_admin: Cliente administrativo de Supabase
    """
    global _supabase_client, _supabase_admin
    _supabase_client = supabase_client
    _supabase_admin = supabase_admin
    print("✅ Clientes de base de datos inicializados en db_core")

def get_client() -> Client:
    """Obtiene el cliente público de Supabase"""
    if _supabase_client is None:
        raise RuntimeError("Cliente de Supabase no inicializado. Llama a initialize_db_clients() primero.")
    return _supabase_client

def get_admin_client() -> Client:
    """Obtiene el cliente administrativo de Supabase"""
    if _supabase_admin is None:
        raise RuntimeError("Cliente administrativo de Supabase no inicializado. Llama a initialize_db_clients() primero.")
    return _supabase_admin
#!/usr/bin/env python3
"""
Punto de entrada principal para el Microsoft To Do Analyzer.
"""
import sys
from utils.config import load_env_file
from utils.auth import get_access_token_device_code
from utils.client import MicrosoftTodoClient

def main():
    # 1. Cargar configuración
    env = load_env_file()
    client_id = env.get('CLIENT_ID')
    
    if not client_id:
        print("❌ Error: No se encontró CLIENT_ID en config.env")
        print("Por favor, ejecuta 'python setup_guide.py' primero.")
        sys.exit(1)

    tenant_id = env.get('TENANT_ID', 'consumers')
    list_name = env.get('DEFAULT_LIST_NAME', 'Tasks')

    print(f"🚀 Iniciando Microsoft To Do Analyzer...")
    print(f"📋 Lista a analizar: {list_name}")

    try:
        # 2. Autenticación
        token = get_access_token_device_code(client_id, tenant_id)
        
        # 3. Inicializar cliente
        client = MicrosoftTodoClient(token)
        
        # 4. Analizar lista
        print("🔄 Obteniendo datos de Microsoft To Do...")
        analysis = client.analyze_list(list_name)
        
        # 5. Mostrar resultados
        client.print_analysis(analysis)
        
    except Exception as e:
        print(f"\n❌ Ocurrió un error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

import os
from typing import Dict

def load_env_file(filename: str = 'config.env') -> Dict[str, str]:
    """
    Carga variables de entorno desde un archivo .env
    
    Args:
        filename: Nombre del archivo .env
        
    Returns:
        Diccionario con las variables de entorno
    """
    env_vars = {}
    
    if not os.path.exists(filename):
        return env_vars
    
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Ignorar líneas vacías y comentarios
            if not line or line.startswith('#'):
                continue
            
            # Separar clave=valor
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars

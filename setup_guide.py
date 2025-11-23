#!/usr/bin/env python3
"""
Guía interactiva para configurar Microsoft To Do Analyzer
Este script te guía paso a paso para configurar Azure AD correctamente.
"""

import webbrowser
import time
import sys

def print_header():
    print("=" * 70)
    print("🎯 GUÍA DE CONFIGURACIÓN - MICROSOFT TO DO ANALYZER")
    print("=" * 70)

def print_step(step_num, title, description):
    print(f"\n📋 PASO {step_num}: {title}")
    print("-" * 50)
    print(description)

def wait_for_user():
    input("\n⏳ Presiona Enter cuando hayas completado este paso...")

def open_browser(url):
    print(f"\n🌐 Abriendo navegador: {url}")
    try:
        webbrowser.open(url)
    except:
        print(f"❌ No se pudo abrir el navegador automáticamente.")
        print(f"   Ve manualmente a: {url}")

def main():
    print_header()

    print("\nEste asistente te guiará paso a paso para configurar Azure AD")
    print("y poder usar el Microsoft To Do Analyzer correctamente.")

    print("\n⚠️  NOTA IMPORTANTE:")
    print("   - Usa una cuenta personal de Microsoft (@outlook.com, @hotmail.com, etc.)")
    print("   - NO uses cuenta corporativa/organizacional para este ejemplo")
    print("   - El proceso toma aproximadamente 5-10 minutos")

    input("\nPresiona Enter para comenzar...")

    # PASO 1: Crear aplicación
    print_step(1, "Crear aplicación en Azure Portal",
               "1. Ve a: https://portal.azure.com\n" +
               "2. Inicia sesión con tu cuenta de Microsoft\n" +
               "3. Busca 'Azure Active Directory' o 'Microsoft Entra ID'\n" +
               "4. En el menú lateral, selecciona 'App registrations'\n" +
               "5. Click en '+ New registration'\n" +
               "6. Nombre: 'Microsoft To Do Analyzer'\n" +
               "7. Supported account types: 'Personal Microsoft accounts only'\n" +
               "8. Redirect URI: Deja vacío\n" +
               "9. Click en 'Register'")

    open_browser("https://portal.azure.com")
    wait_for_user()

    # PASO 2: Configurar permisos
    print_step(2, "Configurar permisos de API",
               "1. En la página de tu aplicación, ve a 'API permissions'\n" +
               "2. Click en '+ Add a permission'\n" +
               "3. Selecciona 'Microsoft Graph'\n" +
               "4. Selecciona 'Delegated permissions'\n" +
               "5. Busca y marca: 'Tasks.Read'\n" +
               "6. Click en 'Add permissions'\n" +
               "7. Click en 'Grant admin consent' (si aparece)")

    wait_for_user()

    # PASO 3: Configurar autenticación
    print_step(3, "Configurar autenticación",
               "1. Ve a 'Authentication' en el menú lateral\n" +
               "2. Desplázate hasta 'Advanced settings'\n" +
               "3. En 'Allow public client flows', selecciona 'Yes'\n" +
               "4. Click en 'Save'")

    wait_for_user()

    # PASO 4: Obtener CLIENT_ID
    print_step(4, "Obtener Application (Client) ID",
               "1. En la página 'Overview' de tu aplicación\n" +
               "2. Copia el 'Application (client) ID'\n" +
               "3. Es un GUID largo como: '12345678-1234-1234-1234-123456789abc'\n" +
               "4. Pégalo en el archivo config.env como CLIENT_ID")

    print("\n📝 FORMATO DEL ARCHIVO config.env:")
    print("-" * 40)
    print("CLIENT_ID=TU_CLIENT_ID_AQUI")
    print("TENANT_ID=consumers")
    print("DEFAULT_LIST_NAME=Tasks")
    print("-" * 40)

    wait_for_user()

    # PASO 5: Probar configuración
    print_step(5, "Probar la configuración",
               "1. Asegúrate de que config.env tenga tu CLIENT_ID correcto\n" +
               "2. Ejecuta: python main.py\n" +
               "3. Sigue las instrucciones de autenticación que aparecerán")

    print("\n✅ ¡Configuración completa!")
    print("\nAhora puedes usar el Microsoft To Do Analyzer.")
    print("El script te pedirá autorización la primera vez que lo uses.")

    print("\n🔧 Comandos útiles:")
    print("- python main.py")

    print("\n📖 Para más detalles, consulta el archivo README.md")

if __name__ == "__main__":
    main()

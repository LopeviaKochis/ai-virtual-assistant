"""
Script de prueba para validar conexión a Azure Cosmos DB.
Ejecutar: python -m tests.test_cosmos_connection
"""
import sys
import asyncio
from datetime import datetime
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from clients.cosmos_client import cosmos_client
from models.user_profile import UserProfile
from utils.logging import setup_logging

setup_logging()

def test_connection():
    """Test 1: Verificar conexión básica"""
    print("\n" + "="*60)
    print("TEST 1: Verificando conexión a Cosmos DB")
    print("="*60)
    
    if not cosmos_client._is_configured():
        print("ERROR: Cosmos DB no está configurado correctamente")
        print("   Verifica que COSMOS_ENDPOINT y COSMOS_KEY estén en .env")
        return False
    
    print("Cliente Cosmos DB inicializado correctamente")
    return True

def test_create_profile():
    """Test 2: Crear perfil de prueba"""
    print("\n" + "="*60)
    print("TEST 2: Creando perfil de prueba")
    print("="*60)
    
    test_contact_id = "test_12345"
    
    # Crear perfil
    profile = UserProfile(
        contactId=test_contact_id,
        firstName="Usuario",
        lastName="Prueba",
        dni="12345678",
        phone="987654321",
        channelId="439657",
        channelSource="telegram",
        preferredLanguage="es"
    )
    
    print(f"Creando perfil para contactId: {test_contact_id}")
    
    try:
        result = cosmos_client.upsert_profile(profile.model_dump())
        print(f"Perfil creado exitosamente")
        print(f"   ID: {result.get('id')}")
        print(f"   Timestamp: {result.get('_ts')}")
        return True
    except Exception as e:
        print(f" ERROR al crear perfil: {e}")
        return False

def test_retrieve_profile():
    """Test 3: Recuperar perfil"""
    print("\n" + "="*60)
    print("TEST 3: Recuperando perfil de prueba")
    print("="*60)
    
    test_contact_id = "test_12345"
    
    profile = cosmos_client.get_profile(test_contact_id)
    
    if profile:
        print(f"Perfil recuperado exitosamente")
        print(f"   Nombre: {profile.get('firstName')} {profile.get('lastName')}")
        print(f"   DNI: {profile.get('dni')}")
        print(f"   Teléfono: {profile.get('phone')}")
        return True
    else:
        print(f" No se encontró el perfil")
        return False

def test_search_by_dni():
    """Test 4: Buscar por DNI"""
    print("\n" + "="*60)
    print("TEST 4: Buscando perfil por DNI")
    print("="*60)
    
    test_dni = "12345678"
    
    profile = cosmos_client.find_by_dni(test_dni)
    
    if profile:
        print(f"Perfil encontrado por DNI: {test_dni}")
        print(f"   Contact ID: {profile.get('contactId')}")
        print(f"   Nombre: {profile.get('firstName')}")
        return True
    else:
        print(f"No se encontró perfil con DNI: {test_dni}")
        return False

def test_cleanup():
    """Test 5: Limpiar perfil de prueba"""
    print("\n" + "="*60)
    print("TEST 5: Limpiando perfil de prueba")
    print("="*60)
    
    test_contact_id = "test_12345"
    
    success = cosmos_client.delete_profile(test_contact_id)
    
    if success:
        print(f"Perfil eliminado exitosamente")
        return True
    else:
        print(f" No se pudo eliminar el perfil (puede que no exista)")
        return False

def main():
    """Ejecuta todos los tests"""
    print("\n" + " INICIANDO TESTS DE COSMOS DB ")
    
    results = []
    
    # Test 1: Conexión
    results.append(("Conexión", test_connection()))
    
    if not results[0][1]:
        print("\nTests abortados: no hay conexión a Cosmos DB")
        return
    
    # Test 2: Crear perfil
    results.append(("Crear perfil", test_create_profile()))
    
    # Test 3: Recuperar perfil
    results.append(("Recuperar perfil", test_retrieve_profile()))
    
    # Test 4: Buscar por DNI
    results.append(("Buscar por DNI", test_search_by_dni()))
    
    # Test 5: Cleanup
    results.append(("Limpiar datos", test_cleanup()))
    
    # Resumen
    print("\n" + "="*60)
    print("RESUMEN DE TESTS")
    print("="*60)
    
    for test_name, passed in results:
        status = "PASS" if passed else " FAIL"
        print(f"  {status} - {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests pasados")
    
    if passed == total:
        print("\nTodos los tests pasaron piola")
    else:
        print("\n Algunos tests fallaron, revisa la configuración")

if __name__ == "__main__":
    main()
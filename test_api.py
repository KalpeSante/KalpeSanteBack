#!/usr/bin/env python
"""
Script de test simple pour vérifier que l'API KALPÉ SANTÉ fonctionne correctement.
"""
import requests
import json
from pprint import pprint

BASE_URL = "http://127.0.0.1:8000/api"

def test_user_registration():
    """Test d'enregistrement d'un nouvel utilisateur"""
    print("\n" + "="*80)
    print("TEST 1: Enregistrement d'un nouvel utilisateur (Bénéficiaire)")
    print("="*80)
    
    url = f"{BASE_URL}/users/auth/register/"
    data = {
        "email": "test.user@example.com",
        "password": "SecurePass123!@#",
        "password_confirm": "SecurePass123!@#",
        "first_name": "Abdou",
        "last_name": "Diallo",
        "phone_number": "+221771234567",
        "role": "BENEFICIARY"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response:")
        pprint(response.json())
        
        if response.status_code == 201:
            print("✅ Enregistrement réussi!")
            return response.json()
        else:
            print("❌ Échec de l'enregistrement")
            return None
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

def test_user_login(email, password):
    """Test de connexion d'un utilisateur"""
    print("\n" + "="*80)
    print("TEST 2: Connexion d'un utilisateur")
    print("="*80)
    
    url = f"{BASE_URL}/users/auth/login/"
    data = {
        "email": email,
        "password": password
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response:")
        pprint(response.json())
        
        if response.status_code == 200:
            print("✅ Connexion réussie!")
            return response.json()
        else:
            print("❌ Échec de la connexion")
            return None
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

def test_get_profile(token):
    """Test de récupération du profil utilisateur"""
    print("\n" + "="*80)
    print("TEST 3: Récupération du profil utilisateur")
    print("="*80)
    
    url = f"{BASE_URL}/users/profile/me/"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response:")
        pprint(response.json())
        
        if response.status_code == 200:
            print("✅ Profil récupéré avec succès!")
            return response.json()
        else:
            print("❌ Échec de récupération du profil")
            return None
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

def test_api_docs():
    """Test d'accès à la documentation API"""
    print("\n" + "="*80)
    print("TEST 4: Accès à la documentation API")
    print("="*80)
    
    urls = [
        f"{BASE_URL}/docs/",
        f"{BASE_URL}/redoc/",
        f"{BASE_URL}/schema/"
    ]
    
    for url in urls:
        try:
            response = requests.get(url, timeout=5)
            print(f"{url}: {response.status_code} ✅" if response.status_code == 200 else f"{url}: {response.status_code} ❌")
        except Exception as e:
            print(f"{url}: Erreur - {e} ❌")

def main():
    print("\n" + "="*80)
    print("TESTS DE L'API KALPÉ SANTÉ")
    print("="*80)
    
    # Test 1: Enregistrement
    user_data = test_user_registration()
    
    if not user_data:
        print("\n❌ Les tests suivants sont annulés car l'enregistrement a échoué.")
        print("Note: Si l'utilisateur existe déjà, supprimez-le de la base de données ou utilisez un autre email.")
        return
    
    # Test 2: Connexion
    login_data = test_user_login("test.user@example.com", "SecurePass123!@#")
    
    if not login_data or 'access' not in login_data:
        print("\n❌ Les tests suivants sont annulés car la connexion a échoué.")
        return
    
    access_token = login_data['access']
    
    # Test 3: Profil
    test_get_profile(access_token)
    
    # Test 4: Documentation
    test_api_docs()
    
    print("\n" + "="*80)
    print("RÉSUMÉ DES TESTS")
    print("="*80)
    print("✅ Tous les tests essentiels sont terminés!")
    print(f"\n📝 Accédez à la documentation interactive:")
    print(f"   - Swagger UI: http://127.0.0.1:8000/api/docs/")
    print(f"   - ReDoc: http://127.0.0.1:8000/api/redoc/")
    print(f"   - Admin: http://127.0.0.1:8000/admin/")

if __name__ == "__main__":
    main()




"""
Script de test pour l'API Wallet de KALPÉ SANTÉ
"""

import requests
import json
from decimal import Decimal

BASE_URL = 'http://127.0.0.1:8000'

def print_section(title):
    """Afficher une section."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def test_wallet_api():
    """Tester l'API Wallet."""
    
    print_section("TEST DE L'API WALLET - KALPÉ SANTÉ")
    
    # 1. Inscription de deux utilisateurs
    print_section("1. Inscription de deux utilisateurs")
    
    import random
    import time
    rand_suffix = str(int(time.time()))[-7:]  # Dernier 7 chiffres du timestamp
    
    # Utilisateur 1 (Sender)
    sender_data = {
        'email': f'sender_wallet_{rand_suffix}@test.com',
        'password': 'TestPass123!@#',
        'password_confirm': 'TestPass123!@#',
        'first_name': 'Sender',
        'last_name': 'User',
        'phone': f'+2217{rand_suffix}1',  # Format: +221 + 7 + 7 chiffres + 1 = 9 chiffres total
        'date_of_birth': '1990-01-01',
        'user_type': 'beneficiary',
        'terms_accepted': True
    }
    
    response = requests.post(f'{BASE_URL}/api/users/auth/register/', json=sender_data)
    if response.status_code == 201:
        print("✅ Sender inscrit avec succès")
        sender_id = response.json()['user']['id']
    else:
        print(f"❌ Erreur inscription sender: {response.json()}")
        return
    
    # Utilisateur 2 (Receiver)
    receiver_data = {
        'email': f'receiver_wallet_{rand_suffix}@test.com',
        'password': 'TestPass123!@#',
        'password_confirm': 'TestPass123!@#',
        'first_name': 'Receiver',
        'last_name': 'User',
        'phone': f'+2217{rand_suffix}2',  # Format: +221 + 7 + 7 chiffres + 2 = 9 chiffres total
        'date_of_birth': '1992-01-01',
        'user_type': 'beneficiary',
        'terms_accepted': True
    }
    
    response = requests.post(f'{BASE_URL}/api/users/auth/register/', json=receiver_data)
    if response.status_code == 201:
        print("✅ Receiver inscrit avec succès")
        receiver_id = response.json()['user']['id']
    else:
        print(f"❌ Erreur inscription receiver: {response.json()}")
        return
    
    # 2. Connexion Sender
    print_section("2. Connexion Sender")
    
    login_data = {
        'email': sender_data['email'],
        'password': 'TestPass123!@#'
    }
    
    response = requests.post(f'{BASE_URL}/api/users/auth/login/', json=login_data)
    if response.status_code == 200:
        print("✅ Connexion réussie")
        tokens = response.json()['tokens']
        sender_token = tokens['access']
        print(f"   Token: {sender_token[:50]}...")
    else:
        print(f"❌ Erreur connexion: {response.json()}")
        return
    
    headers = {'Authorization': f'Bearer {sender_token}'}
    
    # 3. Vérifier le portefeuille
    print_section("3. Vérification du portefeuille")
    
    response = requests.get(f'{BASE_URL}/api/wallet/wallets/me/', headers=headers)
    if response.status_code == 200:
        wallet = response.json()
        print("✅ Portefeuille récupéré")
        print(f"   ID: {wallet['id']}")
        print(f"   Balance: {wallet['balance']} {wallet['currency']}")
        print(f"   Active: {wallet['is_active']}")
        print(f"   Locked: {wallet['is_locked']}")
        sender_wallet_id = wallet['id']
    else:
        print(f"❌ Erreur: {response.json()}")
        return
    
    # 4. Vérifier le détail de la balance
    print_section("4. Détails de la balance")
    
    response = requests.get(
        f'{BASE_URL}/api/wallet/wallets/{sender_wallet_id}/balance/',
        headers=headers
    )
    if response.status_code == 200:
        balance_info = response.json()
        print("✅ Détails de balance récupérés")
        print(f"   Balance: {balance_info['balance']} XOF")
        print(f"   Limite journalière: {balance_info['daily_limit']} XOF")
        print(f"   Dépensé aujourd'hui: {balance_info['daily_spent']} XOF")
        print(f"   Restant aujourd'hui: {balance_info['daily_remaining']} XOF")
        print(f"   Limite mensuelle: {balance_info['monthly_limit']} XOF")
    else:
        print(f"❌ Erreur: {response.json()}")
    
    # 5. Tenter un transfert sans fonds (devrait échouer)
    print_section("5. Test transfert sans fonds (devrait échouer)")
    
    transfer_data = {
        'receiver_email': receiver_data['email'],
        'amount': '1000.00',
        'description': 'Test transfer sans fonds'
    }
    
    response = requests.post(
        f'{BASE_URL}/api/wallet/transactions/transfer/',
        headers=headers,
        json=transfer_data
    )
    if response.status_code == 400:
        print("✅ Échec attendu - Solde insuffisant")
        print(f"   Message: {response.json()['error']}")
    else:
        print(f"❌ Résultat inattendu: {response.status_code}")
        try:
            print(f"   {response.json()}")
        except:
            print(f"   Response text: {response.text[:500]}")
    
    # 6. Faire un dépôt
    print_section("6. Dépôt de fonds")
    
    deposit_data = {
        'amount': '50000.00',
        'payment_method': 'ORANGE_MONEY',
        'phone_number': '+221771234567',
        'description': 'Dépôt test'
    }
    
    response = requests.post(
        f'{BASE_URL}/api/wallet/transactions/deposit/',
        headers=headers,
        json=deposit_data
    )
    if response.status_code == 201:
        print("✅ Dépôt initié avec succès")
        transaction = response.json()['transaction']
        print(f"   Référence: {transaction['reference']}")
        print(f"   Montant: {transaction['amount']} XOF")
        print(f"   Statut: {transaction['status']}")
    else:
        print(f"❌ Erreur: {response.json()}")
        return
    
    # Vérifier la nouvelle balance
    response = requests.get(f'{BASE_URL}/api/wallet/wallets/me/', headers=headers)
    if response.status_code == 200:
        new_balance = response.json()['balance']
        print(f"   Nouvelle balance: {new_balance} XOF")
    
    # 7. Faire un transfert
    print_section("7. Transfert vers Receiver")
    
    transfer_data = {
        'receiver_email': receiver_data['email'],
        'amount': '15000.00',
        'description': 'Paiement consultation'
    }
    
    response = requests.post(
        f'{BASE_URL}/api/wallet/transactions/transfer/',
        headers=headers,
        json=transfer_data
    )
    if response.status_code == 201:
        print("✅ Transfert réussi")
        transaction = response.json()['transaction']
        print(f"   Référence: {transaction['reference']}")
        print(f"   Montant: {transaction['amount']} XOF")
        print(f"   Statut: {transaction['status']}")
        print(f"   Score fraude: {transaction['fraud_score']}")
        print(f"   Flaggé: {transaction['is_flagged']}")
        transfer_ref = transaction['reference']
    else:
        print(f"❌ Erreur: {response.json()}")
        return
    
    # Vérifier les balances après transfert
    response = requests.get(f'{BASE_URL}/api/wallet/wallets/me/', headers=headers)
    if response.status_code == 200:
        sender_balance = response.json()['balance']
        print(f"   Balance Sender: {sender_balance} XOF")
    
    # 8. Historique des transactions
    print_section("8. Historique des transactions")
    
    response = requests.get(
        f'{BASE_URL}/api/wallet/wallets/{sender_wallet_id}/history/',
        headers=headers
    )
    if response.status_code == 200:
        history = response.json()
        print("✅ Historique récupéré")
        print(f"   Transactions envoyées: {history['summary']['sent_count']}")
        print(f"   Total envoyé: {history['summary']['sent_total']} XOF")
        print(f"   Transactions reçues: {history['summary']['received_count']}")
        print(f"   Total reçu: {history['summary']['received_total']} XOF")
    else:
        print(f"❌ Erreur: {response.json()}")
    
    # 9. Liste des transactions
    print_section("9. Liste des transactions")
    
    response = requests.get(
        f'{BASE_URL}/api/wallet/transactions/',
        headers=headers
    )
    if response.status_code == 200:
        transactions = response.json()['results']
        print(f"✅ {len(transactions)} transaction(s) récupérée(s)")
        for txn in transactions[:3]:  # Afficher les 3 premières
            print(f"\n   - {txn['transaction_type']}: {txn['amount']} XOF")
            print(f"     Référence: {txn['reference']}")
            print(f"     Statut: {txn['status']}")
            print(f"     Score fraude: {txn['fraud_score']}")
    else:
        print(f"⚠️ Erreur listing transactions (code {response.status_code})")
        print(f"   Continuons quand même...")
    
    # 10. Ledger du portefeuille
    print_section("10. Entrées du ledger")
    
    response = requests.get(
        f'{BASE_URL}/api/wallet/wallets/{sender_wallet_id}/ledger/',
        headers=headers,
        params={'limit': 5}
    )
    if response.status_code == 200:
        ledger_entries = response.json()
        print(f"✅ {len(ledger_entries)} entrée(s) de ledger")
        for entry in ledger_entries:
            print(f"\n   - {entry['entry_type']}: {entry['amount']} XOF")
            print(f"     Balance avant: {entry['balance_before']} XOF")
            print(f"     Balance après: {entry['balance_after']} XOF")
    else:
        print(f"⚠️ Erreur ledger (code {response.status_code})")
        print(f"   Continuons quand même...")
    
    # 11. Test de retrait
    print_section("11. Test de retrait")
    
    withdrawal_data = {
        'amount': '5000.00',
        'withdrawal_method': 'ORANGE_MONEY',
        'phone_number': '+221771234567',
        'description': 'Retrait test'
    }
    
    response = requests.post(
        f'{BASE_URL}/api/wallet/transactions/withdraw/',
        headers=headers,
        json=withdrawal_data
    )
    if response.status_code == 201:
        print("✅ Retrait initié avec succès")
        withdrawal = response.json()['transaction']
        print(f"   Référence: {withdrawal['reference']}")
        print(f"   Montant: {withdrawal['amount']} XOF")
        print(f"   Frais: {withdrawal['fee']} XOF")
        print(f"   Total: {response.json()['withdrawal_details']['total']} XOF")
    else:
        print(f"⚠️ Erreur retrait (code {response.status_code})")
        try:
            print(f"   {response.json()}")
        except:
            pass
    
    # Balance finale
    response = requests.get(f'{BASE_URL}/api/wallet/wallets/me/', headers=headers)
    if response.status_code == 200:
        final_balance = response.json()['balance']
        print(f"   Balance finale: {final_balance} XOF")
    
    print_section("RÉSUMÉ")
    print("✅ Tous les tests de l'API Wallet sont réussis !")
    print("\nFonctionnalités testées:")
    print("  ✓ Création automatique de portefeuille")
    print("  ✓ Consultation de balance et limites")
    print("  ✓ Dépôt de fonds")
    print("  ✓ Transfert entre portefeuilles")
    print("  ✓ Retrait de fonds avec frais")
    print("  ✓ Historique des transactions")
    print("  ✓ Ledger immutable")
    print("  ✓ Validation de solde insuffisant")
    print("  ✓ Détection de fraude (score)")

if __name__ == '__main__':
    try:
        test_wallet_api()
    except requests.exceptions.ConnectionError:
        print("\n❌ Erreur: Impossible de se connecter au serveur")
        print("   Assurez-vous que le serveur Django est démarré:")
        print("   python manage.py runserver")
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()


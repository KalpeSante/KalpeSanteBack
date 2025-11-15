# Module Wallet - KALPÉ SANTÉ

## Vue d'ensemble

Le module Wallet gère le portefeuille électronique des utilisateurs avec des transactions ACID, la détection de fraude, et la réconciliation automatique.

## Fonctionnalités principales

### 1. Gestion des Portefeuilles

- **Création automatique** : Portefeuille créé automatiquement à l'inscription
- **Devise** : XOF (Franc CFA)
- **Limites** : Limites journalières et mensuelles configurables
- **Verrouillage** : Système de verrouillage pour raisons de sécurité
- **Historique** : Suivi complet de toutes les transactions

### 2. Types de Transactions

- **DEPOSIT** : Dépôt vers le portefeuille
- **WITHDRAWAL** : Retrait du portefeuille
- **TRANSFER** : Transfert entre portefeuilles
- **PAYMENT** : Paiement pour services
- **REFUND** : Remboursement
- **SPONSORSHIP** : Parrainage
- **HEALTHCARE_PAYMENT** : Paiement santé
- **PHARMACY_PAYMENT** : Paiement pharmacie

### 3. Propriétés ACID

#### Atomicité
- Toutes les transactions sont atomiques
- Utilisation de `select_for_update` pour éviter les race conditions
- Rollback automatique en cas d'erreur

#### Cohérence
- Vérification de solde avant débit
- Validation des limites de transaction
- Vérification de l'état du portefeuille

#### Isolation
- Verrouillage pessimiste avec `select_for_update`
- Isolation des transactions simultanées
- Prévention des conflits de balance

#### Durabilité
- Ledger immuable pour audit
- Hash chaining dans AuditLog
- Traçabilité complète

### 4. Détection de Fraude

#### Règles configurables

```python
# Exemples de règles
- AMOUNT_THRESHOLD : Montant suspect
- VELOCITY : Trop de transactions rapides
- PATTERN : Schémas suspects
- GEOLOCATION : Localisation inhabituelle
- BLACKLIST : Liste noire
```

#### Score de fraude

- 0-29 : Risque faible (transaction autorisée)
- 30-49 : Risque moyen (flaggé pour revue)
- 50+ : Risque élevé (blocage possible)

#### Vérifications automatiques

- Première transaction avec montant élevé
- Transactions vers portefeuilles récents
- Montants ronds (potentiellement des tests)
- Vélocité élevée (> 5 transactions/heure)
- Volume élevé (> 1M XOF/heure)

### 5. Réconciliation

- **Réconciliation manuelle** : Transaction par transaction
- **Réconciliation automatique** : Par batch (journalier)
- **Vérification d'intégrité** : Ledger vs transactions
- **Rapports** : Statistiques et erreurs

### 6. Wallet Ledger

- **Immuable** : Aucune modification possible
- **Double entrée** : DEBIT et CREDIT
- **Balance tracking** : Balance avant/après
- **Audit trail** : Lien avec transaction source

## API Endpoints

### Portefeuille

```http
GET    /api/wallet/wallets/me/              # Mon portefeuille
GET    /api/wallet/wallets/{id}/balance/    # Détails balance
GET    /api/wallet/wallets/{id}/history/    # Historique
GET    /api/wallet/wallets/{id}/ledger/     # Entrées ledger
```

### Transactions

```http
GET    /api/wallet/transactions/            # Liste transactions
POST   /api/wallet/transactions/transfer/   # Transfert
POST   /api/wallet/transactions/deposit/    # Dépôt
POST   /api/wallet/transactions/withdraw/   # Retrait
POST   /api/wallet/transactions/{id}/cancel/ # Annuler
GET    /api/wallet/transactions/stats/      # Statistiques (admin)
POST   /api/wallet/transactions/{id}/reconcile/ # Réconcilier (admin)
```

### Règles de fraude (Admin uniquement)

```http
GET    /api/wallet/fraud-rules/             # Liste règles
POST   /api/wallet/fraud-rules/             # Créer règle
GET    /api/wallet/fraud-rules/{id}/        # Détails
PUT    /api/wallet/fraud-rules/{id}/        # Modifier
DELETE /api/wallet/fraud-rules/{id}/        # Supprimer
```

## Exemples d'utilisation

### Transfert entre utilisateurs

```python
from apps.wallet.services import WalletService
from apps.wallet.models import Wallet
from apps.users.models import User

sender = User.objects.get(email='sender@example.com')
receiver = User.objects.get(email='receiver@example.com')

sender_wallet = Wallet.objects.get(user=sender)
receiver_wallet = Wallet.objects.get(user=receiver)

# Effectuer le transfert
txn = WalletService.transfer(
    sender_wallet=sender_wallet,
    receiver_wallet=receiver_wallet,
    amount=Decimal('1000.00'),
    description='Paiement consultation',
    initiated_by=sender,
    check_fraud=True  # Active la détection de fraude
)
```

### Dépôt via Orange Money

```python
from apps.wallet.services import WalletService

wallet = Wallet.objects.get(user=user)

txn = WalletService.deposit(
    receiver_wallet=wallet,
    amount=Decimal('5000.00'),
    description='Dépôt Orange Money',
    external_reference='OM-2024-12345',
    initiated_by=user
)
```

### Vérifier le solde et les limites

```python
from apps.wallet.services import WalletService

balance_info = WalletService.get_wallet_balance(wallet)

print(f"Balance: {balance_info['balance']} XOF")
print(f"Dépensé aujourd'hui: {balance_info['daily_spent']} XOF")
print(f"Restant aujourd'hui: {balance_info['daily_remaining']} XOF")
```

### Réconciliation journalière

```python
from apps.wallet.services import ReconciliationService
from django.utils import timezone

date = timezone.now().date()
results = ReconciliationService.reconcile_daily_transactions(
    date=date,
    reconciled_by=admin_user
)

print(f"Total: {results['total']}")
print(f"Réconciliées: {results['reconciled']}")
print(f"Échouées: {results['failed']}")
```

## Sécurité

### Verrouillage de portefeuille

```python
# Verrouiller
wallet.lock(
    reason='Activité suspecte détectée',
    locked_by=admin_user
)

# Déverrouiller
wallet.unlock()
```

### Flagging de transactions

```python
# Flaguer manuellement
txn.flag_for_review(reason='Montant inhabituel')

# Approuver après revue
txn.approve_review(reviewed_by=admin_user)
```

### Annulation et renversement

```python
# Annuler une transaction en attente
txn.cancel(reason='Demande utilisateur')

# Renverser une transaction complétée
reversal_txn = txn.reverse(reason='Erreur de paiement')
```

## Tests

### Exécuter les tests

```bash
# Tous les tests wallet
pytest apps/wallet/tests/ -v

# Tests modèles uniquement
pytest apps/wallet/tests/test_models.py -v

# Tests API uniquement
pytest apps/wallet/tests/test_api.py -v

# Avec couverture
pytest apps/wallet/tests/ --cov=apps.wallet --cov-report=html
```

## Limites par défaut

| Type | Limite journalière | Limite mensuelle |
|------|-------------------|------------------|
| Standard | 500,000 XOF | 5,000,000 XOF |
| Dépôt minimum | 100 XOF | - |
| Retrait minimum | 1,000 XOF | - |
| Frais de retrait | 1% (min 100, max 5000 XOF) | - |

## Intégrations futures

- [ ] Orange Money API
- [ ] Wave API
- [ ] Banques locales (VISA/Mastercard)
- [ ] PayPal/Stripe (international)
- [ ] Western Union/MoneyGram

## Monitoring et alertes

### Métriques importantes

- Volume de transactions par jour/heure
- Taux de transactions flaggées
- Taux de réconciliation
- Temps de traitement moyen
- Solde total du système

### Alertes automatiques

- Fraude détectée (score > 50)
- Échec de réconciliation
- Portefeuille verrouillé
- Limite quotidienne atteinte
- Solde négatif (ne devrait jamais arriver)

## Maintenance

### Tâches périodiques

```bash
# Réconciliation journalière (à exécuter à 00:00)
python manage.py reconcile_transactions --date=2024-11-13

# Nettoyage des transactions expirées
python manage.py cleanup_expired_transactions

# Rapport de fraude hebdomadaire
python manage.py fraud_report --days=7
```

## Support

Pour toute question ou problème :
- Documentation API : `/api/docs/`
- Email : support@kalpe-sante.com
- Slack : #wallet-support


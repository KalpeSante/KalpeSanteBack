# Module Healthcare - KALPÉ SANTÉ 🏥

## Vue d'ensemble

Le module Healthcare est le **cœur métier** de KALPÉ SANTÉ. Il gère l'ensemble du parcours patient depuis la prise de rendez-vous jusqu'à la consultation et la délivrance de l'ordonnance.

## 🎯 Fonctionnalités

### 1. Gestion des Prestataires de Santé
- Enregistrement des établissements (hôpitaux, cliniques, centres médicaux)
- Vérification et validation par l'administration
- Gestion des spécialités et services
- Notation et avis
- Partenariat CMU

### 2. Billets de Santé (Health Tickets)
- Création de rendez-vous médicaux
- Workflow complet en 10 états
- QR codes pour vérification rapide
- Intégration paiement (Wallet)
- Gestion priorités (Normal, Urgent, Urgence)

### 3. Dossiers Médicaux Électroniques
- Enregistrement des consultations
- Signes vitaux complets
- Diagnostic et plan de traitement
- Historique médical du patient
- Suivi et rendez-vous de contrôle

### 4. Ordonnances Médicales
- Émission d'ordonnances électroniques
- Détail des médicaments (dosage, fréquence, durée)
- QR codes pour vérification en pharmacie
- Gestion de l'expiration
- Traçabilité de la délivrance

## 📡 API Endpoints

### Healthcare Providers

```http
GET    /api/healthcare/providers/                    # Liste des prestataires
GET    /api/healthcare/providers/{id}/                # Détails d'un prestataire
GET    /api/healthcare/providers/accepting_patients/  # Prestataires acceptant nouveaux patients
GET    /api/healthcare/providers/cmu_partners/        # Prestataires CMU
GET    /api/healthcare/providers/top_rated/           # Prestataires les mieux notés
GET    /api/healthcare/providers/{id}/statistics/     # Statistiques (prestataire only)
```

### Health Tickets

```http
GET    /api/healthcare/tickets/                  # Liste des tickets
POST   /api/healthcare/tickets/                  # Créer un ticket
GET    /api/healthcare/tickets/{id}/             # Détails d'un ticket
GET    /api/healthcare/tickets/my_tickets/       # Mes tickets
GET    /api/healthcare/tickets/upcoming/         # Rendez-vous à venir
POST   /api/healthcare/tickets/{id}/update_status/ # Modifier le statut
POST   /api/healthcare/tickets/{id}/cancel/      # Annuler un ticket
```

### Medical Records

```http
GET    /api/healthcare/medical-records/          # Liste des dossiers
POST   /api/healthcare/medical-records/          # Créer un dossier (doctor only)
GET    /api/healthcare/medical-records/{id}/     # Détails d'un dossier
GET    /api/healthcare/medical-records/my_records/ # Mes dossiers médicaux
```

### Prescriptions

```http
GET    /api/healthcare/prescriptions/            # Liste des ordonnances
POST   /api/healthcare/prescriptions/            # Créer une ordonnance (doctor only)
GET    /api/healthcare/prescriptions/{id}/       # Détails d'une ordonnance
GET    /api/healthcare/prescriptions/my_prescriptions/ # Mes ordonnances
GET    /api/healthcare/prescriptions/active/     # Ordonnances actives
POST   /api/healthcare/prescriptions/{id}/dispense/ # Délivrer (pharmacy only)
```

## 💡 Exemples d'utilisation

### 1. Créer un rendez-vous médical

```python
import requests

url = 'http://localhost:8000/api/healthcare/tickets/'
headers = {'Authorization': 'Bearer YOUR_TOKEN'}

data = {
    'provider_id': 'uuid-du-prestataire',
    'appointment_date': '2024-11-20T10:00:00Z',
    'specialty': 'Médecine générale',
    'consultation_type': 'general',
    'priority': 'normal',
    'reason': 'Consultation de routine',
    'symptoms': 'Fatigue, maux de tête'
}

response = requests.post(url, headers=headers, json=data)
ticket = response.json()
print(f"Ticket créé: {ticket['ticket_number']}")
print(f"QR Code: {ticket['qr_code']}")
```

### 2. Enregistrer l'arrivée du patient (Check-in)

```python
ticket_id = 'uuid-du-ticket'
url = f'http://localhost:8000/api/healthcare/tickets/{ticket_id}/update_status/'
headers = {'Authorization': 'Bearer PROVIDER_TOKEN'}

data = {
    'action': 'check_in',
    'notes': 'Patient arrivé à 10h'
}

response = requests.post(url, headers=headers, json=data)
```

### 3. Créer un dossier médical (Médecin)

```python
url = 'http://localhost:8000/api/healthcare/medical-records/'
headers = {'Authorization': 'Bearer DOCTOR_TOKEN'}

data = {
    'health_ticket': 'uuid-du-ticket',
    'chief_complaint': 'Fatigue chronique',
    'temperature': 37.2,
    'blood_pressure_systolic': 120,
    'blood_pressure_diastolic': 80,
    'heart_rate': 72,
    'weight': 70.5,
    'height': 175.0,
    'physical_examination': 'Examen physique normal',
    'diagnosis': 'Syndrome de fatigue chronique',
    'treatment_plan': 'Repos, vitamine B12, contrôle dans 2 semaines',
    'follow_up_required': True,
    'follow_up_date': '2024-12-04'
}

response = requests.post(url, headers=headers, json=data)
```

### 4. Émettre une ordonnance

```python
url = 'http://localhost:8000/api/healthcare/prescriptions/'
headers = {'Authorization': 'Bearer DOCTOR_TOKEN'}

data = {
    'health_ticket_id': 'uuid-du-ticket',
    'medical_record_id': 'uuid-du-dossier',
    'expiry_days': 30,
    'notes': 'À prendre pendant les repas',
    'medications': [
        {
            'medication_name': 'Paracétamol 500mg',
            'dosage': '500mg',
            'frequency': '3 fois par jour',
            'duration': '7 jours',
            'quantity': 2,
            'instructions': 'Après les repas'
        },
        {
            'medication_name': 'Vitamine B12',
            'dosage': '1000mcg',
            'frequency': '1 fois par jour',
            'duration': '30 jours',
            'quantity': 1,
            'instructions': 'Le matin à jeun'
        }
    ]
}

response = requests.post(url, headers=headers, json=data)
prescription = response.json()
print(f"Ordonnance: {prescription['prescription_number']}")
```

### 5. Délivrer une ordonnance (Pharmacie)

```python
prescription_id = 'uuid-de-ordonnance'
url = f'http://localhost:8000/api/healthcare/prescriptions/{prescription_id}/dispense/'
headers = {'Authorization': 'Bearer PHARMACY_TOKEN'}

data = {
    'pharmacy_name': 'Pharmacie du Centre',
    'notes': 'Tous les médicaments délivrés'
}

response = requests.post(url, headers=headers, json=data)
```

## 🔄 Workflow complet

```
1. PATIENT crée un Health Ticket
   ↓
2. PATIENT paie via Wallet
   ↓
3. PATIENT arrive et scanne QR code (Check-in)
   ↓
4. MÉDECIN appelle le patient (Start consultation)
   ↓
5. MÉDECIN examine et crée le Medical Record
   ↓
6. MÉDECIN termine la consultation
   ↓
7. MÉDECIN émet une Prescription (si nécessaire)
   ↓
8. PATIENT récupère l'ordonnance (QR code)
   ↓
9. PHARMACIE délivre les médicaments
   ↓
10. Système marque le ticket comme COMPLETED
```

## 🎨 États du Health Ticket

| État | Description | Transition |
|------|-------------|------------|
| `CREATED` | Ticket créé | → PENDING_PAYMENT |
| `PENDING_PAYMENT` | En attente de paiement | → PAID |
| `PAID` | Payé | → CHECKED_IN |
| `CHECKED_IN` | Patient enregistré | → IN_CONSULTATION |
| `IN_CONSULTATION` | Consultation en cours | → CONSULTATION_COMPLETED |
| `CONSULTATION_COMPLETED` | Consultation terminée | → PRESCRIPTION_ISSUED / COMPLETED |
| `PRESCRIPTION_ISSUED` | Ordonnance émise | → COMPLETED |
| `COMPLETED` | Terminé | - |
| `CANCELLED` | Annulé | - |
| `REFUNDED` | Remboursé | - |

## 🔐 Permissions

### Patient
- ✅ Créer des tickets
- ✅ Voir ses propres tickets
- ✅ Voir ses dossiers médicaux
- ✅ Voir ses ordonnances
- ✅ Annuler ses tickets (si non commencé)

### Prestataire (Healthcare Provider)
- ✅ Voir tous les tickets de son établissement
- ✅ Check-in des patients
- ✅ Statistiques de l'établissement

### Médecin (Doctor)
- ✅ Voir les tickets assignés
- ✅ Démarrer/terminer les consultations
- ✅ Créer des dossiers médicaux
- ✅ Émettre des ordonnances

### Pharmacie (Pharmacy)
- ✅ Voir les ordonnances
- ✅ Délivrer les médicaments

### Admin
- ✅ Tout voir et gérer
- ✅ Vérifier les prestataires
- ✅ Statistiques globales

## 🧪 Tests

```bash
# Tester l'API Healthcare
python manage.py test apps.healthcare

# Avec pytest
pytest apps/healthcare/tests/ -v

# Avec couverture
pytest apps/healthcare/tests/ --cov=apps.healthcare --cov-report=html
```

## 📊 Modèles

- **HealthcareProvider** : 25+ champs
- **HealthTicket** : 35+ champs
- **MedicalRecord** : 20+ champs
- **Prescription** : 15+ champs
- **PrescriptionMedication** : 6 champs

Total : **5 modèles, 100+ champs**

## 🎯 Fonctionnalités avancées

### QR Codes
- ✅ Génération automatique pour tickets et ordonnances
- ✅ Contient toutes les infos essentielles
- ✅ Vérification rapide à l'accueil/pharmacie

### CMU Integration
- ✅ Prestataires conventionnés
- ✅ Calcul automatique de la couverture
- ✅ Paiement patient = total - couverture CMU

### Géolocalisation
- ✅ Coordonnées GPS des prestataires
- ✅ Calcul de distance (à implémenter)
- ✅ Recherche par proximité (à implémenter)

### Statistiques
- ✅ Nombre de consultations
- ✅ Revenu total
- ✅ Consultations du jour
- ✅ Taux d'annulation

## 🚀 Prochaines étapes

- [ ] Intégration calendrier pour disponibilités
- [ ] Système de rappels SMS/Email
- [ ] Notation et avis patients
- [ ] Téléconsultation (vidéo)
- [ ] Export PDF des ordonnances
- [ ] Signature électronique médecin
- [ ] Intégration pharmacies partenaires
- [ ] Analytics avancés

## 📚 Documentation

- API complète : `/api/docs/`
- Schéma OpenAPI : `/api/schema/`
- ReDoc : `/api/redoc/`

---

**Version** : 1.0.0  
**Status** : ✅ Opérationnel  
**Dernière mise à jour** : 13 Novembre 2025


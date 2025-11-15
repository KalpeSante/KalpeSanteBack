# apps/users/utils.py
import re
from django.core.exceptions import ValidationError

def valider_numero_telephone_senegal(phone):
    """Valide un numéro de téléphone sénégalais"""
    pattern = r'^(?:\+221|221|00221)?[76][0-9]{8}$'
    phone_clean = re.sub(r'[\s\-\.]', '', str(phone))
    
    if not re.match(pattern, phone_clean):
        raise ValidationError('Numéro de téléphone sénégalais invalide')
    
    return phone_clean

def generer_code_verification():
    """Génère un code de vérification à 6 chiffres"""
    import random
    return str(random.randint(100000, 999999))
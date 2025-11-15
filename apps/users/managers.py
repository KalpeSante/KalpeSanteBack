from django.contrib.auth.models import BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, phone, email, user_type, password=None, **extra_fields):
        if not phone:
            raise ValueError('Le numéro de téléphone est obligatoire')
        if not email:
            raise ValueError('L\'email est obligatoire')
        if not user_type:
            raise ValueError('Le type d\'utilisateur est obligatoire')

        email = self.normalize_email(email)
        # Génère un username automatique si non fourni
        extra_fields.setdefault('username', phone)

        user = self.model(
            phone=phone,
            email=email,
            user_type=user_type,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, email, user_type='admin_systeme', password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Le superuser doit avoir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Le superuser doit avoir is_superuser=True.')

        # Même logique : ajoute username automatique
        extra_fields.setdefault('username', phone)

        return self.create_user(phone, email, user_type, password, **extra_fields)

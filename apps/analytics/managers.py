# apps/core/managers.py
from django.db import models

class BaseManager(models.Manager):
    def actifs(self):
        return self.filter(is_active=True)
    
    def inactifs(self):
        return self.filter(is_active=False)

class AdresseManager(models.Manager):
    def par_region(self, region):
        return self.filter(region=region)
    
    def par_ville(self, ville):
        return self.filter(ville=ville)
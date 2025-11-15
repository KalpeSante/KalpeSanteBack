"""
Management command to initialize the Site object for django.contrib.sites
"""
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site


class Command(BaseCommand):
    help = 'Initialize the default Site object'

    def handle(self, *args, **options):
        """Initialize or update the default Site"""
        site, created = Site.objects.get_or_create(
            id=1,
            defaults={
                'domain': 'kalpe-sante.sn',
                'name': 'KALPÉ SANTÉ'
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Site created: {site.name} ({site.domain})')
            )
        else:
            # Update existing site
            site.domain = 'kalpe-sante.sn'
            site.name = 'KALPÉ SANTÉ'
            site.save()
            self.stdout.write(
                self.style.SUCCESS(f'✅ Site updated: {site.name} ({site.domain})')
            )




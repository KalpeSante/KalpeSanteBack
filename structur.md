# Ta structure devrait ressembler à :
Get-ChildItem -Recurse

# Output attendu :
# config/
# apps/
# ├── core/
# ├── users/
# ├── wallet/
# ├── healthcare/
# ├── pharmacy/
# ├── payments/
# ├── analytics/
# ├── notifications/
# ├── api/
# manage.py
# requirements.txt
# venv/


 apps/<module>/
├── __init__.py
├── apps.py                   # nom clair pour Django
├── models.py                 # modèles du domaine
├── serializers.py            # DRF
├── views.py                  # viewsets ou APIView
├── urls.py                   # routes
├── admin.py                  # Admin Django
├── signals.py                # récepteurs
├── tasks.py                  # Celery
├── managers.py               # QuerySet perf
├── tests/                    # pytest
├── migrations/
└── utils.py                  # helpers locaux
from django.apps import AppConfig


class HisseTakipConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hisse_takip'

    def ready(self):
        import hisse_takip.signals  # Sinyalleri yükle

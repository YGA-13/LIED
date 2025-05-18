from django.apps import AppConfig

class RepertoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'repertorio'  # Nombre de tu aplicación

    def ready(self):
        # Importar y conectar las señales
        import repertorio.signals
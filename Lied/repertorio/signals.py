# signals.py
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import PiezaMusical
import os

@receiver(post_delete, sender=PiezaMusical)
def eliminar_archivos_asociados(sender, instance, **kwargs):
    """
    Elimina los archivos asociados cuando se elimina una instancia de PiezaMusical.
    """
    if instance.partitura_musicxml:  # Reemplaza con el nombre de tu campo FileField
        if os.path.isfile(instance.partitura_musicxml.path):
            os.remove(instance.partitura_musicxml.path)
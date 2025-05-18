from django.db import models
from django.contrib.auth.models import User

class PiezaMusical(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=255, default='Título no disponible')
    compositor = models.CharField(max_length=100, default='Compositor desconocido')
    fecha_composicion = models.CharField(max_length=50, blank=True, null=True)
    derechos = models.CharField(max_length=100, default='Dominio público', null=True, blank=True)
    partitura_musicxml = models.FileField(upload_to='partituras/musicxml/')
    analisis_data = models.JSONField(default=dict, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.titulo} - {self.compositor}"

class Ejercicio(models.Model):
    partitura = models.ForeignKey(
        PiezaMusical,
        on_delete=models.CASCADE,
        related_name='ejercicios'
    )
    parametros = models.JSONField(default=dict)
    archivo_musicxml = models.FileField(upload_to='ejercicios/musicxml/')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['partitura', 'creado_en']),
        ]

    def __str__(self):
        return f"Ejercicio {self.id} - {self.partitura.titulo}"
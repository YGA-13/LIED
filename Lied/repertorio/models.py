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
    TIPO_CHOICES = [
        ('escalas', 'Escalas Tonales'),
        ('saltos', 'Técnica de Saltos'),
        ('ritmos', 'Coordinación Rítmica'),
        ('acordes', 'Progresiones Armónicas')
    ]
    
    partitura = models.ForeignKey(
        PiezaMusical,
        on_delete=models.CASCADE,
        related_name='ejercicios'
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    parametros = models.JSONField(default=dict)
    archivo_musicxml = models.FileField(upload_to='ejercicios/musicxml/')
    creado_en = models.DateTimeField(auto_now_add=True)
    contenido = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-creado_en']
        verbose_name = 'Ejercicio'
        verbose_name_plural = 'Ejercicios'

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.partitura.titulo}"

# NUEVO MODELO AÑADIDO (sin modificar lo existente)
class NotaTecnica(models.Model):
    TIPO_NOTA = [
        ('OBSERVACION', 'Observación técnica'),
        ('RECORDATORIO', 'Recordatorio'),
        ('ANALISIS', 'Análisis musical'),
        ('EJERCICIO', 'Ejercicio relacionado')
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    contenido = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPO_NOTA)
    
    # Relaciones opcionales con tus modelos existentes:
    pieza_relacionada = models.ForeignKey(
        PiezaMusical, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='notas_tecnicas'
    )
    ejercicio_relacionado = models.ForeignKey(
        Ejercicio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notas_tecnicas'
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_actualizacion']
        verbose_name = 'Nota Técnica'
        verbose_name_plural = 'Notas Técnicas'

    def __str__(self):
        relacion = ""
        if self.pieza_relacionada:
            relacion = f" (Pieza: {self.pieza_relacionada.titulo})"
        elif self.ejercicio_relacionado:
            relacion = f" (Ejercicio: {self.ejercicio_relacionado})"
        return f"{self.get_tipo_display()}{relacion}"
    

class DominioPieza(models.Model):
    NIVEL_CHOICES = [
        ('PR', 'Principiante'),
        ('IN', 'Intermedio'),
        ('AV', 'Avanzado'),
        ('PR', 'Profesional'),
    ]
    
    pieza = models.OneToOneField(
        PiezaMusical,
        on_delete=models.CASCADE,
        related_name='dominio'
    )
    nivel = models.CharField(max_length=2, choices=NIVEL_CHOICES, default='PR')
    ultima_practica = models.DateField(null=True, blank=True)
    grabacion_original = models.FileField(upload_to='grabaciones/originales/', null=True, blank=True)
    grabacion_ejecucion = models.FileField(upload_to='grabaciones/ejecuciones/', null=True, blank=True)
    progreso = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Dominio de Pieza'
        verbose_name_plural = 'Dominios de Piezas'

    def __str__(self):
        return f"{self.pieza.titulo} - {self.get_nivel_display()} ({self.progreso}%)"
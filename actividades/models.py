# models.py
from django.db import models
from django.contrib.auth.models import User


class Actividad(models.Model):
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="actividades"
    )
        
    titulo = models.CharField(max_length=200)
    curso = models.CharField(max_length=200, blank=True, null=True)
    tipo = models.CharField(max_length=200, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha", "hora_inicio"]


    def __str__(self):
        return self.titulo


class Subtarea(models.Model):
    actividad = models.ForeignKey(
        Actividad,
        on_delete=models.CASCADE,
        related_name="subtareas"
    )
    titulo = models.CharField(max_length=200)
    fecha_objetivo = models.DateField()
    horas = models.FloatField()
    completada = models.BooleanField(default=False)

    class Meta:
        ordering = ["fecha_objetivo"]

    def __str__(self):
        return self.titulo

class AvanceSubtarea(models.Model):
    ESTADOS = [
        ("hecho", "Hecho"),
        ("pospuesto", "Pospuesto"),
        ("deshacer", "Deshacer"),
    ]

    subtarea = models.ForeignKey("Subtarea", on_delete=models.CASCADE, related_name="avances")
    estado = models.CharField(max_length=20, choices=ESTADOS)
    nota = models.TextField(blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subtarea.titulo} - {self.estado}"
    
class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    limite_diario = models.IntegerField(default=6)

    def __str__(self):
        return f"Perfil de {self.user.username}"
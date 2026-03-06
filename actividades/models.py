# models.py
"""
from django.db import models

class Actividad(models.Model):
    titulo = models.CharField(max_length=200)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo
"""
from django.db import models

class Actividad(models.Model):
    titulo = models.CharField(max_length=200)
    curso = models.CharField(max_length=200)
    descripcion = models.CharField(max_length=200)
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo


class Subtarea(models.Model):
    actividad = models.ForeignKey(
        Actividad,
        on_delete=models.CASCADE,
        related_name="subtareas"
    )
    titulo = models.CharField(max_length=200)
    fecha = models.DateField()
    horas = models.IntegerField()

    def __str__(self):
        return self.titulo
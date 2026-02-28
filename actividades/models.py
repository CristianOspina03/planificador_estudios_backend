# models.py

from django.db import models

class Actividad(models.Model):
    titulo = models.CharField(max_length=200)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo
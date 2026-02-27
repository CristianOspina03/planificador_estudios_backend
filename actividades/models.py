from django.db import models

class Actividad(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    fecha_entrega = models.DateField()
    horas_estimadas = models.IntegerField()

    def __str__(self):
        return self.titulo



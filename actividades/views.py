from rest_framework import viewsets
from .models import Actividad
from .serializers import ActividadSerializer

class ActividadViewSet(viewsets.ModelViewSet):
    queryset = Actividad.objects.all()
    serializer_class = ActividadSerializer




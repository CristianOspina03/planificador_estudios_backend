# views.py

from rest_framework.viewsets import ModelViewSet
from .models import Actividad
from .serializers import ActividadSerializer

class ActividadViewSet(ModelViewSet):
    queryset = Actividad.objects.all()
    serializer_class = ActividadSerializer
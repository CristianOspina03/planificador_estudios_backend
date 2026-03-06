# views.py

from rest_framework.viewsets import ModelViewSet
from .models import Actividad
from .serializers import ActividadSerializer
from rest_framework.permissions import IsAuthenticated


class ActividadViewSet(ModelViewSet):

    queryset = Actividad.objects.all()
    serializer_class = ActividadSerializer
    permission_classes = [IsAuthenticated]
# views.py

from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from .models import Actividad
from .serializers import ActividadSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import date
from django.db.models import Sum, F, ExpressionWrapper, DurationField
from datetime import datetime

class ActividadViewSet(ModelViewSet):

    serializer_class = ActividadSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

    def get_queryset(self):
        return (
            Actividad.objects
            .filter(usuario=self.request.user)
            .prefetch_related("subtareas")
            .order_by("fecha", "hora_inicio")
        )

    @action(detail=False, methods=["get"])
    def dashboard_hoy(self, request):

        hoy = date.today()

        actividades = self.get_queryset()

        vencidas = actividades.filter(fecha__lt=hoy).order_by("fecha", "hora_inicio")
        para_hoy = actividades.filter(fecha=hoy).order_by("hora_inicio")
        proximas = actividades.filter(fecha__gt=hoy).order_by("fecha", "hora_inicio")

        def serialize(qs):
            return ActividadSerializer(qs, many=True).data
        horas_hoy = 0
        for a in para_hoy:
            inicio = datetime.combine(a.fecha, a.hora_inicio)
            fin = datetime.combine(a.fecha, a.hora_fin)
            horas_hoy += (fin - inicio).total_seconds() / 3600

        return Response({
            "resumen_hoy": {
                "horas_planificadas": horas_hoy,
                "total_actividades": para_hoy.count()
            },
            "vencidas": serialize(vencidas),
            "hoy": serialize(para_hoy),
            "proximas": serialize(proximas),
        })
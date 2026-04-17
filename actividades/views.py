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
from rest_framework.decorators import action


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
    @action(detail=True, methods=["patch"])
    def completar_subtarea(self, request, pk=None):
        subtarea_id = request.data.get("subtarea_id")

        from .models import Subtarea

        try:
            sub = Subtarea.objects.get(id=subtarea_id, actividad__usuario=request.user)
            sub.completada = True
            sub.save()
            return Response({"mensaje": "Subtarea completada"})
        except Subtarea.DoesNotExist:
            return Response({"error": "Subtarea no encontrada"}, status=404)
    
    @action(detail=True, methods=["get"])
    def progreso(self, request, pk=None):
        actividad = self.get_object()

        total = actividad.subtareas.count()
        completas = actividad.subtareas.filter(completada=True).count()

        porcentaje = 0
        if total > 0:
            porcentaje = (completas / total) * 100

        return Response({
            "total_subtareas": total,
            "completadas": completas,
            "progreso": porcentaje
        })
    from datetime import timedelta

    @action(detail=True, methods=["patch"])
    def posponer(self, request, pk=None):
        actividad = self.get_object()
        actividad.fecha = actividad.fecha + timedelta(days=1)
        actividad.save()
        return Response({"mensaje": "Actividad pospuesta para el día siguiente"})
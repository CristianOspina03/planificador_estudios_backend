from datetime import date, datetime, timedelta

from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import date

from .models import Actividad, Subtarea
from .serializers import ActividadSerializer, SubtareaSerializer


class ActividadViewSet(ModelViewSet):

    serializer_class = ActividadSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

    def get_queryset(self):
        queryset = (
            Actividad.objects
            .filter(usuario=self.request.user)
            .prefetch_related("subtareas")
            .order_by("fecha", "hora_inicio")
        )

        # 🔍 QUERY PARAMS DEL FRONT
        fecha = self.request.query_params.get("fecha")
        buscar = self.request.query_params.get("buscar")
        estado = self.request.query_params.get("estado")

        # 📅 Filtro por fecha exacta
        if fecha:
            queryset = queryset.filter(fecha=fecha)

        # 🔎 Buscador por título o curso
        if buscar:
            queryset = queryset.filter(
                titulo__icontains=buscar
            ) | queryset.filter(
                curso__icontains=buscar
            )

        # 🚦 Filtro por estado temporal
        hoy = date.today()

        if estado == "proximas":
            queryset = queryset.filter(fecha__gte=hoy)

        elif estado == "vencidas":
            queryset = queryset.filter(fecha__lt=hoy)

        return queryset

    # 🧭 Vista ejecutiva (macro por actividades)
    @action(detail=False, methods=["get"])
    def resumen_hoy(self, request):

        hoy = date.today()
        actividades = self.get_queryset()

        vencidas = actividades.filter(fecha__lt=hoy)
        para_hoy = actividades.filter(fecha=hoy)
        proximas = actividades.filter(fecha__gt=hoy)

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
            "vencidas": ActividadSerializer(vencidas, many=True).data,
            "hoy": ActividadSerializer(para_hoy, many=True).data,
            "proximas": ActividadSerializer(proximas, many=True).data,
        })

    # ✅ US-04 y US-05 — Vista REAL /hoy basada en SUBTAREAS
    @action(detail=False, methods=["get"])
    def hoy(self, request):

        hoy = date.today()
        curso = request.query_params.get("curso")

        subtareas = Subtarea.objects.filter(
            actividad__usuario=request.user,
            completada=False
        )

        # Filtro por curso (US-05)
        if curso:
            subtareas = subtareas.filter(actividad__curso=curso)

        vencidas = subtareas.filter(
            fecha_objetivo__lt=hoy
        ).order_by("fecha_objetivo", "horas")

        para_hoy = subtareas.filter(
            fecha_objetivo=hoy
        ).order_by("horas")

        proximas = subtareas.filter(
            fecha_objetivo__gt=hoy
        ).order_by("fecha_objetivo", "horas")

        return Response({
            "regla": "Vencidas por fecha más antigua, luego Hoy, luego Próximas por fecha más cercana. Empate por menor esfuerzo.",
            "vencidas": SubtareaSerializer(vencidas, many=True).data,
            "hoy": SubtareaSerializer(para_hoy, many=True).data,
            "proximas": SubtareaSerializer(proximas, many=True).data,
        })

    # ✅ Completar subtarea
    @action(detail=True, methods=["patch"])
    def completar_subtarea(self, request, pk=None):

        subtarea_id = request.data.get("subtarea_id")

        try:
            sub = Subtarea.objects.get(
                id=subtarea_id,
                actividad__usuario=request.user
            )
            sub.completada = True
            sub.save()
            return Response({"mensaje": "Subtarea completada"})
        except Subtarea.DoesNotExist:
            return Response({"error": "Subtarea no encontrada"}, status=404)

    # ✅ Progreso de actividad
    @action(detail=True, methods=["get"])
    def progreso(self, request, pk=None):

        actividad = self.get_object()

        total = actividad.subtareas.count()
        completas = actividad.subtareas.filter(completada=True).count()

        porcentaje = (completas / total) * 100 if total > 0 else 0

        return Response({
            "total_subtareas": total,
            "completadas": completas,
            "progreso": porcentaje
        })

    # ✅ Posponer actividad
    @action(detail=True, methods=["patch"])
    def posponer(self, request, pk=None):

        actividad = self.get_object()
        actividad.fecha = actividad.fecha + timedelta(days=1)
        actividad.save()

        return Response({
            "mensaje": "Actividad pospuesta para el día siguiente"
        })

class SubtareaViewSet(ModelViewSet):
    serializer_class = SubtareaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Subtarea.objects.filter(
            actividad__usuario=self.request.user
        ).order_by("fecha_objetivo", "horas")

    def perform_create(self, serializer):
        serializer.save()
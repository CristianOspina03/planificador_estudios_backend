from datetime import date, datetime, timedelta

from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import date

from .models import Actividad, Subtarea
from .serializers import ActividadSerializer, SubtareaSerializer
from django.db.models import Q
from django.db.models import Sum


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

        if curso:
            subtareas = subtareas.filter(
                Q(actividad__curso__icontains=curso) |
                Q(titulo__icontains=curso)
            )

        vencidas = subtareas.filter(
            fecha_objetivo__lt=hoy
        ).order_by("fecha_objetivo", "horas")

        para_hoy = subtareas.filter(
            fecha_objetivo=hoy
        ).order_by("horas")

        proximas = subtareas.filter(
            fecha_objetivo__gt=hoy
        ).order_by("fecha_objetivo", "horas")

        # 🔥 NUEVO: cálculo de horas
        horas_hoy = para_hoy.aggregate(
            total=Sum("horas")
        )["total"] or 0

        limite = getattr(request.user, "limite_horas", 6)

        sobrecarga = horas_hoy > limite

        return Response({
            "resumen": {
                "horas_hoy": horas_hoy,
                "limite": limite,
                "sobrecarga": sobrecarga
            },
            "regla": "Vencidas → Hoy → Próximas. Orden por fecha y menor esfuerzo.",
            "vencidas": SubtareaSerializer(vencidas, many=True).data,
            "hoy": SubtareaSerializer(para_hoy, many=True).data,
            "proximas": SubtareaSerializer(proximas, many=True).data,
        })

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

    @action(detail=True, methods=["patch"])
    def reprogramar(self, request, pk=None):
        actividad = self.get_object()
        nueva_fecha = request.data.get("fecha")
        modo = request.data.get("modo", "actividad")  
        # "actividad" | "subtareas"

        limite = getattr(request.user, "limite_horas", 6)

        # 🔹 SOLO MOVER ACTIVIDAD (sin tocar subtareas)
        if modo == "actividad":
            actividad.fecha = nueva_fecha
            actividad.save()

            return Response({
                "ok": True,
                "modo": "actividad",
                "mensaje": "Fecha de actividad actualizada",
                "actividad": self.get_serializer(actividad).data
            })

        # 🔹 MOVER SUBTAREAS (inteligente)
        subtareas = actividad.subtareas.filter(completada=False)

        horas_subtareas = subtareas.aggregate(
            total=Sum("horas")
        )["total"] or 0

        horas_dia_destino = Subtarea.objects.filter(
            actividad__usuario=request.user,
            fecha_objetivo=nueva_fecha,
            completada=False
        ).aggregate(total=Sum("horas"))["total"] or 0

        conflicto = (horas_dia_destino + horas_subtareas) > limite

        if conflicto:
            return Response({
                "conflicto": True,
                "mensaje": "Sobrecarga detectada",
                "horas_actuales_dia": horas_dia_destino,
                "horas_a_mover": horas_subtareas,
                "limite": limite,
                "exceso": (horas_dia_destino + horas_subtareas) - limite,

                # 🔥 OPCIONES (UX CLAVE)
                "opciones": [
                    "Mover solo parte de las subtareas",
                    "Mover al siguiente día disponible",
                    "Reducir carga de horas"
                ]
            })

        # ✅ SIN CONFLICTO → mover todo
        subtareas.update(fecha_objetivo=nueva_fecha)

        actividad.fecha = nueva_fecha
        actividad.save()

        return Response({
            "ok": True,
            "modo": "subtareas",
            "mensaje": "Subtareas reprogramadas correctamente"
        })

    @action(detail=True, methods=["patch"])
    def auto_reprogramar(self, request, pk=None):
        actividad = self.get_object()

        limite = getattr(request.user, "limite_horas", 6)

        fecha = date.today()

        while True:
            horas = Subtarea.objects.filter(
                actividad__usuario=request.user,
                fecha_objetivo=fecha,
                completada=False
            ).aggregate(total=Sum("horas"))["total"] or 0

            if horas < limite:
                break

            fecha += timedelta(days=1)

        actividad.subtareas.filter(completada=False).update(
            fecha_objetivo=fecha
        )

        actividad.fecha = fecha
        actividad.save()

        return Response({
            "ok": True,
            "nueva_fecha": fecha
        })
from datetime import date, datetime, timedelta

from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import date

from .models import Actividad, Subtarea, Perfil
from .serializers import ActividadSerializer, SubtareaSerializer, PerfilSerializer
from django.db.models import Q
from django.db.models import Sum

from rest_framework.views import APIView

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
                Q(titulo__icontains=buscar) |
                Q(curso__icontains=buscar) |
                Q(tipo__icontains=buscar)  
            )


        # 🚦 Filtro por estado temporal
        hoy = date.today()

        if estado == "proximas":
            queryset = queryset.filter(fecha__gte=hoy)

        elif estado == "vencidas":
            queryset = queryset.filter(fecha__lt=hoy)

        return queryset

    # ✅ US-04 y US-05 — Vista REAL /hoy basada en SUBTAREAS
    @action(detail=False, methods=["get"])
    def hoy(self, request):

        hoy = date.today()
        buscar = request.query_params.get("buscar")

        subtareas = Subtarea.objects.select_related("actividad").filter(
            actividad__usuario=request.user,
            completada=False
        )

        if buscar:
            subtareas = subtareas.filter(
                Q(actividad__curso__icontains=buscar) |
                Q(actividad__titulo__icontains=buscar) |
                Q(actividad__tipo__icontains=buscar) |
                Q(titulo__icontains=buscar)
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

        limite = Perfil.objects.get(user=request.user).limite_diario

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

        limite = Perfil.objects.get(user=request.user).limite_diario

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

        limite = Perfil.objects.get(user=request.user).limite_diario

        fecha = date.today()
        dias_revisados = []

        horas_actividad = actividad.subtareas.filter(
            completada=False
        ).aggregate(total=Sum("horas"))["total"] or 0

        while True:
            horas_dia = Subtarea.objects.filter(
                actividad__usuario=request.user,
                fecha_objetivo=fecha,
                completada=False
            ).aggregate(total=Sum("horas"))["total"] or 0

            dias_revisados.append({
                "fecha": fecha,
                "horas_en_dia": horas_dia
            })

            if (horas_dia + horas_actividad) <= limite:
                break

            fecha += timedelta(days=1)

        actividad.subtareas.filter(completada=False).update(
            fecha_objetivo=fecha
        )

        actividad.fecha = fecha
        actividad.save()

        return Response({
            "ok": True,
            "nueva_fecha": fecha,
            "horas_actividad": horas_actividad,
            "limite": limite,
            "analisis": dias_revisados,
            "mensaje": "Se movió al primer día que no supera el límite diario"
        })
    # 📅 Eventos para calendario
    @action(detail=False, methods=["get"])
    def calendario(self, request):

        actividades = Actividad.objects.filter(
            usuario=request.user
        ).prefetch_related("subtareas")

        eventos = []

        for act in actividades:
            # Evento principal de la actividad
            eventos.append({
                "id": f"A{act.id}",
                "title": f"{act.titulo} ({act.curso})",
                "date": act.fecha,
            })

            # Eventos de subtareas
            for sub in act.subtareas.all():
                eventos.append({
                    "id": f"S{sub.id}",
                    "title": f"↳ {sub.titulo} • {sub.horas}h",
                    "date": sub.fecha_objetivo,
                })

        return Response(eventos)
    
class SubtareaViewSet(ModelViewSet):
    queryset = Subtarea.objects.all()
    serializer_class = SubtareaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Subtarea.objects.filter(
            actividad__usuario=self.request.user
        )
    
class LimiteDiarioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        perfil = Perfil.objects.get(user=request.user)
        serializer = PerfilSerializer(perfil)
        return Response(serializer.data)

    def patch(self, request):
        perfil = Perfil.objects.get(user=request.user)
        serializer = PerfilSerializer(
            perfil, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
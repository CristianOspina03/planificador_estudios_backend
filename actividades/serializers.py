# serializers.py
from rest_framework import serializers
from .models import Actividad, Subtarea, Perfil
from datetime import datetime
from .models import AvanceSubtarea
from .planificador import analizar_sobrecarga
from django.db.models import Sum

class AvanceSubtareaSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvanceSubtarea
        fields = "__all__"
        
class SubtareaSerializer(serializers.ModelSerializer):
    actividad_id = serializers.IntegerField(source="actividad.id", read_only=True)
    actividad_titulo = serializers.CharField(source="actividad.titulo", read_only=True)
    curso = serializers.CharField(source="actividad.curso", read_only=True)
    tipo = serializers.CharField(source="actividad.tipo", read_only=True)
    fecha_actividad = serializers.DateField(source="actividad.fecha", read_only=True)

    class Meta:
        model = Subtarea
        fields = "__all__"

    def validate(self, data):
        request = self.context.get("request")
        user = request.user

        fecha = data.get("fecha_objetivo")
        horas = data.get("horas")

        if fecha and horas:
            resultado = analizar_sobrecarga(
                user=user,
                fecha=fecha,
                horas_nuevas=horas,
                excluir_subtarea_id=self.instance.id if self.instance else None
            )

            if resultado["sobrecarga"]:
                raise serializers.ValidationError(resultado)

        return data
class SubtareaNestedSerializer(serializers.ModelSerializer):

    avances = AvanceSubtareaSerializer(many=True, read_only=True)

    class Meta:
        model = Subtarea
        exclude = ["actividad"]
    def validate(self, data):
        if "titulo" in data and not data.get("titulo"):
            raise serializers.ValidationError(
                "El nombre de la subtarea es obligatorio."
            )

        if "horas" in data and data.get("horas", 0) <= 0:
            raise serializers.ValidationError(
                "Las horas de una subtarea deben ser mayores a 0."
            )

        if "fecha_objetivo" in data and not data.get("fecha_objetivo"):
            raise serializers.ValidationError(
                "La fecha objetivo es obligatoria."
            )

        return data

class ActividadSerializer(serializers.ModelSerializer):

    subtareas = SubtareaNestedSerializer(many=True, required=False)

    class Meta:
        model = Actividad
        fields = "__all__"
        extra_kwargs = {
            "usuario": {"read_only": True}
        }
    def validate(self, data):
        request = self.context.get("request")
        user = request.user

        hora_inicio = data.get("hora_inicio")
        hora_fin = data.get("hora_fin")

        if hora_inicio and hora_fin:
            if hora_fin <= hora_inicio:
                raise serializers.ValidationError(
                    "La hora_fin debe ser mayor que la hora_inicio."
                )

        # VALIDAR SUBTAREAS CON EL PLANIFICADOR
        subtareas = self.initial_data.get("subtareas", [])

        # VALIDAR SUBTAREAS CON ACUMULADO POR FECHA (CRÍTICO)
        acumulado_por_fecha = {}

        for sub in subtareas:
            fecha = sub.get("fecha_objetivo")
            horas = float(sub.get("horas", 0))

            if not fecha or not horas:
                continue

            acumulado_por_fecha.setdefault(fecha, 0)
            acumulado_por_fecha[fecha] += horas

        for fecha, horas_totales in acumulado_por_fecha.items():
            resultado = analizar_sobrecarga(
                user=user,
                fecha=fecha,
                horas_nuevas=horas_totales
            )

            if resultado["sobrecarga"]:
                raise serializers.ValidationError(resultado)

        return data

    def create(self, validated_data):
        subtareas_data = validated_data.pop("subtareas", [])
        actividad = Actividad.objects.create(**validated_data)

        for sub in subtareas_data:
            serializer = SubtareaSerializer(
                data={**sub, "actividad": actividad.id},
                context=self.context
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return actividad

    def update(self, instance, validated_data):
        subtareas_data = validated_data.pop("subtareas", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if subtareas_data is not None:
            instance.subtareas.all().delete()

            for sub in subtareas_data:
                serializer = SubtareaSerializer(
                    data={**sub, "actividad": instance.id},
                    context=self.context
                )
                serializer.is_valid(raise_exception=True)
                serializer.save()

        return instance

from rest_framework import serializers
from .models import Perfil

class PerfilSerializer(serializers.ModelSerializer):
    email = serializers.CharField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)

    class Meta:
        model = Perfil
        fields = [
            "limite_diario",
            "email",
            "first_name",
        ]

    def validate_limite_diario(self, value):
        if value < 1 or value > 16:
            raise serializers.ValidationError(
                "El límite debe estar entre 1 y 16 horas."
            )
        return value
    
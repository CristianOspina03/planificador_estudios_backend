# serializers.py
from rest_framework import serializers
from .models import Actividad, Subtarea, Perfil
from datetime import datetime
from .models import AvanceSubtarea
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
                limite = Perfil.objects.get(user=user).limite_diario

                queryset = Subtarea.objects.filter(
                    actividad__usuario=user,
                    fecha_objetivo=fecha,
                    completada=False
                )

                # 🔥 CLAVE: excluir la misma subtarea si estamos editando
                if self.instance:
                    queryset = queryset.exclude(id=self.instance.id)

                horas_actuales = queryset.aggregate(
                    total=Sum("horas")
                )["total"] or 0

                if (horas_actuales + horas) > limite:
                    raise serializers.ValidationError({
                        "sobrecarga": True,
                        "mensaje": "Se supera el límite diario",
                        "horas_actuales": horas_actuales,
                        "horas_nuevas": horas,
                        "limite": limite,
                        "exceso": (horas_actuales + horas) - limite
                    })

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
        hora_inicio = data.get("hora_inicio")
        hora_fin = data.get("hora_fin")

        if hora_inicio and hora_fin:
            if hora_fin <= hora_inicio:
                raise serializers.ValidationError(
                    "La hora_fin debe ser mayor que la hora_inicio."
                )
        return data

    def create(self, validated_data):
        subtareas_data = validated_data.pop("subtareas", [])
        actividad = Actividad.objects.create(**validated_data)

        for sub in subtareas_data:
            Subtarea.objects.create(actividad=actividad, **sub)

        return actividad

    def update(self, instance, validated_data):

        subtareas_data = validated_data.pop("subtareas", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if subtareas_data is not None:
            instance.subtareas.all().delete()

            for sub in subtareas_data:
                Subtarea.objects.create(actividad=instance, **sub)

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
    
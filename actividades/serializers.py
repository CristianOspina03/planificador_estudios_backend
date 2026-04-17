# serializers.py
from rest_framework import serializers
from .models import Actividad, Subtarea


class SubtareaSerializer(serializers.ModelSerializer):
    actividad_titulo = serializers.CharField(source="actividad.titulo", read_only=True)
    curso = serializers.CharField(source="actividad.curso", read_only=True)

    class Meta:
        model = Subtarea
        fields = "__all__"
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
class SubtareaNestedSerializer(serializers.ModelSerializer):

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
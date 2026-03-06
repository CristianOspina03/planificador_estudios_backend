# serializers.py
from rest_framework import serializers
from .models import Actividad, Subtarea


class SubtareaSerializer(serializers.ModelSerializer):

    class Meta:
        model = Subtarea
        fields = "__all__"
        extra_kwargs = {
            "actividad": {"read_only": True}
        }


class ActividadSerializer(serializers.ModelSerializer):

    subtareas = SubtareaSerializer(many=True, required=False)

    class Meta:
        model = Actividad
        fields = "__all__"
        extra_kwargs = {
            "usuario": {"read_only": True}
        }

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
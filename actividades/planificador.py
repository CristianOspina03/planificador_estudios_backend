# planificador.py
from django.db.models import Sum
from datetime import date, timedelta
from .models import Subtarea, Perfil, Actividad

def analizar_sobrecarga(user, fecha, horas_nuevas, excluir_subtarea_id=None):
    perfil = Perfil.objects.get(user=user)
    limite = perfil.limite_diario

    qs = Subtarea.objects.filter(
        actividad__usuario=user,
        fecha_objetivo=fecha,
        completada=False
    )

    if excluir_subtarea_id:
        qs = qs.exclude(id=excluir_subtarea_id)

    horas_actuales = qs.aggregate(total=Sum("horas"))["total"] or 0
    total = horas_actuales + horas_nuevas

    if total <= limite:
        return {"sobrecarga": False}

    exceso = total - limite

    recomendaciones = generar_recomendaciones(
        user, fecha, exceso, qs, limite
    )

    return {
        "sobrecarga": True,
        "exceso": exceso,
        "limite": limite,
        "horas_actuales": horas_actuales,
        "recomendaciones": recomendaciones
    }

def generar_recomendaciones(user):
    hoy = date.today()
    recomendaciones = []

    perfil = Perfil.objects.filter(user=user).first()
    limite = perfil.limite_diario if perfil else 6

    # 🔴 1. Subtareas vencidas
    vencidas = Subtarea.objects.filter(
        actividad__usuario=user,
        completada=False,
        fecha_objetivo__lt=hoy
    )

    if vencidas.exists():
        recomendaciones.append({
            "tipo": "urgente",
            "mensaje": f"Tienes {vencidas.count()} subtareas vencidas. Priorízalas hoy."
        })

    # 🟠 2. Sobrecarga hoy
    horas_hoy = Subtarea.objects.filter(
        actividad__usuario=user,
        completada=False,
        fecha_objetivo=hoy
    ).aggregate(total=Sum("horas"))["total"] or 0

    if horas_hoy > limite:
        recomendaciones.append({
            "tipo": "sobrecarga",
            "mensaje": "Hoy estás sobrecargado. Considera reprogramar o dividir actividades."
        })

    # 🟡 3. Actividades demasiado pesadas para un día
    actividades = Actividad.objects.filter(usuario=user)

    for act in actividades:
        horas = act.subtareas.filter(completada=False).aggregate(
            total=Sum("horas")
        )["total"] or 0

        if horas > limite:
            recomendaciones.append({
                "tipo": "actividad_pesada",
                "actividad_id": act.id,
                "mensaje": f"La actividad '{act.titulo}' supera tu límite diario. Divídela en más subtareas."
            })

    # 🟢 4. Días libres mañana
    manana = hoy + timedelta(days=1)

    horas_manana = Subtarea.objects.filter(
        actividad__usuario=user,
        completada=False,
        fecha_objetivo=manana
    ).aggregate(total=Sum("horas"))["total"] or 0

    if horas_manana < limite / 2:
        recomendaciones.append({
            "tipo": "espacio_libre",
            "mensaje": "Mañana tienes poco trabajo. Podrías adelantar una actividad."
        })

    return recomendaciones
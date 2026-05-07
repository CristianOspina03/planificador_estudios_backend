# planificador.py
from django.db.models import Sum
from datetime import date, timedelta, datetime
from .models import Subtarea, Perfil, Actividad
from collections import Counter


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _get_limite(user):
    perfil = Perfil.objects.filter(user=user).first()
    return perfil.limite_diario if perfil else 6


def _horas_en_fecha(user, fecha, excluir_id=None):
    qs = Subtarea.objects.filter(
        actividad__usuario=user,
        fecha_objetivo=fecha,
        completada=False
    )
    if excluir_id:
        qs = qs.exclude(id=excluir_id)
    return qs.aggregate(total=Sum("horas"))["total"] or 0


def _dias_preferidos(user):
    """Infiere qué días de la semana usa el usuario para estudiar (0=lun, 6=dom)."""
    fechas = Subtarea.objects.filter(
        actividad__usuario=user
    ).values_list("fecha_objetivo", flat=True)

    if not fechas:
        return set(range(5))  # lun-vie por defecto

    conteo = Counter(f.weekday() for f in fechas)
    # considera "activos" los días que aparecen al menos 20% del máximo
    max_count = max(conteo.values())
    return {dia for dia, cnt in conteo.items() if cnt >= max_count * 0.2}


def _buscar_dias_disponibles(user, horas_necesarias, desde, hasta_dias=14,
                              excluir_fecha=None, limite=None):
    """
    Retorna lista de dicts con fecha + horas_libres para los próximos `hasta_dias`.
    Respeta los días preferidos del usuario.
    """
    if limite is None:
        limite = _get_limite(user)

    dias_preferidos = _dias_preferidos(user)
    resultados = []
    fecha = desde

    for _ in range(hasta_dias):
        if excluir_fecha and fecha == excluir_fecha:
            fecha += timedelta(days=1)
            continue

        if fecha.weekday() not in dias_preferidos:
            fecha += timedelta(days=1)
            continue

        horas_ocupadas = _horas_en_fecha(user, fecha)
        horas_libres = limite - horas_ocupadas

        if horas_libres > 0:
            resultados.append({
                "fecha": fecha,
                "horas_libres": round(horas_libres, 1),
                "cabe_completa": horas_libres >= horas_necesarias
            })

        fecha += timedelta(days=1)

    return resultados


# ─────────────────────────────────────────────
# ANÁLISIS PRINCIPAL
# ─────────────────────────────────────────────

def analizar_sobrecarga(user, fecha, horas_nuevas, excluir_subtarea_id=None,
                        subtarea_nueva=None):
    if isinstance(fecha, str):
        fecha = datetime.strptime(fecha, "%Y-%m-%d").date()

    limite = _get_limite(user)
    horas_actuales = _horas_en_fecha(user, fecha, excluir_id=excluir_subtarea_id)
    total = horas_actuales + horas_nuevas

    if total <= limite:
        return {
            "sobrecarga": False,
            "limite": limite,
            "horas_actuales": horas_actuales,
            "exceso": 0,
            "recomendaciones": []
        }

    exceso = round(total - limite, 1)

    # subtareas existentes ese día (para recomendaciones)
    qs_dia = Subtarea.objects.filter(
        actividad__usuario=user,
        fecha_objetivo=fecha,
        completada=False
    )
    if excluir_subtarea_id:
        qs_dia = qs_dia.exclude(id=excluir_subtarea_id)

    recomendaciones = _generar_recomendaciones_sobrecarga(
        user=user,
        fecha_conflicto=fecha,
        horas_nuevas=horas_nuevas,
        horas_actuales=horas_actuales,
        exceso=exceso,
        subtareas_dia=qs_dia,
        limite=limite,
        subtarea_nueva=subtarea_nueva,
    )

    return {
        "sobrecarga": True,
        "exceso": exceso,
        "limite": limite,
        "horas_actuales": horas_actuales,
        "recomendaciones": recomendaciones
    }


# ─────────────────────────────────────────────
# RECOMENDACIONES DE SOBRECARGA
# ─────────────────────────────────────────────

def _generar_recomendaciones_sobrecarga(user, fecha_conflicto, horas_nuevas,
                                         horas_actuales, exceso, subtareas_dia,
                                         limite, subtarea_nueva=None):
    nombre = (subtarea_nueva or {}).get("titulo", "esta subtarea")
    recomendaciones = []
    dias_disponibles = _buscar_dias_disponibles(
        user, horas_nuevas,
        desde=fecha_conflicto + timedelta(days=1),
        excluir_fecha=fecha_conflicto,
        limite=limite
    )

    # ── 1. Mover completa al próximo día que quepa ─────────────────────
    dia_completo = next((d for d in dias_disponibles if d["cabe_completa"]), None)
    if dia_completo:
        f = dia_completo["fecha"]
        recomendaciones.append({
            "tipo": "mover_a_otro_dia",
            "fecha_sugerida": f,
            "horas_libres": dia_completo["horas_libres"],
            "razon": (
                f'Mueve "{nombre}" al {f.strftime("%A %d %b")} — '
                f'tiene {dia_completo["horas_libres"]}h libres'
            )
        })

    # ── 2. Dividir en dos días ─────────────────────────────────────────
    horas_disponibles_hoy = round(max(0.0, limite - horas_actuales), 1)

    if horas_disponibles_hoy > 0 and horas_nuevas > horas_disponibles_hoy:
        horas_restantes = round(horas_nuevas - horas_disponibles_hoy, 1)
        dia_resto = next(
            (d for d in dias_disponibles if d["horas_libres"] >= horas_restantes), None
        )
        if dia_resto:
            f2 = dia_resto["fecha"]
            recomendaciones.append({
                "tipo": "dividir_en_dos_dias",
                "parte_1": {"fecha": fecha_conflicto, "horas": horas_disponibles_hoy},
                "parte_2": {"fecha": f2, "horas": horas_restantes},
                "razon": (
                    f'Estudia {horas_disponibles_hoy}h hoy y '
                    f'{horas_restantes}h el {f2.strftime("%A %d %b")}'
                )
            })

    # ── 3. Reducir horas (solo si caben aunque sea algunas) ───────────
    if horas_disponibles_hoy > 0:
        recomendaciones.append({
            "tipo": "reducir_horas",
            "titulo": nombre,
            "horas_actuales": horas_nuevas,
            "sugerir_horas": horas_disponibles_hoy,
            "razon": f'Reduce "{nombre}" a {horas_disponibles_hoy}h para que quepa hoy'
        })

    # ── 4. Vista de la semana — los próximos 7 días con espacio ───────
    vista_semana = [
        {
            "fecha": d["fecha"],
            "horas_libres": d["horas_libres"],
            "cabe_completa": d["cabe_completa"]
        }
        for d in dias_disponibles[:7]
    ]
    if vista_semana:
        recomendaciones.append({
            "tipo": "vista_semana",
            "dias": vista_semana,
            "razon": "Estos son los próximos días con espacio disponible"
        })

    # ── 5. Aumentar límite — solo si es razonable y no hay mejor opción
    limite_sugerido = horas_actuales + horas_nuevas
    if limite_sugerido <= 10 and not dia_completo:
        recomendaciones.append({
            "tipo": "aumentar_limite",
            "sugerir_limite": int(limite_sugerido),
            "razon": f"Sube tu límite a {int(limite_sugerido)}h para permitir este día"
        })

    return recomendaciones


# ─────────────────────────────────────────────
# RECOMENDACIONES DEL DASHBOARD
# ─────────────────────────────────────────────

def generar_recomendaciones(user):
    hoy = date.today()
    limite = _get_limite(user)
    recomendaciones = []

    # 🔴 1. Subtareas vencidas — con detalle accionable
    vencidas = Subtarea.objects.filter(
        actividad__usuario=user,
        completada=False,
        fecha_objetivo__lt=hoy
    ).select_related("actividad").order_by("fecha_objetivo")

    if vencidas.exists():
        dias_disponibles = _buscar_dias_disponibles(
            user, horas_necesarias=0, desde=hoy, hasta_dias=7, limite=limite
        )
        mejor_dia = next((d for d in dias_disponibles if d["horas_libres"] > 0), None)

        recomendaciones.append({
            "tipo": "urgente",
            "cantidad": vencidas.count(),
            "subtareas": [
                {
                    "id": s.id,
                    "titulo": s.titulo,
                    "horas": s.horas,
                    "fecha_objetivo": s.fecha_objetivo,
                    "actividad": s.actividad.titulo
                }
                for s in vencidas[:5]  # máximo 5 en el resumen
            ],
            "dia_sugerido": mejor_dia["fecha"] if mejor_dia else None,
            "mensaje": (
                f"Tienes {vencidas.count()} subtarea(s) vencida(s). "
                + (f"Podrías trabajarlas el {mejor_dia['fecha'].strftime('%A %d %b')}." if mejor_dia else "Revisa tu agenda.")
            )
        })

    # 🟠 2. Sobrecarga hoy — con qué mover y a dónde
    horas_hoy = _horas_en_fecha(user, hoy)

    if horas_hoy > limite:
        exceso = round(horas_hoy - limite, 1)
        subtareas_hoy = Subtarea.objects.filter(
            actividad__usuario=user,
            completada=False,
            fecha_objetivo=hoy
        ).order_by("-horas")

        # Sugiere mover la subtarea más pesada
        candidata = subtareas_hoy.first()
        dias_disp = _buscar_dias_disponibles(
            user, candidata.horas if candidata else exceso,
            desde=hoy + timedelta(days=1), limite=limite
        )
        dia_sugerido = next((d for d in dias_disp if d["cabe_completa"]), None)

        recomendaciones.append({
            "tipo": "sobrecarga",
            "exceso": exceso,
            "candidata_mover": {
                "id": candidata.id,
                "titulo": candidata.titulo,
                "horas": candidata.horas,
                "fecha_sugerida": dia_sugerido["fecha"] if dia_sugerido else None
            } if candidata else None,
            "mensaje": (
                f"Hoy tienes {exceso}h de exceso. "
                + (
                    f'Considera mover "{candidata.titulo}" ({candidata.horas}h) '
                    f'al {dia_sugerido["fecha"].strftime("%A %d %b")}.'
                    if candidata and dia_sugerido else
                    "Considera reprogramar alguna subtarea."
                )
            )
        })

    # 🟡 3. Actividades pesadas — desglosadas por subtarea
    actividades = Actividad.objects.filter(usuario=user).prefetch_related("subtareas")
    for act in actividades:
        horas_total = act.subtareas.filter(completada=False).aggregate(
            total=Sum("horas")
        )["total"] or 0

        if horas_total > limite:
            recomendaciones.append({
                "tipo": "actividad_pesada",
                "actividad_id": act.id,
                "actividad_titulo": act.titulo,
                "horas_total": horas_total,
                "limite": limite,
                "mensaje": (
                    f'"{act.titulo}" tiene {horas_total}h en subtareas pendientes '
                    f"(tu límite es {limite}h/día). Divide en más subtareas."
                )
            })

    # 🟢 4. Espacio libre — próximos 3 días con hueco
    dias_libres = _buscar_dias_disponibles(
        user, horas_necesarias=0,
        desde=hoy + timedelta(days=1),
        hasta_dias=7,
        limite=limite
    )
    dias_con_espacio = [d for d in dias_libres if d["horas_libres"] >= limite * 0.5]

    if dias_con_espacio:
        recomendaciones.append({
            "tipo": "espacio_libre",
            "dias": [
                {"fecha": d["fecha"], "horas_libres": d["horas_libres"]}
                for d in dias_con_espacio[:3]
            ],
            "mensaje": (
                f'Tienes espacio libre en los próximos días. '
                f'El {dias_con_espacio[0]["fecha"].strftime("%A")} tiene '
                f'{dias_con_espacio[0]["horas_libres"]}h disponibles.'
            )
        })

    return recomendaciones
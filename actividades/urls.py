from django.urls import path, include
from .views import registrar_avance
from rest_framework.routers import DefaultRouter
from .views import ActividadViewSet, SubtareaViewSet, LimiteDiarioView

router = DefaultRouter()
router.register(r'actividades', ActividadViewSet, basename='actividades')
router.register(r'subtareas', SubtareaViewSet, basename='subtareas')

urlpatterns = [
    path('', include(router.urls)),
    path("perfil/limite", LimiteDiarioView.as_view()),
    path("subtareas/<int:id>/avance/", registrar_avance),
]
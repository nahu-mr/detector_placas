from django.urls import path
from .views import (
    listar_placas, 
    eliminar_placa,
    registrar_entrada, 
    registrar_salida,
    listar_movimientos
)

urlpatterns = [
    path("placas/", listar_placas, name="listar_placas"),
    path("placas/<str:placa>/", eliminar_placa, name="eliminar_placa"),
    path("entrada/", registrar_entrada, name="registrar_entrada"),
    path("salida/", registrar_salida, name="registrar_salida"),
    path("movimientos/", listar_movimientos, name="listar_movimientos"),
]
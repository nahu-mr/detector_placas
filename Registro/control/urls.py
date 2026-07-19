from django.urls import path
from .views import (
    listar_placas, 
    eliminar_placa,
    registrar_entrada, 
    registrar_salida,
    listar_movimientos
)
from .views_web import (
    dashboard, get_placas, get_movimientos, add_placa, delete_placa, update_placa,
    video_feed, iniciar_streaming, detener_streaming, notificaciones_stream, clear_movimientos
)

urlpatterns = [
    # API endpoints
    path("placas/", listar_placas, name="listar_placas"),
    path("placas/<str:placa>/", eliminar_placa, name="eliminar_placa"),
    path("entrada/", registrar_entrada, name="registrar_entrada"),
    path("salida/", registrar_salida, name="registrar_salida"),
    path("movimientos/", listar_movimientos, name="listar_movimientos"),
    
    # Web endpoints
    path("", dashboard, name="dashboard"),
    path("api/web/placas/", get_placas, name="api_placas"),
    path("api/web/movimientos/", get_movimientos, name="api_movimientos"),
    path("api/web/add-placa/", add_placa, name="add_placa"),
    path("api/web/delete-placa/<str:placa>/", delete_placa, name="delete_placa_web"),
    path("api/web/update-placa/<str:placa>/", update_placa, name="update_placa_web"),
    path("api/web/clear-movimientos/", clear_movimientos, name="clear_movimientos"),
    
    # Video streaming
    path("video/", video_feed, name="video_feed"),
    path("video/iniciar/", iniciar_streaming, name="iniciar_streaming"),
    path("video/detener/", detener_streaming, name="detener_streaming"),
    
    # Notificaciones en tiempo real
    path("api/notificaciones/", notificaciones_stream, name="notificaciones_stream"),
]

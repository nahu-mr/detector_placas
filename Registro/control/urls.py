from django.urls import path
from django.contrib.auth.decorators import login_required
from .views import (
    listar_placas, 
    eliminar_placa,
    registrar_entrada, 
    registrar_salida,
    listar_movimientos
)
from .views_web import (
    dashboard, get_placas, get_movimientos, add_placa, delete_placa, update_placa,
    video_feed, iniciar_streaming, detener_streaming, notificaciones_stream, clear_movimientos,
    exportar_reporte_movimientos
)

urlpatterns = [
    # API endpoints
    path("placas/", login_required(listar_placas), name="listar_placas"),
    path("placas/<str:placa>/", login_required(eliminar_placa), name="eliminar_placa"),
    path("entrada/", login_required(registrar_entrada), name="registrar_entrada"),
    path("salida/", login_required(registrar_salida), name="registrar_salida"),
    path("movimientos/", login_required(listar_movimientos), name="listar_movimientos"),
    
    # Web endpoints
    path("", login_required(dashboard), name="dashboard"),
    path("api/web/placas/", login_required(get_placas), name="api_placas"),
    path("api/web/movimientos/", login_required(get_movimientos), name="api_movimientos"),
    path("api/web/add-placa/", login_required(add_placa), name="add_placa"),
    path("api/web/delete-placa/<str:placa>/", login_required(delete_placa), name="delete_placa_web"),
    path("api/web/update-placa/<str:placa>/", login_required(update_placa), name="update_placa_web"),
    path("api/web/clear-movimientos/", login_required(clear_movimientos), name="clear_movimientos"),
    path("api/web/reportes/movimientos.xlsx/", login_required(exportar_reporte_movimientos), name="reporte_movimientos"),
    
    # Video streaming
    path("video/", login_required(video_feed), name="video_feed"),
    path("video/iniciar/", login_required(iniciar_streaming), name="iniciar_streaming"),
    path("video/detener/", login_required(detener_streaming), name="detener_streaming"),
    
    # Notificaciones en tiempo real
    path("api/notificaciones/", login_required(notificaciones_stream), name="notificaciones_stream"),
]

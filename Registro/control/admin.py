#admin.py
from django.contrib import admin
from .models import Registrada, Entrada


@admin.register(Registrada)
class RegistradaAdmin(admin.ModelAdmin):
    list_display = (
        'placa', 'modelo_auto', 'color_auto', 'nombre_propietario',
        'dni_propietario', 'activo'
    )
    search_fields = (
        'placa', 'modelo_auto', 'color_auto', 'nombre_propietario',
        'dni_propietario'
    )


admin.site.register(Entrada)

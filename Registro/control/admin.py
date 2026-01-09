#admin.py
from django.contrib import admin
from .models import Registrada, Entrada

admin.site.register(Registrada)
admin.site.register(Entrada)

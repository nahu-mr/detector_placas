from django.db import models

class Registrada(models.Model):
    placa = models.CharField(max_length=10, unique=True)
    propietario = models.CharField(max_length=100, default="Sin especificar")
    nombre_propietario = models.CharField(max_length=100, default="Sin especificar")
    dni_propietario = models.CharField(max_length=12, blank=True, default="")
    modelo_auto = models.CharField(max_length=80, blank=True, default="")
    color_auto = models.CharField(max_length=40, blank=True, default="")
    activo = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.nombre_propietario:
            self.nombre_propietario = self.propietario or "Sin especificar"
        self.propietario = self.nombre_propietario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.placa} - {self.nombre_propietario}"


class Entrada(models.Model):
    placa = models.CharField(max_length=10)
    entrada = models.DateTimeField()
    salida = models.DateTimeField(null=True, blank=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    procesada = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.placa} - {self.entrada.strftime('%d/%m/%Y %H:%M:%S')}"


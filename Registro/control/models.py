from django.db import models

class Registrada(models.Model):
    placa = models.CharField(max_length=10, unique=True)
    propietario = models.CharField(max_length=100, default="Sin especificar")
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.placa} - {self.propietario}"


class Entrada(models.Model):
    placa = models.CharField(max_length=10)
    entrada = models.DateTimeField(auto_now_add=True)
    salida = models.DateTimeField(null=True, blank=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    procesada = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.placa} - {self.entrada.strftime('%d/%m/%Y %H:%M:%S')}"

from django.test import TestCase

from .views import calcular_monto_estacionamiento


class CalculoMontoEstacionamientoTests(TestCase):
    def test_menos_de_10_minutos_no_cobra(self):
        self.assertEqual(calcular_monto_estacionamiento((10 * 60) - 1), 0.00)

    def test_desde_10_minutos_cobra_monto_base(self):
        self.assertEqual(calcular_monto_estacionamiento(10 * 60), 5.00)

    def test_despues_de_10_minutos_suma_tarifa_adicional_por_minuto(self):
        self.assertEqual(calcular_monto_estacionamiento(70 * 60), 7.50)

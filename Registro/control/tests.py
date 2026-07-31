from datetime import date, datetime
import json
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from django.utils import timezone

from .views import calcular_monto_estacionamiento
from .views_web import get_estadisticas_dashboard, get_movimientos
from .models import Entrada


class CalculoMontoEstacionamientoTests(TestCase):
    def test_menos_de_10_minutos_no_cobra(self):
        self.assertEqual(calcular_monto_estacionamiento((10 * 60) - 1), 0.00)

    def test_desde_10_minutos_cobra_monto_base(self):
        self.assertEqual(calcular_monto_estacionamiento(10 * 60), 5.00)

    def test_despues_de_10_minutos_suma_tarifa_adicional_por_minuto(self):
        self.assertEqual(calcular_monto_estacionamiento(70 * 60), 7.50)


class EstadisticasDashboardTests(TestCase):
    def test_vehiculos_dentro_cuenta_entradas_sin_salida(self):
        Entrada.objects.create(
            placa='XYZ789',
            entrada=timezone.now(),
            salida=None,
            procesada=False,
        )

        request = RequestFactory().get('/api/web/dashboard-estadisticas/')
        response = get_estadisticas_dashboard(request)

        datos = json.loads(response.content)
        self.assertEqual(datos['vehiculos_dentro'], 1)

    def test_ingresos_se_agregan_por_fecha_de_salida(self):
        zona_horaria = timezone.get_current_timezone()
        Entrada.objects.create(
            placa='ABC123',
            entrada=timezone.make_aware(datetime(2026, 7, 18, 23, 50), zona_horaria),
            salida=timezone.make_aware(datetime(2026, 7, 19, 0, 10), zona_horaria),
            monto='7.50',
            procesada=True,
        )

        request = RequestFactory().get('/api/web/dashboard-estadisticas/')
        with patch('control.views_web.timezone.localdate', return_value=date(2026, 7, 19)):
            response = get_estadisticas_dashboard(request)

        datos = json.loads(response.content)
        self.assertEqual(datos['ingresos_por_dia']['2026-07-18'], 0.0)
        self.assertEqual(datos['ingresos_por_dia']['2026-07-19'], 7.5)
        self.assertEqual(datos['ingresos_hoy'], 7.5)


class MovimientosDashboardTests(TestCase):
    def test_movimiento_sin_salida_se_marca_como_dentro(self):
        Entrada.objects.create(
            placa='XYZ789',
            entrada=timezone.now(),
            salida=None,
            procesada=False,
        )

        request = RequestFactory().get('/api/web/movimientos/')
        response = get_movimientos(request)

        datos = json.loads(response.content)
        self.assertTrue(datos[0]['dentro'])

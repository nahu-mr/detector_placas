from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.shortcuts import get_object_or_404
import json
from .models import Registrada, Entrada
from math import ceil

MINUTOS_GRATIS = 5
TARIFA_BASE = 5.00
TARIFA_MINUTO_ADICIONAL = 0.15


def calcular_monto_estacionamiento(segundos):
    """Calcula el cobro: menos de 5 min gratis; desde 5 min cobra base + adicional."""
    segundos = max(0, segundos)
    segundos_gratis = MINUTOS_GRATIS * 60
    if segundos < segundos_gratis:
        return 0.00

    minutos_adicionales = ceil((segundos - segundos_gratis) / 60)
    return round(TARIFA_BASE + (minutos_adicionales * TARIFA_MINUTO_ADICIONAL), 2)


@csrf_exempt
def listar_placas(request):
    """GET /api/placas/ - Lista todas las placas registradas"""
    if request.method == 'GET':
        placas = Registrada.objects.filter(activo=True).values(
            'id', 'placa', 'propietario', 'nombre_propietario',
            'dni_propietario', 'modelo_auto', 'color_auto'
        )
        return JsonResponse(list(placas), safe=False)
    
    """POST /api/placas/ - Registra una nueva placa"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            placa = data.get("placa", "").strip().upper()
            nombre_propietario = data.get("nombre_propietario", data.get("propietario", "Sin especificar")).strip() or "Sin especificar"
            dni_propietario = data.get("dni_propietario", "").strip()
            modelo_auto = data.get("modelo_auto", "").strip()
            color_auto = data.get("color_auto", "").strip()

            if not placa:
                return JsonResponse({"error": "Placa vacía"}, status=400)

            # Verificar si ya existe
            if Registrada.objects.filter(placa=placa).exists():
                return JsonResponse({"error": "La placa ya existe"}, status=400)

            # Crear nueva placa
            nueva_placa = Registrada.objects.create(
                placa=placa,
                propietario=nombre_propietario,
                nombre_propietario=nombre_propietario,
                dni_propietario=dni_propietario,
                modelo_auto=modelo_auto,
                color_auto=color_auto,
                activo=True
            )
            
            print(f"✅ Placa registrada: {placa} - {nombre_propietario}")
            
            return JsonResponse({
                "id": nueva_placa.id,
                "placa": nueva_placa.placa,
                "propietario": nueva_placa.propietario,
                "nombre_propietario": nueva_placa.nombre_propietario,
                "dni_propietario": nueva_placa.dni_propietario,
                "modelo_auto": nueva_placa.modelo_auto,
                "color_auto": nueva_placa.color_auto
            }, status=201)

        except Exception as e:
            print(f"❌ Error en listar_placas POST: {e}")
            return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def eliminar_placa(request, placa):
    """DELETE /api/placas/<placa>/ - Elimina una placa"""
    if request.method == 'DELETE':
        try:
            placa_obj = get_object_or_404(Registrada, placa=placa.upper())
            placa_obj.delete()
            print(f"✅ Placa eliminada: {placa}")
            return JsonResponse({"mensaje": "Placa eliminada"}, status=200)
        except Exception as e:
            print(f"❌ Error al eliminar placa: {e}")
            return JsonResponse({"error": str(e)}, status=404)


@csrf_exempt
def registrar_entrada(request):
    """POST /api/entrada/ - Registra una entrada"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            placa = data.get("placa", "").strip().upper()

            if not placa:
                return JsonResponse({"error": "Placa vacía"}, status=400)

            # Verificar que la placa esté registrada
            if not Registrada.objects.filter(placa=placa, activo=True).exists():
                return JsonResponse({"error": "Placa no registrada"}, status=400)

            # Verificar si ya tiene una entrada activa
            if Entrada.objects.filter(placa=placa, procesada=False).exists():
                return JsonResponse({"error": "Ya existe una entrada activa"}, status=400)

            # Crear entrada
            entrada = Entrada.objects.create(placa=placa)
            
            print(f"✅ Entrada registrada: {placa}")
            
            return JsonResponse({
                "id": entrada.id,
                "placa": entrada.placa,
                "entrada": entrada.entrada.strftime("%d/%m/%Y %H:%M:%S")
            }, status=201)

        except Exception as e:
            print(f"❌ Error en registrar_entrada: {e}")
            return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def registrar_salida(request):
    """POST /api/salida/ - Registra una salida y calcula el monto"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            placa = data.get("placa", "").strip().upper()

            if not placa:
                return JsonResponse({"error": "Placa vacía"}, status=400)

            # Buscar entrada sin procesar
            entrada = Entrada.objects.filter(placa=placa, procesada=False).order_by('-entrada').first()

            if not entrada:
                # No hay entrada activa, devolver None
                return JsonResponse({"error": "No hay entrada activa"}, status=404)

            # Calcular tiempo y monto
            ahora = timezone.now()
            segundos = (ahora - entrada.entrada).total_seconds()
            monto = calcular_monto_estacionamiento(segundos)

            # Actualizar entrada
            entrada.salida = ahora
            entrada.monto = monto
            entrada.procesada = True
            entrada.save()

            print(f"✅ Salida registrada: {placa} - Monto: S/ {monto}")

            return JsonResponse({
                "placa": placa,
                "entrada": entrada.entrada.strftime("%d/%m/%Y %H:%M:%S"),
                "salida": ahora.strftime("%d/%m/%Y %H:%M:%S"),
                "segundos": segundos,
                "monto": float(monto)
            }, status=200)

        except Exception as e:
            print(f"❌ Error en registrar_salida: {e}")
            return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def listar_movimientos(request):
    """GET /api/movimientos/ - Lista todos los movimientos"""
    if request.method == 'GET':
        try:
            entradas = Entrada.objects.all().order_by('-entrada')
            propietarios = {
                registro.placa: registro.nombre_propietario
                for registro in Registrada.objects.filter(
                    placa__in=[entrada.placa for entrada in entradas]
                )
            }
            
            movimientos = []
            for e in entradas:
                fin = e.salida or timezone.now()
                duracion = fin - e.entrada
                total_segundos = max(0, int(duracion.total_seconds()))
                horas = total_segundos // 3600
                minutos = (total_segundos % 3600) // 60
                movimientos.append({
                    "placa": e.placa,
                    "propietario": propietarios.get(e.placa, "Sin especificar"),
                    "entrada": e.entrada.strftime("%d/%m/%Y %H:%M:%S"),
                    "salida": e.salida.strftime("%d/%m/%Y %H:%M:%S") if e.salida else "",
                    "tiempo": f"{horas}h {minutos} min" if horas else f"{minutos} min",
                    "monto": f"S/ {float(e.monto):.2f}" if e.procesada else "-"
                })
            
            return JsonResponse(movimientos, safe=False)
            
        except Exception as e:
            print(f"❌ Error en listar_movimientos: {e}")
            return JsonResponse({"error": str(e)}, status=500)
    
    """DELETE /api/movimientos/ - Elimina todos los movimientos"""
    if request.method == 'DELETE':
        try:
            Entrada.objects.all().delete()
            print("✅ Todos los movimientos eliminados")
            return JsonResponse({"mensaje": "Movimientos eliminados"}, status=200)
        except Exception as e:
            print(f"❌ Error al eliminar movimientos: {e}")
            return JsonResponse({"error": str(e)}, status=500)




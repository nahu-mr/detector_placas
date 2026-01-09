from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.shortcuts import get_object_or_404
import json
from .models import Registrada, Entrada
from math import ceil

TARIFA_MINUTO = 0.15


@csrf_exempt
def listar_placas(request):
    """GET /api/placas/ - Lista todas las placas registradas"""
    if request.method == 'GET':
        placas = Registrada.objects.filter(activo=True).values('id', 'placa', 'propietario')
        return JsonResponse(list(placas), safe=False)
    
    """POST /api/placas/ - Registra una nueva placa"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            placa = data.get("placa", "").strip().upper()
            propietario = data.get("propietario", "Sin especificar").strip()

            if not placa:
                return JsonResponse({"error": "Placa vacía"}, status=400)

            # Verificar si ya existe
            if Registrada.objects.filter(placa=placa).exists():
                return JsonResponse({"error": "La placa ya existe"}, status=400)

            # Crear nueva placa
            nueva_placa = Registrada.objects.create(
                placa=placa,
                propietario=propietario,
                activo=True
            )
            
            print(f"✅ Placa registrada: {placa} - {propietario}")
            
            return JsonResponse({
                "id": nueva_placa.id,
                "placa": nueva_placa.placa,
                "propietario": nueva_placa.propietario
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
            minutos = ceil(segundos / 60)
            monto = round(minutos * TARIFA_MINUTO, 2)

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
            
            movimientos = []
            for e in entradas:
                # Entrada
                movimientos.append({
                    "placa": e.placa,
                    "accion": "ENTRADA",
                    "fecha": e.entrada.strftime("%d/%m/%Y %H:%M:%S"),
                    "monto": "-"
                })
                
                # Salida (si existe)
                if e.procesada and e.salida:
                    movimientos.append({
                        "placa": e.placa,
                        "accion": "SALIDA",
                        "fecha": e.salida.strftime("%d/%m/%Y %H:%M:%S"),
                        "monto": f"S/ {float(e.monto):.2f}"
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


from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, StreamingHttpResponse
from .models import Registrada, Entrada
from django.utils import timezone
import json
import cv2
import numpy as np
from PIL import Image
import sys
import os
import threading
import time
from queue import Queue

# Agregar la ruta del proyecto para importar detector
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from detector import detectar_placas

# Variables globales para la cámara
camera_lock = threading.Lock()
cap = None
current_frame = None
placas_en_proceso = {}
notificaciones_queue = Queue()  # Cola de eventos para SSE
placas_tiempo_entrada = {}  # Rastrear cuándo se registró cada entrada
placas_tiempo_salida = {}  # Rastrear cuándo se registró cada salida

@require_http_methods(["GET"])
def dashboard(request):
    """Vista principal del dashboard web"""
    context = {
        'placas_count': Registrada.objects.filter(activo=True).count(),
        'movimientos_today': Entrada.objects.filter(entrada__date=timezone.localdate()).count(),
    }
    return render(request, 'dashboard.html', context)

@require_http_methods(["GET"])
def get_placas(request):
    """API para obtener placas registradas"""
    placas = Registrada.objects.filter(activo=True).values('id', 'placa', 'propietario')
    return JsonResponse(list(placas), safe=False)

@require_http_methods(["GET"])
def get_movimientos(request):
    """API para obtener movimientos del día"""
    movimientos = Entrada.objects.all().order_by('-entrada').values(
        'placa', 'entrada', 'salida', 'monto', 'procesada'
    )[:50]
    
    result = []
    for mov in movimientos:
        result.append({
            'placa': mov['placa'],
            'entrada': formatear_hora_local(mov['entrada']),
            'salida': formatear_hora_local(mov['salida']),
            'monto': f"S/ {mov['monto']:.2f}" if mov['procesada'] else '-',
            'accion': 'SALIDA' if mov['salida'] else 'ENTRADA'
        })
    return JsonResponse(result, safe=False)

@require_http_methods(["POST"])
@csrf_exempt
def add_placa(request):
    """Agregar nueva placa"""
    try:
        data = json.loads(request.body)
        placa = data.get('placa', '').strip().upper()
        propietario = data.get('propietario', 'Sin especificar').strip()
        
        if not placa:
            return JsonResponse({'error': 'Placa vacía'}, status=400)
        
        if Registrada.objects.filter(placa=placa).exists():
            return JsonResponse({'error': 'La placa ya existe'}, status=400)
        
        nueva = Registrada.objects.create(placa=placa, propietario=propietario, activo=True)
        return JsonResponse({'success': True, 'placa': nueva.placa}, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["DELETE"])
@csrf_exempt
def delete_placa(request, placa):
    """Eliminar una placa"""
    try:
        p = Registrada.objects.get(placa=placa.upper())
        p.delete()
        return JsonResponse({'success': True})
    except Registrada.DoesNotExist:
        return JsonResponse({'error': 'Placa no encontrada'}, status=404)


@require_http_methods(["PUT"])
@csrf_exempt
def update_placa(request, placa):
    """Actualiza la placa y/o el propietario de un registro autorizado."""
    try:
        registro = Registrada.objects.get(placa=placa.upper())
        data = json.loads(request.body)
        nueva_placa = data.get('placa', registro.placa).strip().upper()
        propietario = data.get('propietario', '').strip() or 'Sin especificar'

        if not nueva_placa:
            return JsonResponse({'error': 'La placa no puede estar vacía'}, status=400)

        if Registrada.objects.exclude(pk=registro.pk).filter(placa=nueva_placa).exists():
            return JsonResponse({'error': 'La placa ya existe'}, status=400)

        registro.placa = nueva_placa
        registro.propietario = propietario
        registro.save()
        return JsonResponse({
            'success': True,
            'placa': registro.placa,
            'propietario': registro.propietario,
        })
    except Registrada.DoesNotExist:
        return JsonResponse({'error': 'Placa no encontrada'}, status=404)
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Datos inválidos'}, status=400)

def iniciar_camara_streaming():
    """Inicia la cámara para streaming continuo"""
    global cap
    if cap is None:
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)
        print("✅ Cámara iniciada para streaming")

def detener_camara_streaming():
    """Detiene la cámara de streaming"""
    global cap
    with camera_lock:
        if cap:
            try:
                cap.release()
            except:
                pass
            cap = None
            print("❌ Cámara detenida correctamente")

def generar_frames():
    """Generador de frames para MJPEG streaming"""
    global cap, current_frame
    
    iniciar_camara_streaming()
    
    placas_procesadas = set()
    tiempo_limpieza = time.time()
    
    while cap is not None:  # Verificar que cap existe
        try:
            with camera_lock:  # Proteger acceso a cap
                if cap is None:  # Si se detuvo durante la lectura, salir
                    break
                ret, frame = cap.read()
            
            if not ret:
                time.sleep(0.1)  # Esperar un poco antes de reintentar
                continue
            
            # Detectar placas
            placas = detectar_placas(frame)
            
            # Procesar placas detectadas
            for placa, (x1, y1, x2, y2) in placas:
                # Dibujar rectángulo y texto
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 217, 255), 3)
                cv2.putText(frame, placa, (x1, y1 - 15),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 217, 255), 3)
                
                # Procesar si es nueva
                if placa not in placas_procesadas:
                    placas_procesadas.add(placa)
                    threading.Thread(target=procesar_placa_async, args=(placa,), daemon=True).start()
            
            # Limpiar placas antiguas cada 5 segundos
            if time.time() - tiempo_limpieza > 5:
                placas_procesadas.clear()
                tiempo_limpieza = time.time()
            
            # Codificar frame a JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_bytes = buffer.tobytes()
            
            # Yield como MJPEG
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n'
                   b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n\r\n' 
                   + frame_bytes + b'\r\n')
            
        except GeneratorExit:
            # Cuando el cliente desconecta
            print("🔌 Cliente desconectó del stream")
            break
        except Exception as e:
            print(f"Error en generar_frames: {e}")
            time.sleep(0.1)
            # Reiniciar cámara si hubo error
            if cap is None:
                iniciar_camara_streaming()
            continue
    
    # Al terminar el generador, detener la cámara
    detener_camara_streaming()

@require_http_methods(["GET"])
def video_feed(request):
    """Endpoint para streaming de video MJPEG"""
    try:
        return StreamingHttpResponse(
            generar_frames(),
            content_type='multipart/x-mixed-replace; boundary=frame'
        )
    except Exception as e:
        print(f"Error en video_feed: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["POST"])
@csrf_exempt
def iniciar_streaming(request):
    """Inicia el streaming de cámara"""
    try:
        iniciar_camara_streaming()
        return JsonResponse({'status': 'streaming'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["POST"])
@csrf_exempt
def detener_streaming(request):
    """Detiene el streaming"""
    try:
        detener_camara_streaming()
        return JsonResponse({'status': 'stopped'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def generar_notificaciones():
    """Generador de eventos SSE para notificaciones en tiempo real"""
    while True:
        try:
            # Obtener evento de la cola (con timeout para evitar bloqueo infinito)
            evento = notificaciones_queue.get(timeout=1)
            yield f"data: {json.dumps(evento)}\n\n"
        except:
            # Timeout - enviar heartbeat
            yield f": heartbeat\n\n"

@require_http_methods(["GET"])
def notificaciones_stream(request):
    """Endpoint SSE para notificaciones en tiempo real"""
    return StreamingHttpResponse(
        generar_notificaciones(),
        content_type='text/event-stream'
    )



def procesar_placa_async(placa):
    """Procesar placa detectada (async) - Mismo flujo que interfaz_optimizada.py"""
    try:
        placa = placa.strip().upper()
        
        # Verificar si está registrada
        if not Registrada.objects.filter(placa=placa, activo=True).exists():
            # Notificar que no está registrada
            evento = {
                'tipo': 'advertencia',
                'mensaje': f'La placa {placa} no está registrada en el sistema.',
                'placa': placa
            }
            notificaciones_queue.put(evento)
            print(f"❌ ADVERTENCIA: Placa no registrada: {placa}")
            return
        
        # Intentar registrar salida
        entrada = Entrada.objects.filter(placa=placa, salida__isnull=True).first()
        
        if not entrada:
            # VERIFICAR SI HAN PASADO 3 SEGUNDOS DESDE LA ÚLTIMA SALIDA
            tiempo_salida = placas_tiempo_salida.get(placa)
            if tiempo_salida is not None:
                tiempo_transcurrido_salida = time.time() - tiempo_salida
                
                # Si han pasado menos de 3 segundos desde la salida, no procesar entrada
                if tiempo_transcurrido_salida < 3:
                    print(f"⏳ Placa {placa} detectada pero espera de salida ({tiempo_transcurrido_salida:.1f}s). Requiere 3s antes de nueva entrada.")
                    return
                else:
                    # Ya pasaron 3 segundos, limpiar registro de salida
                    del placas_tiempo_salida[placa]
            
            # Nueva entrada
            nueva_entrada = Entrada.objects.create(placa=placa, entrada=timezone.now())
            
            # Rastrear tiempo de entrada (para retraso de 3 segundos)
            placas_tiempo_entrada[placa] = time.time()
            
            evento = {
                'tipo': 'entrada',
                'placa': placa,
                'mensaje': f'✅ Placa: {placa}\n\nRegistrada como ENTRADA\n\nFecha: {formatear_hora_local(timezone.now())}',
                'fecha': formatear_hora_local(timezone.now())
            }
            notificaciones_queue.put(evento)
            print(f"✅ ENTRADA registrada: {placa}")
        else:
            # VERIFICAR SI HAN PASADO AL MENOS 3 SEGUNDOS DESDE LA ENTRADA
            tiempo_entrada = placas_tiempo_entrada.get(placa)
            if tiempo_entrada is None:
                # Si no hay registro de tiempo, permitir salida (por si acaso)
                tiempo_entrada = entrada.entrada.timestamp()
                placas_tiempo_entrada[placa] = tiempo_entrada
            
            tiempo_transcurrido = time.time() - tiempo_entrada
            
            # Si han pasado menos de 3 segundos, no procesar salida
            if tiempo_transcurrido < 3:
                print(f"⏳ Placa {placa} detectada de nuevo pero muy rápido ({tiempo_transcurrido:.1f}s). Esperando 3s mínimo.")
                return
            
            # Registrar salida
            salida = timezone.now()
            duracion_segundos = (salida - entrada.entrada).total_seconds()
            duracion_minutos = round(duracion_segundos / 60, 1)
            
            tarifa_minuto = 0.15
            monto = round(duracion_minutos * tarifa_minuto, 2)
            
            entrada.salida = salida
            entrada.monto = monto
            entrada.procesada = True
            entrada.save()
            
            # Rastrear tiempo de salida para delay antes de siguiente entrada
            placas_tiempo_salida[placa] = time.time()
            
            # Limpiar del diccionario de rastreo de entrada
            if placa in placas_tiempo_entrada:
                del placas_tiempo_entrada[placa]
            
            evento = {
                'tipo': 'salida',
                'placa': placa,
                'mensaje': f'💰 COBRO GENERADO\n\nPlaca: {placa}\nTiempo: {duracion_minutos} minutos\nMonto: S/ {monto:.2f}',
                'duracion': duracion_minutos,
                'monto': monto,
                'fecha': formatear_hora_local(salida)
            }
            notificaciones_queue.put(evento)
            print(f"✅ SALIDA registrada: {placa} - Monto: S/ {monto}")
    
    except Exception as e:
        print(f"Error procesando placa {placa}: {e}")
        evento = {
            'tipo': 'error',
            'mensaje': f'Error al procesar la placa {placa}',
            'placa': placa
        }
        notificaciones_queue.put(evento)

@require_http_methods(["POST"])
def registrar_salida(request):
    """Registrar salida de vehículo y calcular tarifa"""
    try:
        data = json.loads(request.body)
        placa = data.get('placa', '').strip().upper()
        
        if not placa:
            return JsonResponse({'error': 'Placa vacía'}, status=400)
        
        entrada = Entrada.objects.filter(placa=placa, salida__isnull=True).first()
        if not entrada:
            return JsonResponse({'error': 'No hay entrada registrada'}, status=400)
        
        salida = timezone.now()
        duracion_segundos = (salida - entrada.entrada).total_seconds()
        duracion_minutos = duracion_segundos / 60
        
        tarifa_minuto = 0.15
        monto = round(duracion_minutos * tarifa_minuto, 2)
        
        entrada.salida = salida
        entrada.monto = monto
        entrada.procesada = True
        entrada.save()
        
        return JsonResponse({
            'success': True,
            'placa': entrada.placa,
            'salida': formatear_hora_local(salida),
            'monto': f"{monto:.2f}",
            'duracion': f"{duracion_minutos:.1f} min"
        }, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["DELETE"])
@csrf_exempt
def clear_movimientos(request):
    """Eliminar todos los movimientos de la tabla Entrada"""
    try:
        count, _ = Entrada.objects.all().delete()
        return JsonResponse({
            'success': True,
            'message': f'Se eliminaron {count} movimientos',
            'count': count
        }, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def formatear_hora_local(fecha):
    """Convierte fechas UTC almacenadas por Django a hora local de Lima."""
    return timezone.localtime(fecha).strftime("%d/%m/%Y %H:%M:%S") if fecha else '-'

from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
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
from datetime import datetime, timedelta
import io
import zipfile
from xml.sax.saxutils import escape

# Agregar la ruta del proyecto para importar detector
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from detector import detectar_placas
from .views import calcular_monto_estacionamiento

# Variables globales para la cámara
camera_lock = threading.Lock()
cap = None
current_frame = None
camera_stop_requested = False
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
    placas = Registrada.objects.filter(activo=True).values(
        'id', 'placa', 'propietario', 'nombre_propietario',
        'dni_propietario', 'modelo_auto', 'color_auto'
    )
    return JsonResponse(list(placas), safe=False)

@require_http_methods(["GET"])
def get_movimientos(request):
    """API para obtener movimientos del día"""
    movimientos = Entrada.objects.all().order_by('-entrada').values(
        'placa', 'entrada', 'salida', 'monto', 'procesada'
    )[:50]
    propietarios = {
        registro.placa: registro.nombre_propietario
        for registro in Registrada.objects.filter(
            placa__in=[mov['placa'] for mov in movimientos]
        )
    }
    
    result = []
    for mov in movimientos:
        fin = mov['salida'] or timezone.now()
        duracion = fin - mov['entrada'] if mov['entrada'] else timedelta()
        total_segundos = max(0, int(duracion.total_seconds()))
        horas = total_segundos // 3600
        minutos = (total_segundos % 3600) // 60
        result.append({
            'placa': mov['placa'],
            'propietario': propietarios.get(mov['placa'], 'Sin especificar'),
            'entrada': formatear_hora_local(mov['entrada']),
            'salida': formatear_hora_local(mov['salida']),
            'tiempo': f"{horas}h {minutos} min" if horas else f"{minutos} min",
            'monto': f"S/ {mov['monto']:.2f}" if mov['procesada'] else '-',
        })
    return JsonResponse(result, safe=False)

@require_http_methods(["POST"])
@csrf_exempt
def add_placa(request):
    """Agregar nueva placa"""
    try:
        data = json.loads(request.body)
        placa = data.get('placa', '').strip().upper()
        nombre_propietario = data.get('nombre_propietario', data.get('propietario', 'Sin especificar')).strip() or 'Sin especificar'
        dni_propietario = data.get('dni_propietario', '').strip()
        modelo_auto = data.get('modelo_auto', '').strip()
        color_auto = data.get('color_auto', '').strip()
        
        if not placa:
            return JsonResponse({'error': 'Placa vacía'}, status=400)
        
        if Registrada.objects.filter(placa=placa).exists():
            return JsonResponse({'error': 'La placa ya existe'}, status=400)
        
        nueva = Registrada.objects.create(
            placa=placa,
            propietario=nombre_propietario,
            nombre_propietario=nombre_propietario,
            dni_propietario=dni_propietario,
            modelo_auto=modelo_auto,
            color_auto=color_auto,
            activo=True
        )
        return JsonResponse({
            'success': True,
            'placa': nueva.placa,
            'propietario': nueva.propietario,
            'nombre_propietario': nueva.nombre_propietario,
            'dni_propietario': nueva.dni_propietario,
            'modelo_auto': nueva.modelo_auto,
            'color_auto': nueva.color_auto,
        }, status=201)
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
    """Actualiza los datos de un registro autorizado."""
    try:
        registro = Registrada.objects.get(placa=placa.upper())
        data = json.loads(request.body)
        nueva_placa = data.get('placa', registro.placa).strip().upper()
        nombre_propietario = data.get('nombre_propietario', data.get('propietario', '')).strip() or 'Sin especificar'
        dni_propietario = data.get('dni_propietario', '').strip()
        modelo_auto = data.get('modelo_auto', '').strip()
        color_auto = data.get('color_auto', '').strip()

        if not nueva_placa:
            return JsonResponse({'error': 'La placa no puede estar vacía'}, status=400)

        if Registrada.objects.exclude(pk=registro.pk).filter(placa=nueva_placa).exists():
            return JsonResponse({'error': 'La placa ya existe'}, status=400)

        registro.placa = nueva_placa
        registro.propietario = nombre_propietario
        registro.nombre_propietario = nombre_propietario
        registro.dni_propietario = dni_propietario
        registro.modelo_auto = modelo_auto
        registro.color_auto = color_auto
        registro.save()
        return JsonResponse({
            'success': True,
            'placa': registro.placa,
            'propietario': registro.propietario,
            'nombre_propietario': registro.nombre_propietario,
            'dni_propietario': registro.dni_propietario,
            'modelo_auto': registro.modelo_auto,
            'color_auto': registro.color_auto,
        })
    except Registrada.DoesNotExist:
        return JsonResponse({'error': 'Placa no encontrada'}, status=404)
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Datos inválidos'}, status=400)


def iniciar_camara_streaming():
    """Inicia la camara para streaming continuo con fallback de backend."""
    global cap, camera_stop_requested
    camera_stop_requested = False
    if cap is not None:
        return True

    backends = (
        (0, cv2.CAP_DSHOW),
        (1, cv2.CAP_DSHOW),
        (0, cv2.CAP_ANY),
        (1, cv2.CAP_ANY),
    )
    for indice, backend in backends:
        prueba = cv2.VideoCapture(indice, backend)
        if not prueba.isOpened():
            prueba.release()
            continue

        prueba.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        prueba.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        prueba.set(cv2.CAP_PROP_FPS, 30)
        ret, _ = prueba.read()
        if ret:
            cap = prueba
            print(f"Camara iniciada para streaming (indice {indice})")
            return True

        prueba.release()

    cap = None
    print("No se pudo iniciar la camara: no entrega imagen")
    return False


def detener_camara_streaming():
    """Detiene la cámara de streaming"""
    global cap, camera_stop_requested
    camera_stop_requested = True
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
    global cap, current_frame, camera_stop_requested
    
    iniciar_camara_streaming()
    
    placas_procesadas = set()
    tiempo_limpieza = time.time()
    
    while cap is not None and not camera_stop_requested:  # Verificar que cap existe
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
            if cap is None and not camera_stop_requested:
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
        if not iniciar_camara_streaming():
            return JsonResponse({'error': 'No se pudo abrir la camara'}, status=503)
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
            monto = calcular_monto_estacionamiento(duracion_segundos)
            
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
        monto = calcular_monto_estacionamiento(duracion_segundos)
        
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


def _parse_fecha(valor):
    return datetime.strptime(valor, "%Y-%m-%d").date()


def _rango_reporte(request):
    tipo = request.GET.get('tipo', 'dia')
    hoy = timezone.localdate()

    if tipo == 'rango':
        inicio = _parse_fecha(request.GET.get('desde') or hoy.isoformat())
        fin = _parse_fecha(request.GET.get('hasta') or inicio.isoformat())
    elif tipo == 'mes':
        anio = int(request.GET.get('anio') or hoy.year)
        mes = int(request.GET.get('mes') or hoy.month)
        inicio = datetime(anio, mes, 1).date()
        if mes == 12:
            fin = datetime(anio, 12, 31).date()
        else:
            fin = datetime(anio, mes + 1, 1).date() - timedelta(days=1)
    elif tipo == 'anio':
        anio = int(request.GET.get('anio') or hoy.year)
        inicio = datetime(anio, 1, 1).date()
        fin = datetime(anio, 12, 31).date()
    else:
        inicio = _parse_fecha(request.GET.get('fecha') or hoy.isoformat())
        fin = inicio

    if fin < inicio:
        inicio, fin = fin, inicio

    inicio_dt = timezone.make_aware(datetime.combine(inicio, datetime.min.time()))
    fin_exclusivo = timezone.make_aware(datetime.combine(fin + timedelta(days=1), datetime.min.time()))
    etiqueta = f"{inicio.strftime('%Y%m%d')}_{fin.strftime('%Y%m%d')}"
    return inicio_dt, fin_exclusivo, etiqueta


def _duracion_texto(inicio, fin):
    if not inicio:
        return "-"
    fin = fin or timezone.now()
    total_segundos = max(0, int((fin - inicio).total_seconds()))
    horas = total_segundos // 3600
    minutos = (total_segundos % 3600) // 60
    return f"{horas}h {minutos}min" if horas else f"{minutos}min"


def _xlsx_cell(valor, fila, columna):
    letras = ""
    indice = columna
    while indice:
        indice, resto = divmod(indice - 1, 26)
        letras = chr(65 + resto) + letras
    referencia = f"{letras}{fila}"
    texto = escape("" if valor is None else str(valor))
    return f'<c r="{referencia}" t="inlineStr"><is><t>{texto}</t></is></c>'


def _crear_worksheet(filas):
    sheet_rows = []
    for numero_fila, fila in enumerate(filas, start=1):
        celdas = ''.join(_xlsx_cell(valor, numero_fila, indice) for indice, valor in enumerate(fila, start=1))
        sheet_rows.append(f'<row r="{numero_fila}">{celdas}</row>')

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>' + ''.join(sheet_rows) + '</sheetData></worksheet>'
    )


def _crear_xlsx(hojas):
    buffer = io.BytesIO()
    sheets_xml = ''.join(
        f'<sheet name="{escape(nombre)}" sheetId="{indice}" r:id="rId{indice}"/>'
        for indice, (nombre, _) in enumerate(hojas, start=1)
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets>{sheets_xml}</sheets></workbook>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    workbook_rels_items = ''.join(
        f'<Relationship Id="rId{indice}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{indice}.xml"/>'
        for indice, _ in enumerate(hojas, start=1)
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{workbook_rels_items}</Relationships>'
    )
    worksheet_types = ''.join(
        f'<Override PartName="/xl/worksheets/sheet{indice}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for indice, _ in enumerate(hojas, start=1)
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        f'{worksheet_types}</Types>'
    )

    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archivo:
        archivo.writestr('[Content_Types].xml', content_types)
        archivo.writestr('_rels/.rels', rels)
        archivo.writestr('xl/workbook.xml', workbook)
        archivo.writestr('xl/_rels/workbook.xml.rels', workbook_rels)
        for indice, (_, filas) in enumerate(hojas, start=1):
            archivo.writestr(f'xl/worksheets/sheet{indice}.xml', _crear_worksheet(filas))
    return buffer.getvalue()


@require_http_methods(["GET"])
def exportar_reporte_movimientos(request):
    """Descarga un reporte Excel de movimientos filtrado por fecha."""
    try:
        inicio_dt, fin_dt, etiqueta = _rango_reporte(request)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Filtros de fecha invalidos'}, status=400)

    movimientos = list(Entrada.objects.filter(
        entrada__gte=inicio_dt,
        entrada__lt=fin_dt
    ).order_by('entrada'))
    propietarios = {
        registro.placa: registro.nombre_propietario
        for registro in Registrada.objects.filter(
            placa__in=[movimiento.placa for movimiento in movimientos]
        )
    }

    total_finalizados = sum(1 for movimiento in movimientos if movimiento.salida)
    total_dentro = len(movimientos) - total_finalizados
    total_monto = sum(float(movimiento.monto) for movimiento in movimientos if movimiento.procesada)
    resumen = [
        ['Reporte de movimientos'],
        ['Generado', formatear_hora_local(timezone.now())],
        ['Desde', formatear_hora_local(inicio_dt)],
        ['Hasta', formatear_hora_local(fin_dt - timedelta(seconds=1))],
        ['Total movimientos', len(movimientos)],
        ['Finalizados', total_finalizados],
        ['Dentro', total_dentro],
        ['Monto total', f"S/ {total_monto:.2f}"],
    ]

    detalle = [[
        'Placa', 'Propietario', 'Entrada', 'Salida',
        'Tiempo', 'Monto', 'Estado'
    ]]
    for movimiento in movimientos:
        detalle.append([
            movimiento.placa,
            propietarios.get(movimiento.placa, 'Sin especificar'),
            formatear_hora_local(movimiento.entrada),
            formatear_hora_local(movimiento.salida),
            _duracion_texto(movimiento.entrada, movimiento.salida),
            f"S/ {float(movimiento.monto):.2f}" if movimiento.procesada else "-",
            'Finalizado' if movimiento.salida else 'Dentro',
        ])

    contenido = _crear_xlsx([
        ('Resumen', resumen),
        ('Movimientos', detalle),
    ])
    nombre = f"reporte_movimientos_{etiqueta}.xlsx"
    response = HttpResponse(
        contenido,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{nombre}"'
    return response


def formatear_hora_local(fecha):
    """Convierte fechas UTC almacenadas por Django a hora local de Lima."""
    return timezone.localtime(fecha).strftime("%d/%m/%Y %H:%M:%S") if fecha else '-'

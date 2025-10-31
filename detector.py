# detector.py
from ultralytics import YOLO
import easyocr
import re

# Carga modelo y OCR solo una vez al inicio
model = YOLO("best.pt")  # Asegúrate de tener el modelo en el mismo directorio
reader = easyocr.Reader(["en"])  # OCR alfanumérico

# Patrones válidos de placas peruanas
# === Patrones válidos de placas peruanas (actualizado 2025) ===
PATRONES_PLACA = [
    # Formato clásico: tres letras y tres números
    r"^(?:PERU\s*)?[A-Z]{3}-\d{3}$",
    # Formato mixto alfanumérico (como A1A-950, 1AB-234, AB1-456, etc.)
    r"^(?:PERU\s*)?[A-Z0-9]{3}-\d{3}$",
]

def normalizar_texto_placa(texto):
    """
    Limpia y corrige errores OCR comunes sin alterar el formato de la placa.
    No aplica restricciones de letras/números (válido para el sistema 2025).
    """
    texto = texto.upper().strip().replace(" ", "")
    reemplazos = {
        "O": "0", "I": "1", "L": "1", "B": "8", "S": "5", "|": "1"
    }
    for k, v in reemplazos.items():
        texto = texto.replace(k, v)
    texto = texto.replace("PERU", "")  # elimina prefijo si aparece en OCR
    return texto

def es_placa_peruana(texto):
    """Valida si el texto coincide con formato de placa peruana."""
    texto = normalizar_texto_placa(texto)
    for patron in PATRONES_PLACA:
        if re.match(patron, texto):
            return texto
    return None

def detectar_placas(frame):
    """
    Detecta placas vehiculares en tiempo real con YOLO + EasyOCR.
    Devuelve lista [(placa, (x1, y1, x2, y2)), ...]
    """
    placas_detectadas = []
    results = model(frame)
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            crop = frame[y1:y2, x1:x2]

            # OCR en la región detectada
            textos = reader.readtext(crop, detail=0)
            if not textos:
                continue
            texto_raw = " ".join(textos).strip()
            placa = es_placa_peruana(texto_raw)
            if placa:
                placas_detectadas.append((placa, (x1, y1, x2, y2)))
    return placas_detectadas

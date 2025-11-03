# detector.py
from ultralytics import YOLO
import easyocr
import re #modulo para trabajar con expresiones regulares - patrones de placas

# Carga modelo y OCR solo una vez al inicio
model = YOLO("best.pt")
reader = easyocr.Reader(["en"])  # OCR alfanumérico

# Patrones válidos de placas peruanas
# === Patrones válidos de placas peruanas (actualizado 2025) ===

# Formatos válidos de placa peruana
PATRONES_PLACA = [
    r"^(?:PERU\s*)?[A-Z][A-Z0-9][A-Z]-\d{3}$",  # Ej: A1B-234, K2X-781, ABC-123
]

def normalizar_texto_placa(texto):
    """
    Limpia y corrige errores OCR comunes en placas peruanas (formato 2025):
    L₁-X₂-L₃-D₄D₅D₆, donde:
      - L₁ y L₃ son letras.
      - X₂ puede ser letra o número.
      - D₄D₅D₆ siempre son números.
    """
    texto = texto.upper().strip()
    texto = texto.replace(" ", "")
    texto = texto.replace("PERU", "")

    # Asegurar que haya guion (OCR puede omitirlo)
    if "-" not in texto and len(texto) >= 6:
        texto = texto[:3] + "-" + texto[3:]

    # Validar que tenga estructura tipo XXX-XXX
    if not re.match(r"^[A-Z0-9]{3}-[A-Z0-9]{3}$", texto):
        return texto  # no intentamos corregir si es ilegible

    parte_letras = list(texto.split("-")[0])
    parte_numeros = list(texto.split("-")[1])

    # --- Correcciones específicas por posición ---

    # Posición 1 (debe ser letra)
    if parte_letras[0] in ["0", "1", "2", "5", "8"]:
        reemplazos = {"0": "O", "1": "I", "2": "Z", "5": "S", "8": "B"}
        parte_letras[0] = reemplazos.get(parte_letras[0], parte_letras[0])

    # Posición 2 (puede ser letra o número)
    if parte_letras[1] in ["I"]:
        reemplazos = {"I": "1"}
        parte_letras[1] = reemplazos.get(parte_letras[1], parte_letras[1])

    # Posición 3 (debe ser letra)
    if parte_letras[2] in ["0", "1", "2", "5", "8"]:
        reemplazos = {"0": "O", "1": "I", "2": "Z", "5": "S", "8": "B"}
        parte_letras[2] = reemplazos.get(parte_letras[2], parte_letras[2])

    # Parte numérica (solo deben quedar números)
    for i in range(3):
        if parte_numeros[i] in ["O", "Q", "B", "S", "I", "L"]:
            reemplazos = {"O": "0", "Q": "0", "B": "8", "S": "5", "I": "1", "L": "1"}
            parte_numeros[i] = reemplazos.get(parte_numeros[i], parte_numeros[i])

    texto_normalizado = "".join(parte_letras) + "-" + "".join(parte_numeros)
    return texto_normalizado


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

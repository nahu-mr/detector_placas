from ultralytics import YOLO
import cv2
import easyocr

# Inicializa el modelo y OCR
model = YOLO("best.pt")
reader = easyocr.Reader(["en"])  # OCR en inglés (también reconoce letras/números latinos)

# Abre la cámara
cap = cv2.VideoCapture(0)

# Lista para guardar placas detectadas
placas_detectadas = []

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Detectar placas con YOLO
    results = model(frame)
    annotated_frame = frame.copy()

    for result in results:
        for box in result.boxes:
            # Coordenadas del rectángulo
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # Recortar la región de la placa
            placa_crop = frame[y1:y2, x1:x2]

            # Leer texto con EasyOCR
            texto = reader.readtext(placa_crop, detail=0)
            texto_placa = " ".join(texto).strip()

            # Guardar si no está vacío ni repetido
            if texto_placa and texto_placa not in placas_detectadas:
                placas_detectadas.append(texto_placa)
                print(f"Placa detectada: {texto_placa}")

            # Dibujar el rectángulo y el texto
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                annotated_frame,
                texto_placa if texto_placa else "Detectando...",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

    # Mostrar el resultado
    cv2.imshow("Detección de Placas Peruanas", annotated_frame)

    # Presiona ESC para salir
    if cv2.waitKey(1) & 0xFF == 27:
        break

# Liberar recursos
cap.release()
cv2.destroyAllWindows()

# Mostrar todas las placas detectadas
print("\n📋 Placas detectadas durante la sesión:")
for p in placas_detectadas:
    print(" -", p)

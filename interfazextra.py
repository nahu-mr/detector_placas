import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import cv2
from ultralytics import YOLO
import easyocr
import datetime
import re

# === Inicialización del modelo y OCR ===
model = YOLO("best.pt")  # Modelo entrenado
reader = easyocr.Reader(["en"])  # OCR para texto alfanumérico

# === Configuración de ventana principal ===
root = tk.Tk()
root.title("Sistema de Verificación de Placas Vehiculares")
root.geometry("900x700")
root.configure(bg="#f0f0f0")

# === Frame para la cámara (fijo, color naranja) ===
img_frame = tk.Frame(root, borderwidth=5, relief="solid", width=640, height=480)
img_frame.pack(pady=10)
img_frame.pack_propagate(False)  # 🔒 Mantiene el tamaño fijo
lmain = tk.Label(img_frame, bg="black")
lmain.pack(fill="both", expand=True)

# === Frame para botones ===
btn_frame = tk.Frame(root, bg="#f0f0f0")
btn_frame.pack(pady=10)

# === Frame para registro de placas detectadas ===
registro_frame = tk.Frame(root, bg="#f0f0f0")
registro_frame.pack(pady=10)

tk.Label(registro_frame, text="📋 Placas Detectadas", font=("Arial", 12, "bold"), bg="#f0f0f0").pack()

columns = ("Placa", "Fecha", "Hora")
tree = ttk.Treeview(registro_frame, columns=columns, show="headings", height=8)
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=150, anchor="center")
tree.pack()

# === Variables globales ===
cap = None
after_id = None
placas_detectadas = set()

import re

# === Patrones de placas peruanas ===
PATRONES_PLACA = [
    r"^(?:PERU\s*)?[A-Z]{3}-\d{3}$",      # ABC-123 o PERU ABC-123
    r"^(?:PERU\s*)?[A-Z]{2}-\d{4}$",      # AB-1234 o PERU AB-1234
    r"^(?:PERU\s*)?[A-Z]\d[A-Z]-\d{3}$",  # A1B-234 o PERU A1B-234
]

def normalizar_texto_placa(texto):
    """Corrige errores OCR comunes, sin alterar letras legítimas."""
    texto = texto.upper().strip().replace(" ", "")
    texto = re.sub(r"^PERU", "", texto)  # quita 'PERU' si está presente

    # Si hay guion, separamos en letras y números
    if "-" in texto:
        partes = texto.split("-")
        letras = partes[0]
        numeros = partes[1]

        # Corrige errores en la parte numérica
        numeros_corr = (
            numeros.replace("O", "0")
                   .replace("I", "1")
                   .replace("L", "1")
                   .replace("B", "8")
                   .replace("S", "5")
                   .replace("|", "1")
        )

        # También corregimos un caso especial: letra central de tipo A1B-234
        letras_corr = (
            letras.replace("1", "I")  # si el OCR puso 1 en la zona de letras
        )

        texto = f"{letras_corr}-{numeros_corr}"
    else:
        # Si no tiene guion, aplicamos corrección leve
        texto = texto.replace("|", "1").replace("B", "8")

    return texto

def es_placa_peruana(texto):
    texto = normalizar_texto_placa(texto)
    for patron in PATRONES_PLACA:
        if re.match(patron.replace(" ", ""), texto):
            return texto
    return None

# === Funciones ===
def iniciar_camara():
    global cap, after_id
    if cap is None:
        cap = cv2.VideoCapture(0)

    ret, frame = cap.read()
    if not ret:
        print("⚠️ No se pudo acceder a la cámara.")
        return

    # === Detección con YOLO ===
    results = model(frame)
    annotated_frame = frame.copy()

    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            placa_crop = frame[y1:y2, x1:x2]

            # OCR sobre la placa
            texto = reader.readtext(placa_crop, detail=0)
            texto_placa = " ".join(texto).strip()

            # Dibujar caja y texto
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)  # naranja BGR
            cv2.putText(
                annotated_frame,
                texto_placa if texto_placa else "Detectando...",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
            )

            # Validar formato de placa peruana
            placa_valida = es_placa_peruana(texto_placa)
            if placa_valida and placa_valida not in placas_detectadas:
                placas_detectadas.add(placa_valida)
                fecha = datetime.datetime.now().strftime("%Y-%m-%d")
                hora = datetime.datetime.now().strftime("%H:%M:%S")
                tree.insert("", "end", values=(placa_valida, fecha, hora))
                print(f"✅ Placa detectada: {placa_valida}")

    # === Mostrar imagen en la GUI ===
    frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
    img = ImageTk.PhotoImage(Image.fromarray(frame_rgb))
    lmain.imgtk = img
    lmain.configure(image=img)

    after_id = lmain.after(30, iniciar_camara)

def detener_camara():
    global after_id, cap
    if after_id is not None:
        lmain.after_cancel(after_id)
        after_id = None
    if cap is not None:
        cap.release()
        cap = None
    # Mantiene el tamaño del frame
    lmain.configure(image="", bg="black")

def vaciar_registro():
    global placas_detectadas
    placas_detectadas.clear()
    for item in tree.get_children():
        tree.delete(item)
    print("🧹 Registro vaciado")

def detener():
    detener_camara()
    root.destroy()

# === Botones ===
tk.Button(btn_frame, text="Iniciar Detector", command=iniciar_camara, width=15).pack(side=tk.LEFT, padx=5)
tk.Button(btn_frame, text="Detener Detector", command=detener_camara, width=15).pack(side=tk.LEFT, padx=5)
tk.Button(btn_frame, text="Vaciar Registro", command=vaciar_registro, width=15).pack(side=tk.LEFT, padx=5)
tk.Button(btn_frame, text="Cerrar", command=detener, width=15).pack(side=tk.LEFT, padx=5)

# === Ejecutar la app ===
root.mainloop()

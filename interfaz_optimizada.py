import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import cv2
import datetime
import threading

import db
from detector import detectar_placas


# === CONFIGURACIÓN DE VENTANA ===
root = tk.Tk()
root.title("Sistema de Control Vehicular - Perú (Optimizado)")
root.geometry("1100x900")
root.configure(bg="#f0f0f0")

# === FRAME DE CÁMARA ===
frame_camara = tk.Frame(root, bg="orange", bd=5, relief="solid", width=750, height=450)
frame_camara.pack(side=tk.TOP, pady=15)
frame_camara.pack_propagate(False)

lmain = tk.Label(frame_camara, bg="black")
lmain.pack(fill="both", expand=True)

# === FRAME BOTONES ===
frame_botones = tk.Frame(root, bg="#e0e0e0")
frame_botones.pack(side=tk.TOP, pady=15, fill="x")

# Sub-frame centrado dentro del principal
frame_botones_centro = tk.Frame(frame_botones, bg="#e0e0e0")
frame_botones_centro.pack(anchor="center")  # 🔹 Centra horizontalmente

def crear_boton(texto, color, comando):
    return tk.Button(frame_botones_centro, text=texto, bg=color, fg="white",
                     font=("Arial", 11, "bold"), width=18, height=2, command=comando)

# Botones centrados
crear_boton("🎥 Encender Cámara", "#4CAF50", lambda: iniciar_camara()).pack(side=tk.LEFT, padx=10)
crear_boton("🛑 Detener Cámara", "#f44336", lambda: detener_camara()).pack(side=tk.LEFT, padx=10)
crear_boton("➕ Agregar Placa", "#2196F3", lambda: abrir_ventana_agregar_placa()).pack(side=tk.LEFT, padx=10)
crear_boton("❌ Cerrar", "#9E9E9E", lambda: cerrar()).pack(side=tk.LEFT, padx=10)

# === FRAME PARA PESTAÑAS DE TABLAS ===
frame_tabs = tk.Frame(root, bg="#f0f0f0")
frame_tabs.pack(side=tk.TOP, pady=15, fill="both", expand=True)

# === BOTONES PARA CAMBIAR TABLAS ===
tab_buttons_frame = tk.Frame(frame_tabs, bg="#f0f0f0")
tab_buttons_frame.pack(pady=5)

btn_tab_reg = tk.Button(tab_buttons_frame, text="📋 Placas Registradas",
                        bg="#2196F3", fg="white", font=("Arial", 11, "bold"),
                        width=20, command=lambda: mostrar_tab("reg"))
btn_tab_reg.pack(side=tk.LEFT, padx=10)

btn_tab_mov = tk.Button(tab_buttons_frame, text="🚗 Entradas / Salidas",
                        bg="#FF9800", fg="white", font=("Arial", 11, "bold"),
                        width=20, command=lambda: mostrar_tab("mov"))
btn_tab_mov.pack(side=tk.LEFT, padx=10)

# === CONTENEDORES DE TABLAS ===
frame_reg = tk.Frame(frame_tabs, bg="#f0f0f0")
frame_mov = tk.Frame(frame_tabs, bg="#f0f0f0")

# === TABLA 1: PLACAS REGISTRADAS ===
cols_reg = ("Placa", "Propietario")
tree_reg_scroll = tk.Scrollbar(frame_reg)
tree_reg_scroll.pack(side=tk.RIGHT, fill="y")

tree_reg = ttk.Treeview(frame_reg, columns=cols_reg, show="headings", height=12, yscrollcommand=tree_reg_scroll.set)
for col in cols_reg:
    tree_reg.heading(col, text=col)
    tree_reg.column(col, width=300, anchor="center")
tree_reg.pack(fill="both", expand=True, pady=5)
tree_reg_scroll.config(command=tree_reg.yview)


# === TABLA 2: ENTRADAS / SALIDAS ===
cols_mov = ("Placa", "Acción", "Fecha", "Monto")
tree_mov_scroll = tk.Scrollbar(frame_mov)
tree_mov_scroll.pack(side=tk.RIGHT, fill="y")

tree_mov = ttk.Treeview(frame_mov, columns=cols_mov, show="headings", height=12, yscrollcommand=tree_mov_scroll.set)
for col in cols_mov:
    tree_mov.heading(col, text=col)
    tree_mov.column(col, width=220, anchor="center")
tree_mov.pack(fill="both", expand=True, pady=5)
tree_mov_scroll.config(command=tree_mov.yview)

# === MOSTRAR TABLA ACTUAL ===def mostrar_tab(tab):
def mostrar_tab(tab):
    for f in (frame_reg, frame_mov):
        f.pack_forget()
    if tab == "reg":
        frame_reg.pack(fill="both", expand=True)
        actualizar_tabla_registradas()
    else:
        frame_mov.pack(fill="both", expand=True)
        actualizar_tabla_movimientos()

# === VARIABLES GLOBALES ===
cap = None
after_id = None
placas_en_proceso = set()
mostrando_mensaje = False

# === FUNCIONES DE CÁMARA ===
def iniciar_camara():
    global cap, after_id
    if cap is None:
        cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if not ret:
        messagebox.showerror("Error", "⚠️ No se pudo acceder a la cámara.")
        return

    placas = detectar_placas(frame)
    for placa, (x1, y1, x2, y2) in placas:
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,0), 2)
        cv2.putText(frame, placa, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

        if db.puede_procesar_placa(placa) and placa not in placas_en_proceso:
            placas_en_proceso.add(placa)
            threading.Thread(target=procesar_placa_async, args=(placa,), daemon=True).start()

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = ImageTk.PhotoImage(Image.fromarray(frame_rgb))
    lmain.imgtk = img
    lmain.configure(image=img)
    after_id = lmain.after(30, iniciar_camara)

def detener_camara():
    global cap, after_id
    if after_id:
        lmain.after_cancel(after_id)
        after_id = None
    if cap:
        cap.release()
        cap = None
    lmain.configure(image="", bg="black")

# === FUNCIONES DE PROCESAMIENTO EN HILO ===
# === CONTROL GLOBAL ===
mostrando_mensaje = False  # 🔒 bloquea procesamiento durante el mensaje


def procesar_placa_async(placa):
    """Procesa la placa en un hilo separado para no trabar la GUI"""
    global mostrando_mensaje

    # Si hay un mensaje abierto, no procesar nuevas placas
    if mostrando_mensaje:
        return

    try:
        if db.esta_registrada(placa):
            resultado = db.registrar_salida(placa)

            if resultado is None:
                # Registrar entrada
                db.registrar_entrada(placa)
                root.after(0, lambda: mostrar_info(
                    f"Placa {placa} registrada como ENTRADA.", "Visto Bueno ✅"
                ))
                root.after(0, lambda: tree_mov.insert(
                    "", "end",
                    values=(placa, "ENTRADA",
                            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "-")
                ))
            else:
                # Registrar salida
                monto = resultado['monto']
                duracion = round(resultado['segundos'] / 60, 1)
                root.after(0, lambda: mostrar_info(
                    f"Placa: {placa}\nTiempo: {duracion} min\nMonto: S/{monto}",
                    "Salida Registrada 💵"
                ))
                root.after(0, lambda: tree_mov.insert(
                    "", "end",
                    values=(placa, "SALIDA",
                            resultado['salida'].strftime("%Y-%m-%d %H:%M:%S"),
                            f"S/{monto:.2f}")
                ))

            root.after(0, actualizar_tabla_registradas)

        else:
            root.after(0, lambda: mostrar_advertencia(
                f"La placa {placa} no está registrada."))
    finally:
        # Permite volver a procesar la placa después de unos segundos
        root.after(5000, lambda: placas_en_proceso.discard(placa))


# === FUNCIONES DE MENSAJE (bloqueo total de procesamiento) ===
def mostrar_info(msg, titulo="Info"):
    global mostrando_mensaje
    mostrando_mensaje = True
    messagebox.showinfo(titulo, msg)
    mostrando_mensaje = False


def mostrar_advertencia(msg):
    global mostrando_mensaje
    mostrando_mensaje = True
    messagebox.showwarning("No Autorizado ⛔", msg)
    mostrando_mensaje = False


# === FUNCIONES DE INTERFAZ ===
def abrir_ventana_agregar_placa():
    ventana = tk.Toplevel(root)
    ventana.title("Registrar Nueva Placa Autorizada")
    ventana.geometry("400x250")
    ventana.config(bg="#f9f9f9")

    tk.Label(ventana, text="Placa:", font=("Arial", 12), bg="#f9f9f9").pack(pady=5)
    entry_placa = tk.Entry(ventana, font=("Arial", 12))
    entry_placa.pack(pady=5)

    tk.Label(ventana, text="Propietario:", font=("Arial", 12), bg="#f9f9f9").pack(pady=5)
    entry_prop = tk.Entry(ventana, font=("Arial", 12))
    entry_prop.pack(pady=5)

    def guardar():
        placa = entry_placa.get().strip().upper()
        prop = entry_prop.get().strip()
        if not placa:
            messagebox.showwarning("Error", "Debe ingresar una placa.")
            return
        db.registrar_autorizada(placa, prop)
        messagebox.showinfo("Guardado ✅", f"Placa {placa} registrada correctamente.")
        ventana.destroy()
        actualizar_tabla_registradas()

    tk.Button(ventana, text="Guardar", bg="#4CAF50", fg="white", command=guardar, width=12).pack(pady=10)
    tk.Button(ventana, text="Cancelar", command=ventana.destroy, width=12).pack()

def actualizar_tabla_registradas():
    """Actualiza la tabla de placas registradas sin mostrar columna 'Activo'."""
    for row in tree_reg.get_children():
        tree_reg.delete(row)

    data = db.obtener_registradas()
    for p in data:
        # Asumiendo que el orden es: id, placa, propietario, activo
        tree_reg.insert("", "end", values=(p[1], p[2]))

        

def actualizar_tabla_movimientos():
    """Muestra tanto las entradas como las salidas registradas en la base de datos."""
    for row in tree_mov.get_children():
        tree_mov.delete(row)

    data = db.obtener_movimientos()
    for fila in data:
        placa = fila["placa"]
        entrada_ts = fila["entrada_ts"]
        salida_ts = fila["salida_ts"]
        monto = fila["monto"]
        procesada = int(fila["procesada"])

        # Siempre mostrar la ENTRADA
        if entrada_ts:
            tree_mov.insert("", "end", values=(
                placa,
                "ENTRADA",
                entrada_ts.strftime("%Y-%m-%d %H:%M:%S"),
                "-"
            ))

        # Si hay salida registrada, mostrar también la SALIDA
        if procesada == 1 and salida_ts:
            tree_mov.insert("", "end", values=(
                placa,
                "SALIDA",
                salida_ts.strftime("%Y-%m-%d %H:%M:%S"),
                f"S/{float(monto):.2f}"
            ))

def cerrar():
    detener_camara()
    root.destroy()

# === INICIALIZACIÓN ===

db.registrar_autorizada("ABC-123", "Juan Pérez")
mostrar_tab("reg")

root.mainloop()

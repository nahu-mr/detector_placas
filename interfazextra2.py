import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import cv2
import datetime
from db import (
    inicializar_tablas,
    esta_registrada,
    registrar_entrada,
    registrar_salida,
    registrar_autorizada,
    puede_procesar_placa,
    obtener_registradas
)
from detector import detectar_placas

# === CONFIGURACIÓN DE VENTANA ===
root = tk.Tk()
root.title("Sistema de Control Vehicular - Perú")
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

def crear_boton(texto, color, comando):
    return tk.Button(frame_botones, text=texto, bg=color, fg="white",
                     font=("Arial", 11, "bold"), width=18, height=2, command=comando)

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

# === TABLA 1: PLACAS REGISTRADAS (con scroll) ===
cols_reg = ("Placa", "Propietario", "Activo")
tree_reg_scroll = tk.Scrollbar(frame_reg)
tree_reg_scroll.pack(side=tk.RIGHT, fill="y")

tree_reg = ttk.Treeview(frame_reg, columns=cols_reg, show="headings", height=12, yscrollcommand=tree_reg_scroll.set)
for col in cols_reg:
    tree_reg.heading(col, text=col)
    tree_reg.column(col, width=250, anchor="center")
tree_reg.pack(fill="both", expand=True, pady=5)
tree_reg_scroll.config(command=tree_reg.yview)

# === TABLA 2: ENTRADAS / SALIDAS (con scroll) ===
cols_mov = ("Placa", "Acción", "Fecha", "Monto")
tree_mov_scroll = tk.Scrollbar(frame_mov)
tree_mov_scroll.pack(side=tk.RIGHT, fill="y")

tree_mov = ttk.Treeview(frame_mov, columns=cols_mov, show="headings", height=12, yscrollcommand=tree_mov_scroll.set)
for col in cols_mov:
    tree_mov.heading(col, text=col)
    tree_mov.column(col, width=220, anchor="center")
tree_mov.pack(fill="both", expand=True, pady=5)
tree_mov_scroll.config(command=tree_mov.yview)

# === MOSTRAR TABLA ACTUAL ===
def mostrar_tab(tab):
    for f in (frame_reg, frame_mov):
        f.pack_forget()
    if tab == "reg":
        frame_reg.pack(fill="both", expand=True)
        actualizar_tabla_registradas()
    else:
        frame_mov.pack(fill="both", expand=True)

# === FUNCIONES DE CÁMARA ===
cap = None
after_id = None


def iniciar_camara():
    global cap, after_id, detected_last
    if cap is None:
        cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if not ret:
        messagebox.showerror("Error", "⚠️ No se pudo acceder a la cámara.")
        return

    placas = detectar_placas(frame)
    for placa, (x1, y1, x2, y2) in placas:
        # Dibuja rectángulo verde persistente
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,0), 2)
        cv2.putText(frame, placa, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
        if puede_procesar_placa(placa):
            procesar_placa(placa)
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

# === FUNCIONES DE PROCESAMIENTO ===
def procesar_placa(placa):
    if esta_registrada(placa):
        resultado = registrar_salida(placa)
        if resultado is None:
            registrar_entrada(placa)
            messagebox.showinfo("Visto Bueno ✅", f"Placa {placa} registrada como ENTRADA.")
            tree_mov.insert("", "end", values=(placa, "ENTRADA",
                             datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "-"))
        else:
            monto = resultado['monto']
            duracion = round(resultado['segundos']/60, 1)
            messagebox.showinfo("Salida Registrada 💵",
                                f"Placa: {placa}\nTiempo: {duracion} min\nMonto: S/{monto}")
            tree_mov.insert("", "end", values=(placa, "SALIDA",
                             resultado['salida'].strftime("%Y-%m-%d %H:%M:%S"), f"S/{monto:.2f}"))
        actualizar_tabla_registradas()
    else:
        messagebox.showwarning("No Autorizado ⛔", f"La placa {placa} no está registrada.")

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
        registrar_autorizada(placa, prop)
        messagebox.showinfo("Guardado ✅", f"Placa {placa} registrada correctamente.")
        ventana.destroy()
        actualizar_tabla_registradas()

    tk.Button(ventana, text="Guardar", bg="#4CAF50", fg="white", command=guardar, width=12).pack(pady=10)
    tk.Button(ventana, text="Cancelar", command=ventana.destroy, width=12).pack()

def actualizar_tabla_registradas():
    """Actualiza la tabla de placas registradas"""
    for row in tree_reg.get_children():
        tree_reg.delete(row)
    data = obtener_registradas()
    for p in data:
        estado = "✅" if p[3] == 1 else "❌"
        tree_reg.insert("", "end", values=(p[1], p[2], estado))

def cerrar():
    detener_camara()
    root.destroy()

# === INICIALIZAR BD ===
inicializar_tablas()
registrar_autorizada("ABC-123", "Juan Pérez")
mostrar_tab("reg")  # inicia mostrando las placas registradas

root.mainloop()

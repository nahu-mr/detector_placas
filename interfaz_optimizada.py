import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import cv2
import datetime
import threading
import db
from db import (
    inicializar_tablas, esta_registrada, registrar_entrada,
    registrar_salida, registrar_autorizada, puede_procesar_placa,
    obtener_registradas, obtener_movimientos
)
from detector import detectar_placas

# ===============================
# CONFIGURACIÓN DE LA VENTANA
# ===============================
root = tk.Tk()
root.title("PlateMind Sistema de Control Vehicular - Perú")
root.geometry("1350x900")
root.configure(bg="#f4f5f7")

# ===============================
# PALETA DE COLORES (MODO CLARO)
# ===============================
COLOR_FONDO = "#f4f5f7"          # Fondo principal
COLOR_PANEL = "#ffffff"          # Panel lateral / barra superior
COLOR_BOTON = "#0078D7"          # Azul profesional
COLOR_BOTON_HOVER = "#339CFF"    # Azul más claro al pasar el mouse
COLOR_TEXTO = "#222222"          # Texto principal oscuro
COLOR_TEXTO_SEC = "#555555"      # Texto secundario
COLOR_ACCENTO = "#0078D7"        # Azul de acento
COLOR_TABLA_FONDO = "#ffffff"    # Fondo tabla
COLOR_TABLA_FILAS = "#f0f0f0"    # Filas alternas
COLOR_SCROLL = "#e0e0e0"         # Scroll claro
COLOR_INPUT_BG = "#f9f9f9"

FUENTE = ("Segoe UI", 12)
FUENTE_TITULO = ("Segoe UI Semibold", 16)

# ===============================
# VARIABLES GLOBALES
# ===============================
cap = None
after_id = None
placas_en_proceso = set()
bloqueado = False

# ===============================
# BARRA SUPERIOR
# ===============================
barra_superior = tk.Frame(root, bg=COLOR_PANEL, height=60)
barra_superior.pack(side=tk.TOP, fill="x")

titulo_lbl = tk.Label(
    barra_superior, text="PlateMind - SISTEMA DE CONTROL VEHICULAR - Perú",
    bg=COLOR_PANEL, fg=COLOR_TEXTO, font=FUENTE_TITULO
)
titulo_lbl.pack(side=tk.LEFT, padx=20)

hora_lbl = tk.Label(barra_superior, bg=COLOR_PANEL, fg=COLOR_ACCENTO, font=("Consolas", 14))
hora_lbl.pack(side=tk.RIGHT, padx=20)

def actualizar_hora():
    ahora = datetime.datetime.now().strftime("%H:%M:%S")
    hora_lbl.config(text=ahora)
    root.after(1000, actualizar_hora)
actualizar_hora()

# ===============================
# PANELES PRINCIPALES
# ===============================
panel_izquierdo = tk.Frame(root, bg=COLOR_PANEL, width=250)
panel_izquierdo.pack(side=tk.LEFT, fill="y")

panel_derecho = tk.Frame(root, bg=COLOR_FONDO)
panel_derecho.pack(side=tk.RIGHT, fill="both", expand=True)

# ===============================
# BOTONES DE MENÚ
# ===============================
def crear_boton(texto, comando):
    boton_frame = tk.Frame(panel_izquierdo, bg=COLOR_PANEL)
    boton_frame.pack(fill="x", pady=6, padx=15)
    boton = tk.Button(
        boton_frame,
        text=texto,
        bg=COLOR_BOTON,
        fg="white",
        font=("Segoe UI", 12, "bold"),
        relief="flat",
        bd=0,
        height=2,
        cursor="hand2",
        command=comando
    )
    boton.pack(fill="x", expand=True, padx=5, pady=2)
    boton.bind("<Enter>", lambda e: boton.config(bg=COLOR_BOTON_HOVER))
    boton.bind("<Leave>", lambda e: boton.config(bg=COLOR_BOTON))
    boton.config(highlightthickness=0, overrelief="ridge")
    return boton

tk.Label(
    panel_izquierdo,
    text="MENÚ PRINCIPAL",
    bg=COLOR_PANEL,
    fg=COLOR_TEXTO,
    font=FUENTE_TITULO
).pack(pady=(25, 15))

crear_boton("Encender Cámara", lambda: mostrar_seccion("cam"))
crear_boton("Agregar Placa", lambda: abrir_ventana_agregar_placa())
crear_boton("Placas Registradas", lambda: mostrar_seccion("reg"))
crear_boton("Entradas / Salidas", lambda: mostrar_seccion("mov"))
crear_boton("Detener Cámara", lambda: detener_camara())
crear_boton("Eliminar Movimientos", lambda: eliminar_todos_movimientos())
crear_boton("Eliminar Usuario", lambda: eliminar_usuario())
crear_boton("Salir del Sistema", lambda: cerrar())

# ===============================
# FRAMES DE CONTENIDO
# ===============================
frame_camara = tk.Frame(panel_derecho, bg="#ffffff", bd=6, relief="ridge")
frame_reg = tk.Frame(panel_derecho, bg="#ffffff")
frame_mov = tk.Frame(panel_derecho, bg="#ffffff")

lmain = tk.Label(frame_camara, bg="#ffffff")
lmain.pack(fill="both", expand=True)

# ===============================
# IMAGEN INICIAL
# ===============================
def mostrar_imagen_inicial(event=None):
    global img_inicio_tk
    try:
        img = Image.open("imagen.png")
        w_frame, h_frame = frame_camara.winfo_width(), frame_camara.winfo_height()
        if w_frame < 10 or h_frame < 10:
            return
        iw, ih = img.size
        ratio_img = iw / ih
        ratio_frame = w_frame / h_frame
        if ratio_img > ratio_frame:
            new_w = w_frame
            new_h = int(w_frame / ratio_img)
        else:
            new_h = h_frame
            new_w = int(h_frame * ratio_img)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        fondo = Image.new("RGB", (w_frame, h_frame), "#ffffff")
        offset = ((w_frame - new_w) // 2, (h_frame - new_h) // 2)
        fondo.paste(img, offset)
        img_inicio_tk = ImageTk.PhotoImage(fondo)
        lmain.config(image=img_inicio_tk, bg="#ffffff")
        lmain.image = img_inicio_tk
    except:
        lmain.config(image="", bg="#ffffff")

frame_camara.bind("<Configure>", mostrar_imagen_inicial)

# ===============================
# ESTILO DE TABLAS (MODO CLARO)
# ===============================
style = ttk.Style()
style.theme_use("clam")

style.configure(
    "Treeview",
    background=COLOR_TABLA_FONDO,
    foreground=COLOR_TEXTO,
    rowheight=30,
    fieldbackground=COLOR_TABLA_FONDO,
    font=("Segoe UI", 12)
)
style.configure(
    "Treeview.Heading",
    background=COLOR_BOTON,
    foreground="white",
    font=("Segoe UI Semibold", 12)
)
style.map("Treeview", background=[("selected", COLOR_BOTON_HOVER)])

style.configure("Vertical.TScrollbar",
                troughcolor=COLOR_SCROLL,
                background="#b0b0b0",
                bordercolor="#e0e0e0")

# ===============================
# TABLAS
# ===============================
cols_reg = ("Placa", "Propietario", "Activo")
tree_reg_scroll = tk.Scrollbar(frame_reg, bg=COLOR_SCROLL)
tree_reg_scroll.pack(side=tk.RIGHT, fill="y")
tree_reg = ttk.Treeview(frame_reg, columns=cols_reg, show="headings", yscrollcommand=tree_reg_scroll.set)
for col in cols_reg:
    tree_reg.heading(col, text=col)
    tree_reg.column(col, anchor="center", width=250)
tree_reg.pack(fill="both", expand=True, pady=10)
tree_reg_scroll.config(command=tree_reg.yview)

cols_mov = ("Placa", "Acción", "Fecha", "Monto")
tree_mov_scroll = tk.Scrollbar(frame_mov, bg=COLOR_SCROLL)
tree_mov_scroll.pack(side=tk.RIGHT, fill="y")
tree_mov = ttk.Treeview(frame_mov, columns=cols_mov, show="headings", yscrollcommand=tree_mov_scroll.set)
for col in cols_mov:
    tree_mov.heading(col, text=col)
    tree_mov.column(col, anchor="center", width=230)
tree_mov.pack(fill="both", expand=True, pady=10)
tree_mov_scroll.config(command=tree_mov.yview)

# ===============================
# FUNCIONES DE INTERFAZ
# ===============================
def ocultar_todos_frames():
    for f in (frame_camara, frame_reg, frame_mov):
        f.pack_forget()

def mostrar_seccion(seccion):
    detener_camara()
    ocultar_todos_frames()
    if seccion == "cam":
        frame_camara.pack(fill="both", expand=True, padx=15, pady=15)
        iniciar_camara()
    elif seccion == "reg":
        frame_reg.pack(fill="both", expand=True, padx=15, pady=15)
        actualizar_tabla_registradas()
    elif seccion == "mov":
        frame_mov.pack(fill="both", expand=True, padx=15, pady=15)
        actualizar_tabla_movimientos()

# ===============================
# CÁMARA Y PROCESAMIENTO
# ===============================
def iniciar_camara():
    global cap, after_id
    if cap is None:
        cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if not ret:
        messagebox.showerror("Error", "No se pudo acceder a la cámara.")
        return

    placas = detectar_placas(frame)
    if not bloqueado:
        for placa, (x1, y1, x2, y2) in placas:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255,0), 2)
            cv2.putText(frame, placa, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255,0), 2)
            if puede_procesar_placa(placa) and placa not in placas_en_proceso:
                placas_en_proceso.add(placa)
                threading.Thread(target=procesar_placa_async, args=(placa,), daemon=True).start()

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w = frame_rgb.shape[:2]
    w_frame, h_frame = frame_camara.winfo_width(), frame_camara.winfo_height()
    if w_frame < 10 or h_frame < 10:
        w_frame, h_frame = 640, 480

    ratio_img = w / h
    ratio_frame = w_frame / h_frame
    if ratio_img > ratio_frame:
        new_w = w_frame
        new_h = int(w_frame / ratio_img)
    else:
        new_h = h_frame
        new_w = int(h_frame * ratio_img)

    resized = cv2.resize(frame_rgb, (new_w, new_h))
    fondo = Image.new("RGB", (w_frame, h_frame), "#ffffff")
    offset = ((w_frame - new_w) // 2, (h_frame - new_h) // 2)
    fondo.paste(Image.fromarray(resized), offset)

    img = ImageTk.PhotoImage(fondo)
    lmain.imgtk = img
    lmain.configure(image=img, bg="#ffffff")
    after_id = lmain.after(30, iniciar_camara)

def detener_camara():
    global cap, after_id
    if after_id:
        lmain.after_cancel(after_id)
        after_id = None
    if cap:
        cap.release()
        cap = None
    mostrar_imagen_inicial()

# ===============================
# PROCESAMIENTO DE PLACAS
# ===============================
def procesar_placa_async(placa):
    global bloqueado
    bloqueado = True
    try:
        if esta_registrada(placa):
            resultado = registrar_salida(placa)
            if resultado is None:
                registrar_entrada(placa)
                root.after(0, lambda: mostrar_info(f"Placa {placa} registrada como ENTRADA.", "Entrada ✅"))
            else:
                monto = resultado["monto"]
                duracion = round(resultado["segundos"]/60, 1)
                root.after(0, lambda: mostrar_info(f"Placa: {placa}\nTiempo: {duracion} min\nMonto: S/{monto}", "Salida 💵"))
        else:
            root.after(0, lambda: mostrar_advertencia(f"La placa {placa} no está registrada."))
    finally:
        root.after(5000, lambda: placas_en_proceso.discard(placa))
        bloqueado = False

# ===============================
# FUNCIONES DE GESTIÓN
# ===============================
def abrir_ventana_agregar_placa():
    ocultar_todos_frames()
    ventana = tk.Toplevel(root)
    ventana.title("Registrar Nueva Placa Autorizada")
    ventana.geometry("600x300")
    ventana.config(bg=COLOR_PANEL)

    tk.Label(ventana, text="Placa:", font=("Segoe UI", 13), bg=COLOR_PANEL, fg=COLOR_TEXTO).pack(pady=8)
    entry_placa = tk.Entry(ventana, font=("Segoe UI", 13), bg=COLOR_INPUT_BG, fg=COLOR_TEXTO, insertbackground=COLOR_TEXTO)
    entry_placa.pack(pady=4, ipadx=5, ipady=5)

    tk.Label(ventana, text="Propietario:", font=("Segoe UI", 13), bg=COLOR_PANEL, fg=COLOR_TEXTO).pack(pady=8)
    entry_prop = tk.Entry(ventana, font=("Segoe UI", 13), bg=COLOR_INPUT_BG, fg=COLOR_TEXTO, insertbackground=COLOR_TEXTO)
    entry_prop.pack(pady=4, ipadx=5, ipady=5)

    def guardar():
        placa = entry_placa.get().strip().upper()
        prop = entry_prop.get().strip()
        if not placa:
            messagebox.showwarning("Error", "Debe ingresar una placa.")
            return
        registrar_autorizada(placa, prop)
        messagebox.showinfo("Guardado ✅", f"Placa {placa} registrada correctamente.")
        ventana.destroy()
        mostrar_seccion("reg")

    tk.Button(ventana, text="Guardar", bg=COLOR_BOTON, fg="white", font=("Segoe UI", 12, "bold"), command=guardar, width=12).pack(pady=10)
    tk.Button(ventana, text="Cancelar", font=("Segoe UI", 12), command=lambda: [ventana.destroy(), mostrar_seccion("reg")], width=12).pack()

def eliminar_todos_movimientos():
    ocultar_todos_frames()
    if messagebox.askyesno("Confirmar", "¿Seguro que deseas eliminar todos los movimientos registrados?"):
        try:
            conn = db.conectar_db()
            cur = conn.cursor()
            cur.execute("DELETE FROM entradas")
            conn.commit()
            cur.close(); conn.close()
            messagebox.showinfo("Éxito", "✅ Todos los movimientos han sido eliminados correctamente.")
            mostrar_seccion("mov")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron eliminar los movimientos:\n{e}")
    else:
        mostrar_seccion("mov")

def eliminar_usuario():
    ocultar_todos_frames()
    ventana = tk.Toplevel(root)
    ventana.title("Eliminar Usuario")
    ventana.geometry("400x200")
    ventana.configure(bg=COLOR_PANEL)

    tk.Label(ventana, text="Ingrese la placa del usuario a eliminar:", bg=COLOR_PANEL, fg=COLOR_TEXTO, font=("Segoe UI", 13)).pack(pady=10)
    placa_entry = tk.Entry(ventana, width=25, bg=COLOR_INPUT_BG, fg=COLOR_TEXTO, insertbackground=COLOR_TEXTO, font=("Segoe UI", 12))
    placa_entry.pack(pady=5)

    def confirmar_eliminacion():
        placa = placa_entry.get().strip().upper()
        if not placa:
            messagebox.showwarning("Advertencia", "Debe ingresar una placa válida.")
            return
        try:
            conn = db.conectar_db()
            cur = conn.cursor()
            cur.execute("DELETE FROM registradas WHERE placa = %s", (placa,))
            conn.commit()
            if cur.rowcount > 0:
                messagebox.showinfo("Éxito", f"✅ El usuario con placa {placa} fue eliminado.")
            else:
                messagebox.showwarning("Aviso", f"No se encontró ningún usuario con la placa {placa}.")
            cur.close(); conn.close()
            ventana.destroy()
            mostrar_seccion("reg")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar el usuario:\n{e}")

    tk.Button(ventana, text="Eliminar", bg="#E03A3E", fg="white", font=("Segoe UI", 12, "bold"), command=confirmar_eliminacion, width=12).pack(pady=10)
    tk.Button(ventana, text="Cancelar", font=("Segoe UI", 12), command=lambda: [ventana.destroy(), mostrar_seccion("reg")], width=12).pack()

# ===============================
# ACTUALIZACIÓN DE TABLAS
# ===============================
def actualizar_tabla_registradas():
    for row in tree_reg.get_children():
        tree_reg.delete(row)
    for p in obtener_registradas():
        estado = "✅" if p[3] == 1 else "❌"
        tree_reg.insert("", "end", values=(p[1], p[2], estado))

def actualizar_tabla_movimientos():
    for row in tree_mov.get_children():
        tree_mov.delete(row)
    for fila in obtener_movimientos():
        placa = fila["placa"]
        entrada_ts = fila["entrada_ts"]
        salida_ts = fila["salida_ts"]
        monto = fila["monto"]
        procesada = int(fila["procesada"])
        if entrada_ts:
            tree_mov.insert("", "end", values=(placa, "ENTRADA", entrada_ts.strftime("%Y-%m-%d %H:%M:%S"), "-"))
        if procesada == 1 and salida_ts:
            tree_mov.insert("", "end", values=(placa, "SALIDA", salida_ts.strftime("%Y-%m-%d %H:%M:%S"), f"S/{float(monto):.2f}"))

# ===============================
# FUNCIONES DE MENSAJE
# ===============================
def mostrar_info(mensaje, titulo="Información"):
    messagebox.showinfo(titulo, mensaje)

def mostrar_advertencia(mensaje):
    messagebox.showwarning("Advertencia", mensaje)

def cerrar():
    detener_camara()
    root.destroy()

# ===============================
# INICIALIZAR BD Y MOSTRAR
# ===============================
inicializar_tablas()
ocultar_todos_frames()        # Oculta los otros frames
frame_camara.pack(fill="both", expand=True, padx=15, pady=15)  # Muestra el frame principal
root.after(100, mostrar_imagen_inicial)  # Muestra la imagen apenas carga la ventana
root.mainloop()

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import cv2
import datetime
import threading
import time
import db
from db import (
    esta_registrada, registrar_entrada,
    registrar_salida, registrar_autorizada, puede_procesar_placa,
    obtener_registradas, obtener_movimientos
)
from detector import detectar_placas

# CONFIGURACIÓN DE LA VENTANA
root = tk.Tk()
root.title("PlateMind - Sistema de Control Vehicular")
root.geometry("1400x900")
root.configure(bg="#1a1a2e")
root.state('zoomed')  # Pantalla completa en Windows
# ===============================
# PALETA DE COLORES (CLARA – PROFESIONAL)
# ===============================

COLOR_FONDO = "#F7F7F7"           # Gris muy claro - Fondo principal
COLOR_PANEL = "#FFFFFF"          # Blanco limpio - Panel lateral / tarjetas
COLOR_BOTON = "#D9B44A"           # Dorado suave / amarillo elegante
COLOR_BOTON_HOVER = "#E6C866"     # Dorado claro - Hover
COLOR_TEXTO = "#2E2E2E"           # Gris oscuro suave (no negro)
COLOR_TEXTO_SEC = "#7A7A7A"       # Gris medio - Texto secundario
COLOR_ACCENTO = "#0f4c75"        # Acento dorado
COLOR_EXITO = "#6BBF59"           # Verde claro - Éxito
COLOR_PELIGRO = "#E57373"         # Rojo suave - Peligro
COLOR_ADVERTENCIA = "#F2B705"     # Amarillo advertencia
COLOR_GRIS_OSCURO = "#4A4A4A"     # Gris medio (NO oscuro fuerte)
COLOR_BORDE = "#E0E0E0"           # Gris claro - Bordes

FUENTE = ("Segoe UI", 11)
FUENTE_TITULO = ("Segoe UI", 18, "bold")
FUENTE_SUBTITULO = ("Segoe UI", 14, "bold")

# ===============================
# VARIABLES GLOBALES
# ===============================
cap = None
after_id = None
placas_en_proceso = {}
bloqueado = False
mostrando_mensaje = False
lock_procesamiento = threading.Lock()

# ===============================
# BARRA SUPERIOR CON GRADIENTE
# ===============================

COLO_AZUL = "#0f4c75"
barra_superior = tk.Frame(root, bg=COLOR_ACCENTO, height=80)
barra_superior.pack(side=tk.TOP, fill="x")
barra_superior.pack_propagate(False)

# Logo y título
frame_titulo = tk.Frame(barra_superior, bg=COLOR_ACCENTO)
frame_titulo.pack(side=tk.LEFT, padx=30, pady=15)

titulo_principal = tk.Label(
    frame_titulo, 
    text="🚗 PLATEMIND", 
    bg=COLOR_ACCENTO, 
    fg="#FFFFFF", 
    font=("Segoe UI", 24, "bold")
)
titulo_principal.pack(anchor="w")

subtitulo = tk.Label(
    frame_titulo, 
    text="Sistema de Control Vehicular - Perú", 
    bg=COLOR_ACCENTO, 
    fg = "#FFFFFF", 
    font=("Segoe UI", 11)
)
subtitulo.pack(anchor="w")

# Panel de información derecha
frame_info_derecha = tk.Frame(barra_superior, bg=COLOR_ACCENTO)
frame_info_derecha.pack(side=tk.RIGHT, padx=30, pady=15)

fecha_lbl = tk.Label(
    frame_info_derecha, 
    bg=COLOR_ACCENTO, 
    fg = "#FFFFFF", 
    font=("Segoe UI", 10)
)
fecha_lbl.pack(anchor="e")

hora_lbl = tk.Label(
    frame_info_derecha, 
    bg= COLOR_ACCENTO, 
    fg="#FFFFFF", 
    font=("Consolas", 20, "bold")
)
hora_lbl.pack(anchor="e")

def actualizar_hora():
    ahora = datetime.datetime.now()
    hora_lbl.config(text=ahora.strftime("%H:%M:%S"))
    fecha_lbl.config(text=ahora.strftime("%A, %d de %B de %Y"))
    root.after(1000, actualizar_hora)
actualizar_hora()

# ===============================
# PANEL LATERAL MEJORADO
# ===============================
panel_izquierdo = tk.Frame(root, bg=COLOR_PANEL, width=280)
panel_izquierdo.pack(side=tk.LEFT, fill="y")
panel_izquierdo.pack_propagate(False)

# Título del menú
tk.Label(
    panel_izquierdo,
    text="MENÚ DE CONTROL",
    bg=COLOR_PANEL,
    fg="#2C2C2C",
    font=FUENTE_SUBTITULO
).pack(pady=(30, 10))

# Separador
separador = tk.Frame(panel_izquierdo, bg=COLOR_ACCENTO, height=2)
separador.pack(fill="x", padx=20, pady=(0, 20))

# ===============================
# BOTONES MODERNOS CON ICONOS
# ===============================
def crear_boton(texto, comando, icono=""):
    boton_frame = tk.Frame(panel_izquierdo, bg=COLOR_PANEL)
    boton_frame.pack(fill="x", pady=5, padx=20)
    
    boton = tk.Button(
        boton_frame,
        text=f"{icono}  {texto}",
        bg=COLOR_BOTON,
        fg=COLOR_TEXTO,
        font=("Segoe UI", 11, "bold"),
        relief="flat",
        bd=0,
        height=2,
        cursor="hand2",
        command=comando,
        anchor="w",
        padx=20
    )
    boton.pack(fill="x")
    
    def on_enter(e):
        boton.config(bg=COLOR_BOTON_HOVER)
    
    def on_leave(e):
        boton.config(bg=COLOR_BOTON)
    
    boton.bind("<Enter>", on_enter)
    boton.bind("<Leave>", on_leave)
    
    return boton

crear_boton("Encender Cámara", lambda: mostrar_seccion("cam"), "📹")
crear_boton("Agregar Placa", lambda: abrir_ventana_agregar_placa(), "➕")
crear_boton("Placas Registradas", lambda: mostrar_seccion("reg"), "📋")
crear_boton("Entradas / Salidas", lambda: mostrar_seccion("mov"), "📊")

# Separador
tk.Frame(panel_izquierdo, bg=COLOR_ACCENTO, height=1).pack(fill="x", padx=20, pady=20)

crear_boton("Detener Cámara", lambda: detener_camara(), "⏹")
crear_boton("Eliminar Movimientos", lambda: eliminar_todos_movimientos(), "🗑")
crear_boton("Eliminar Usuario", lambda: eliminar_usuario(), "❌")

# Botón de salir al final
frame_salir = tk.Frame(panel_izquierdo, bg=COLOR_PANEL)
frame_salir.pack(side=tk.BOTTOM, fill="x", pady=30, padx=20)

boton_salir = tk.Button(
    frame_salir,
    text="🚪  SALIR DEL SISTEMA",
    bg=COLOR_PELIGRO,
    fg=COLOR_TEXTO,
    font=("Segoe UI", 11, "bold"),
    relief="flat",
    bd=0,
    height=2,
    cursor="hand2",
    command=lambda: cerrar()
)
boton_salir.pack(fill="x")

def on_enter_salir(e):
    boton_salir.config(bg="#ff5252")

def on_leave_salir(e):
    boton_salir.config(bg=COLOR_PELIGRO)

boton_salir.bind("<Enter>", on_enter_salir)
boton_salir.bind("<Leave>", on_leave_salir)

# ===============================
# PANEL DERECHO (CONTENIDO)
# ===============================
panel_derecho = tk.Frame(root, bg=COLOR_FONDO)
panel_derecho.pack(side=tk.RIGHT, fill="both", expand=True)

# ===============================
# FRAMES DE CONTENIDO CON TARJETAS
# ===============================
frame_camara = tk.Frame(panel_derecho, bg=COLOR_PANEL, bd=0)
frame_reg = tk.Frame(panel_derecho, bg=COLOR_FONDO)
frame_mov = tk.Frame(panel_derecho, bg=COLOR_FONDO)

# Contenedor para la cámara con título
contenedor_camara = tk.Frame(frame_camara, bg=COLOR_PANEL)
contenedor_camara.pack(fill="both", expand=True, padx=30, pady=30)

titulo_camara = tk.Label(
    contenedor_camara,
    text="📹 CAMARA",
    bg=COLOR_PANEL,
    fg="#2C2C2C",
    font=FUENTE_SUBTITULO
)
titulo_camara.pack(pady=(0, 15))

# Frame para la imagen de la cámara
frame_video = tk.Frame(contenedor_camara, bg="#000000", relief="solid", bd=2)
frame_video.pack(fill="both", expand=True)

lmain = tk.Label(frame_video, bg="#000000")
lmain.pack(fill="both", expand=True, padx=5, pady=5)

# Estado de la cámara
estado_camara = tk.Label(
    contenedor_camara,
    text="● Estado: Cámara apagada",
    bg=COLOR_PANEL,
    fg=COLOR_ADVERTENCIA,
    font=("Segoe UI", 10)
)
estado_camara.pack(pady=(10, 0))

# ===============================
# IMAGEN INICIAL
# ===============================
def mostrar_imagen_inicial(event=None):
    global img_inicio_tk
    try:
        img = Image.open("imagen.png")
        w_frame = lmain.winfo_width()
        h_frame = lmain.winfo_height()
        
        if w_frame < 10 or h_frame < 10:
            w_frame, h_frame = 800, 600
        
        iw, ih = img.size
        ratio_img = iw / ih
        ratio_frame = w_frame / h_frame
        
        if ratio_img > ratio_frame:
            new_w = w_frame - 10
            new_h = int((w_frame - 10) / ratio_img)
        else:
            new_h = h_frame - 10
            new_w = int((h_frame - 10) * ratio_img)
        
        img = img.resize((new_w, new_h), Image.LANCZOS)
        img_inicio_tk = ImageTk.PhotoImage(img)
        lmain.config(image=img_inicio_tk, bg="#000000")
        lmain.image = img_inicio_tk
    except Exception as e:
        print(f"Error cargando imagen: {e}")
        lmain.config(image="", bg="#000000", text="PlateMind\nSistema Listo", 
                    fg=COLOR_EXITO, font=("Segoe UI", 24, "bold"))

frame_video.bind("<Configure>", mostrar_imagen_inicial)

style = ttk.Style()
style.theme_use("clam")

style.configure(
    "Treeview",
    background=COLOR_PANEL,
    foreground=COLOR_TEXTO,
    rowheight=35,
    fieldbackground=COLOR_PANEL,
    font=("Segoe UI", 11),
    borderwidth=0
)

style.configure(
    "Treeview.Heading",
    background=COLOR_ACCENTO,
    foreground="#FFFFFF",
    font=("Segoe UI", 12, "bold"),
    relief="flat"
)

style.map(
    "Treeview",
    background=[
        ("active", COLOR_BOTON), 
        ("selected", COLOR_BOTON)   
    ],
    foreground=[
        ("active", COLOR_TEXTO),
        ("selected", COLOR_TEXTO)
    ]
)


# ===============================
# TABLA PLACAS REGISTRADAS
# ===============================
contenedor_reg = tk.Frame(frame_reg, bg= COLOR_FONDO)
contenedor_reg.pack(fill="both", expand=True, padx=30, pady=30)

titulo_reg = tk.Label(
    contenedor_reg,
    text="📋 PLACAS AUTORIZADAS",
    bg=COLOR_FONDO,
    fg="#2C2C2C",
    font=FUENTE_SUBTITULO
)
titulo_reg.pack(pady=(0, 15))

frame_tabla_reg = tk.Frame(contenedor_reg, bg=COLOR_PANEL, relief="flat", bd=2)
frame_tabla_reg.pack(fill="both", expand=True)

cols_reg = ("Placa", "Propietario")
tree_reg_scroll = tk.Scrollbar(frame_tabla_reg)
tree_reg_scroll.pack(side=tk.RIGHT, fill="y")

tree_reg = ttk.Treeview(frame_tabla_reg, columns=cols_reg, show="headings", 
                        yscrollcommand=tree_reg_scroll.set)
tree_reg.heading("Placa", text="PLACA")
tree_reg.heading("Propietario", text="PROPIETARIO")
tree_reg.column("Placa", anchor="center", width=200)
tree_reg.column("Propietario", anchor="w", width=400)
tree_reg.pack(fill="both", expand=True, padx=5, pady=5)
tree_reg_scroll.config(command=tree_reg.yview)

# ===============================
# TABLA MOVIMIENTOS
# ===============================
contenedor_mov = tk.Frame(frame_mov, bg=COLOR_FONDO)
contenedor_mov.pack(fill="both", expand=True, padx=30, pady=30)

titulo_mov = tk.Label(
    contenedor_mov,
    text="📊 REGISTRO DE MOVIMIENTOS",
    bg=COLOR_FONDO,
    fg="#2C2C2C",
    font=FUENTE_SUBTITULO
)
titulo_mov.pack(pady=(0, 15))

frame_tabla_mov = tk.Frame(contenedor_mov, bg=COLOR_PANEL, relief="flat", bd=2)
frame_tabla_mov.pack(fill="both", expand=True)

cols_mov = ("Placa", "Acción", "Fecha", "Monto")
tree_mov_scroll = tk.Scrollbar(frame_tabla_mov)
tree_mov_scroll.pack(side=tk.RIGHT, fill="y")

tree_mov = ttk.Treeview(frame_tabla_mov, columns=cols_mov, show="headings",
                        yscrollcommand=tree_mov_scroll.set)
tree_mov.heading("Placa", text="PLACA")
tree_mov.heading("Acción", text="ACCIÓN")
tree_mov.heading("Fecha", text="FECHA Y HORA")
tree_mov.heading("Monto", text="MONTO")
tree_mov.column("Placa", anchor="center", width=150)
tree_mov.column("Acción", anchor="center", width=150)
tree_mov.column("Fecha", anchor="center", width=250)
tree_mov.column("Monto", anchor="center", width=150)
tree_mov.pack(fill="both", expand=True, padx=5, pady=5)
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
        frame_camara.pack(fill="both", expand=True)
        iniciar_camara()
    elif seccion == "reg":
        frame_reg.pack(fill="both", expand=True)
        actualizar_tabla_registradas()
    elif seccion == "mov":
        frame_mov.pack(fill="both", expand=True)
        actualizar_tabla_movimientos()

# ===============================
# LIMPIEZA DE PLACAS EN PROCESO
# ===============================
def limpiar_placas_antiguas():
    global placas_en_proceso
    tiempo_actual = time.time()
    placas_a_eliminar = []
    
    with lock_procesamiento:
        for placa, timestamp in placas_en_proceso.items():
            if tiempo_actual - timestamp > 5:
                placas_a_eliminar.append(placa)
        
        for placa in placas_a_eliminar:
            del placas_en_proceso[placa]
    
    root.after(2000, limpiar_placas_antiguas)

# ===============================
# CÁMARA Y PROCESAMIENTO
# ===============================
def iniciar_camara():
    global cap, after_id
    if cap is None:
        cap = cv2.VideoCapture(0)
        estado_camara.config(text="● Estado: Cámara activa", fg=COLOR_EXITO)
    
    ret, frame = cap.read()
    if not ret:
        messagebox.showerror("Error", "No se pudo acceder a la cámara.")
        estado_camara.config(text="● Estado: Error en cámara", fg=COLOR_PELIGRO)
        return

    placas = detectar_placas(frame)
    tiempo_actual = time.time()
    
    for placa, (x1, y1, x2, y2) in placas:
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 217, 255), 3)
        cv2.putText(frame, placa, (x1, y1 - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 217, 255), 3)

        with lock_procesamiento:
            puede_procesar = placa not in placas_en_proceso
            if puede_procesar:
                placas_en_proceso[placa] = tiempo_actual

        if puede_procesar and not mostrando_mensaje:
            threading.Thread(target=procesar_placa_async, args=(placa,), daemon=True).start()


    h_label = 860
    w_label = 1280

    if w_label > 10 and h_label > 10:
        frame = cv2.resize(frame, (w_label, h_label), interpolation=cv2.INTER_AREA)

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = ImageTk.PhotoImage(Image.fromarray(frame_rgb))
    lmain.imgtk = img
    lmain.configure(image=img)
    after_id = lmain.after(30, iniciar_camara)

def detener_camara():
    global cap, after_id, placas_en_proceso
    if after_id:
        lmain.after_cancel(after_id)
        after_id = None
    if cap:
        cap.release()
        cap = None
    with lock_procesamiento:
        placas_en_proceso.clear()
    estado_camara.config(text="● Estado: Cámara apagada", fg=COLOR_ADVERTENCIA)
    mostrar_imagen_inicial()

# ===============================
# PROCESAMIENTO DE PLACAS
# ===============================
def procesar_placa_async(placa):
    global mostrando_mensaje

    if mostrando_mensaje:
        return

    try:
        if not db.esta_registrada(placa):
            root.after(0, lambda: mostrar_advertencia(
                f"La placa {placa} no está registrada en el sistema."))
            return

        resultado = db.registrar_salida(placa)

        if resultado is None:
            db.registrar_entrada(placa)
            root.after(0, lambda: mostrar_info(
                f"✅ Placa: {placa}\n\nRegistrada como ENTRADA\n\nFecha: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", 
                "Entrada Registrada"
            ))
            root.after(0, lambda: tree_mov.insert(
                "", 0,
                values=(placa, "ENTRADA",
                        datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "-")
            ))
        else:
            monto = resultado['monto']
            duracion = round(resultado['segundos'] / 60, 1)
            root.after(0, lambda: mostrar_info(
                f"💰 COBRO GENERADO\n\nPlaca: {placa}\nTiempo: {duracion} minutos\nMonto: S/ {monto:.2f}", 
                "Salida Registrada"
            ))
            root.after(0, lambda: tree_mov.insert(
                "", 0,
                values=(placa, "SALIDA",
                        resultado['salida'].strftime("%d/%m/%Y %H:%M:%S"),
                        f"S/ {monto:.2f}")
            ))

        root.after(0, actualizar_tabla_registradas)

    except Exception as e:
        print(f"Error procesando placa {placa}: {e}")
        root.after(0, lambda: mostrar_advertencia(
            f"Error al procesar la placa {placa}"))

# ===============================
# FUNCIONES DE GESTIÓN
# ===============================
def abrir_ventana_agregar_placa():
    ocultar_todos_frames()
    ventana = tk.Toplevel(root)
    ventana.title("Registrar Nueva Placa")
    ventana.geometry("500x350")
    ventana.config(bg=COLOR_PANEL)
    ventana.resizable(False, False)
    ventana.update_idletasks()
    w = 500
    h = 350
    x = (ventana.winfo_screenwidth() // 2) - (w // 2)
    y = (ventana.winfo_screenheight() // 2) - (h // 2)
    ventana.geometry(f"{w}x{h}+{x}+{y}")
    # Centrar ventana
    ventana.transient(root)
    ventana.grab_set()

    tk.Label(
        ventana, 
        text="➕ REGISTRAR NUEVA PLACA", 
        font=FUENTE_SUBTITULO, 
        bg=COLOR_PANEL, 
        fg="#2C2C2C"
    ).pack(pady=20)

    tk.Label(ventana, text="Número de Placa:", font=FUENTE, bg=COLOR_PANEL, fg=COLOR_TEXTO).pack(pady=(15, 5))
    entry_placa = tk.Entry(
        ventana, 
        font=("Segoe UI", 13), 
        bg="#D9D9D9", 
        fg=COLOR_TEXTO, 
        insertbackground=COLOR_TEXTO,
        relief="flat",
        bd=5
    )
    entry_placa.pack(pady=5, ipadx=10, ipady=8)

    tk.Label(ventana, text="Propietario:", font=FUENTE, bg=COLOR_PANEL, fg=COLOR_TEXTO).pack(pady=(15, 5))
    entry_prop = tk.Entry(
        ventana, 
        font=("Segoe UI", 13), 
        bg="#D9D9D9", 
        fg=COLOR_TEXTO, 
        insertbackground=COLOR_TEXTO,
        relief="flat",
        bd=5
    )
    entry_prop.pack(pady=5, ipadx=10, ipady=8)

    def guardar():
        placa = entry_placa.get().strip().upper()
        prop = entry_prop.get().strip()
        if not placa:
            messagebox.showwarning("Advertencia", "Debe ingresar una placa válida.")
            return
        registrar_autorizada(placa, prop if prop else "Sin especificar")
        messagebox.showinfo("Éxito", f"✅ Placa {placa} registrada correctamente.")
        ventana.destroy()
        mostrar_seccion("reg")

    frame_botones = tk.Frame(ventana, bg=COLOR_PANEL)
    frame_botones.pack(pady=20)

    tk.Button(
        frame_botones, 
        text="💾 Guardar", 
        bg=COLOR_EXITO, 
        fg="#000000", 
        font=("Segoe UI", 11, "bold"), 
        command=guardar, 
        width=12,
        relief="flat",
        bd=0,
        cursor="hand2"
    ).pack(side=tk.LEFT, padx=5)
    
    tk.Button(
        frame_botones, 
        text="❌ Cancelar", 
        bg=COLOR_PELIGRO, 
        fg=COLOR_TEXTO, 
        font=("Segoe UI", 11, "bold"), 
        command=lambda: [ventana.destroy(), mostrar_seccion("reg")], 
        width=12,
        relief="flat",
        bd=0,
        cursor="hand2"
    ).pack(side=tk.LEFT, padx=5)

def eliminar_todos_movimientos():
    ocultar_todos_frames()
    if messagebox.askyesno("Confirmar", "⚠️ ¿Está seguro de eliminar TODOS los movimientos?\n\nEsta acción no se puede deshacer."):
        try:
            conn = db.conectar_db()
            cur = conn.cursor()
            cur.execute("DELETE FROM entradas")
            conn.commit()
            cur.close()
            conn.close()
            messagebox.showinfo("Éxito", "✅ Todos los movimientos han sido eliminados.")
            mostrar_seccion("mov")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron eliminar los movimientos:\n{e}")
    else:
        mostrar_seccion("mov")

def eliminar_usuario():
    ocultar_todos_frames()
    ventana = tk.Toplevel(root)
    ventana.title("Eliminar Usuario")
    ventana.geometry("450x250")
    ventana.configure(bg=COLOR_PANEL)
    ventana.resizable(False, False)
    ventana.update_idletasks()
    w = 500
    h = 350
    x = (ventana.winfo_screenwidth() // 2) - (w // 2)
    y = (ventana.winfo_screenheight() // 2) - (h // 2)
    ventana.geometry(f"{w}x{h}+{x}+{y}")
    
    ventana.transient(root)
    ventana.grab_set()

    tk.Label(
        ventana, 
        text="❌ ELIMINAR USUARIO", 
        bg=COLOR_PANEL, 
        fg=COLOR_PELIGRO, 
        font=FUENTE_SUBTITULO
    ).pack(pady=20)
    
    tk.Label(
        ventana, 
        text="Ingrese la placa del usuario:", 
        bg=COLOR_PANEL, 
        fg=COLOR_TEXTO, 
        font=FUENTE
    ).pack(pady=10)
    
    placa_entry = tk.Entry(
        ventana, 
        width=20, 
        bg="#D9D9D9", 
        fg=COLOR_TEXTO, 
        insertbackground=COLOR_TEXTO, 
        font=("Segoe UI", 13),
        relief="flat",
        bd=5
    )
    placa_entry.pack(pady=10, ipady=8)

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
                messagebox.showinfo("Éxito", f"✅ Usuario con placa {placa} eliminado.")
            else:
                messagebox.showwarning("Aviso", f"No se encontró la placa {placa}.")
            cur.close()
            conn.close()
            ventana.destroy()
            mostrar_seccion("reg")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar:\n{e}")

    frame_botones = tk.Frame(ventana, bg=COLOR_PANEL)
    frame_botones.pack(pady=15)

    tk.Button(
        frame_botones, 
        text="🗑 Eliminar", 
        bg=COLOR_PELIGRO, 
        fg=COLOR_TEXTO, 
        font=("Segoe UI", 11, "bold"), 
        command=confirmar_eliminacion, 
        width=12,
        relief="flat",
        bd=0,
        cursor="hand2"
    ).pack(side=tk.LEFT, padx=5)
    
    tk.Button(
        frame_botones, 
        text="Cancelar", 
        bg=COLOR_BOTON, 
        fg=COLOR_TEXTO, 
        font=("Segoe UI", 11, "bold"), 
        command=lambda: [ventana.destroy(), mostrar_seccion("reg")], 
        width=12,
        relief="flat",
        bd=0,
        cursor="hand2"
    ).pack(side=tk.LEFT, padx=5)

# ===============================
# ACTUALIZACIÓN DE TABLAS
# ===============================
def actualizar_tabla_registradas():
    for row in tree_reg.get_children():
        tree_reg.delete(row)

    data = db.obtener_registradas()
    for p in data:
        tree_reg.insert("", "end", values=(p[1], p[2]))

def actualizar_tabla_movimientos():
    for row in tree_mov.get_children():
        tree_mov.delete(row)
    for fila in db.obtener_movimientos():
        placa = fila["placa"]
        entrada_ts = fila["entrada_ts"]
        salida_ts = fila["salida_ts"]
        monto = fila["monto"]
        procesada = int(fila["procesada"])
        if entrada_ts:
            tree_mov.insert("", "end", values=(placa, "ENTRADA", entrada_ts.strftime("%d/%m/%Y %H:%M:%S"), "-"))
        if procesada == 1 and salida_ts:
            tree_mov.insert("", "end", values=(placa, "SALIDA", salida_ts.strftime("%d/%m/%Y %H:%M:%S"), f"S/ {float(monto):.2f}"))

def mostrar_info(msg, titulo="Información"):
    global mostrando_mensaje
    mostrando_mensaje = True
    messagebox.showinfo(titulo, msg)
    mostrando_mensaje = False

def mostrar_advertencia(msg):
    global mostrando_mensaje
    mostrando_mensaje = True
    messagebox.showwarning("⚠️ Advertencia", msg)
    mostrando_mensaje = False

def cerrar():
    if messagebox.askyesno("Confirmar Salida", "¿Está seguro que desea salir del sistema?"):
        detener_camara()
        root.destroy()

# ===============================
# INICIALIZAR
# ===============================
ocultar_todos_frames()
frame_camara.pack(fill="both", expand=True)
root.after(100, mostrar_imagen_inicial)
root.after(2000, limpiar_placas_antiguas)
root.mainloop()
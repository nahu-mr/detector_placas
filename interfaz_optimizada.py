import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import cv2
import datetime
import threading
import time
from detector import detectar_placas
import requests
# CONFIGURACIÓN DE LA VENTANA
root = tk.Tk()
root.title("PlateMind")
root.geometry("1440x900")
root.minsize(1100, 700)
root.configure(bg="#F4F6FA")
root.state('zoomed')  # Pantalla completa en Windows
# ===============================
# PALETA DE COLORES (CLARA – PROFESIONAL)
# ===============================

COLOR_FONDO = "#F4F6FA"           # Fondo principal
COLOR_PANEL = "#FFFFFF"          # Blanco limpio - Panel lateral / tarjetas
COLOR_BOTON = "#13A8E4"           # Azul de accion
COLOR_BOTON_HOVER = "#087FB7"     # Azul oscuro
COLOR_TEXTO = "#10233F"           # Texto principal
COLOR_TEXTO_SEC = "#718096"       # Texto secundario
COLOR_ACCENTO = "#0C2E55"        # Azul marino
COLOR_EXITO = "#6BBF59"           # Verde claro - Éxito
COLOR_PELIGRO = "#EF6B73"         # Rojo
COLOR_ADVERTENCIA = "#F5B942"     # Amarillo
COLOR_GRIS_OSCURO = "#263B59"     # Azul gris
COLOR_BORDE = "#E7ECF3"           # Borde

FUENTE = ("Segoe UI", 11)
FUENTE_TITULO = ("Segoe UI", 18, "bold")
FUENTE_SUBTITULO = ("Segoe UI", 14, "bold")

# ===============================
# VARIABLES GLOBALES
# ===============================
cap = None
after_id = None
placas_en_proceso = {}
placas_tiempo_entrada = {}  # Rastrear cuándo se registró cada entrada
bloqueado = False
mostrando_mensaje = False
lock_procesamiento = threading.Lock()
API_BASE = "http://127.0.0.1:8000/api"

import requests
from tkinter import messagebox

API_BASE = "http://127.0.0.1:8000/api"

def api_esta_registrada(placa):
    placa = placa.strip().upper()

    r = requests.get(f"{API_BASE}/placas/")
    if r.status_code == 200:
        return any(p["placa"].strip().upper() == placa for p in r.json())
    return False


def api_registrar_entrada(placa):
    requests.post(f"{API_BASE}/entrada/", json={"placa": placa})

def api_registrar_salida(placa):
    r = requests.post(f"{API_BASE}/salida/", json={"placa": placa})
    if r.status_code == 200:
        return r.json()
    return None


def api_registrar_autorizada(placa, propietario):
    """Registra una placa y devuelve la respuesta del servidor.

    No se debe mostrar una confirmación hasta que la API haya respondido con
    éxito; de otro modo los errores (por ejemplo, una placa duplicada) quedan
    ocultos al usuario.
    """
    try:
        respuesta = requests.post(
            f"{API_BASE}/placas/",
            json={"placa": placa, "propietario": propietario},
            timeout=10,
        )
        try:
            datos = respuesta.json()
        except ValueError:
            datos = {}

        if respuesta.status_code == 201:
            return True, datos.get("placa", placa)

        return False, datos.get("error", "No se pudo registrar la placa.")
    except requests.RequestException as error:
        return False, f"No se pudo conectar con el servidor: {error}"

def api_obtener_registradas():
    r = requests.get(f"{API_BASE}/placas/")
    return r.json() if r.status_code == 200 else []

def api_obtener_movimientos():
    r = requests.get(f"{API_BASE}/movimientos/")
    return r.json() if r.status_code == 200 else []

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

# La navegacion original se reemplaza por una composicion tipo dashboard.
barra_superior.pack_forget()
panel_izquierdo.pack_forget()
panel_derecho.pack_forget()

app_shell = tk.Frame(root, bg=COLOR_FONDO)
app_shell.pack(fill="both", expand=True)

sidebar = tk.Frame(app_shell, bg="#0B2B51", width=220)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)

brand = tk.Frame(sidebar, bg="#0B2B51")
brand.pack(fill="x", padx=24, pady=(28, 34))
tk.Label(brand, text="◒", bg="#0B2B51", fg="#FFFFFF", font=("Segoe UI Symbol", 31, "bold")).pack(anchor="w")
tk.Label(brand, text="PlateMind", bg="#0B2B51", fg="#FFFFFF", font=("Segoe UI", 18, "bold")).pack(anchor="w")


nav_buttons = {}
def nav_button(key, text, icon, command):
    button = tk.Button(sidebar, text=f" {icon}    {text}", command=command,
                       anchor="w", bd=0, relief="flat", cursor="hand2",
                       bg="#0B2B51", activebackground="#16446F", fg="#DCE9F7",
                       activeforeground="#FFFFFF", font=("Segoe UI", 10), padx=20, pady=12)
    button.pack(fill="x", padx=12, pady=2)
    nav_buttons[key] = button

content_shell = tk.Frame(app_shell, bg=COLOR_FONDO)
content_shell.pack(side="left", fill="both", expand=True)

header = tk.Frame(content_shell, bg="#FFFFFF", height=72)
header.pack(fill="x")
header.pack_propagate(False)
tk.Label(header, text="Dashboard", bg="#FFFFFF", fg=COLOR_TEXTO,
         font=("Segoe UI", 18, "bold")).pack(side="left", padx=30)
search = tk.Entry(header, bd=0, relief="flat", bg="#F4F6FA", fg=COLOR_TEXTO_SEC,
                  font=("Segoe UI", 9), width=34)
search.insert(0, "⌕  Buscar placas, propietarios, movimientos")
search.pack(side="right", padx=(10, 22), ipady=9)
tk.Label(header, text="●  Administrador  ▾", bg="#FFFFFF", fg=COLOR_TEXTO,
         font=("Segoe UI", 10, "bold")).pack(side="right", padx=12)

panel_derecho = tk.Frame(content_shell, bg=COLOR_FONDO)
panel_derecho.pack(fill="both", expand=True)

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
# DASHBOARD PRINCIPAL
# ===============================
frame_dashboard = tk.Frame(panel_derecho, bg=COLOR_FONDO)
dashboard_body = tk.Frame(frame_dashboard, bg=COLOR_FONDO)
dashboard_body.pack(fill="both", expand=True, padx=26, pady=24)

def dashboard_card(parent, title, variable, color, column):
    card = tk.Frame(parent, bg=color, height=102)
    card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 6, 6), pady=(0, 16))
    card.grid_propagate(False)
    tk.Label(card, text=title, bg=color, fg="#FFFFFF" if color != "#DFFF00" else COLOR_TEXTO,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=16, pady=(15, 2))
    tk.Label(card, textvariable=variable, bg=color, fg="#FFFFFF" if color != "#DFFF00" else COLOR_TEXTO,
             font=("Segoe UI", 22, "bold")).pack(anchor="w", padx=16)

metrics = tk.Frame(dashboard_body, bg=COLOR_FONDO)
metrics.pack(fill="x")
for col in range(4): metrics.grid_columnconfigure(col, weight=1, uniform="metric")
stat_total = tk.StringVar(value="--")
stat_today = tk.StringVar(value="--")
stat_active = tk.StringVar(value="--")
stat_income = tk.StringVar(value="S/ --")
dashboard_card(metrics, "PLACAS REGISTRADAS", stat_total, "#EFE9DE", 0)
dashboard_card(metrics, "MOVIMIENTOS HOY", stat_today, "#1288C8", 1)
dashboard_card(metrics, "VEHÍCULOS DENTRO", stat_active, "#40C7E7", 2)
dashboard_card(metrics, "INGRESOS REGISTRADOS", stat_income, "#DFFF00", 3)

dashboard_grid = tk.Frame(dashboard_body, bg=COLOR_FONDO)
dashboard_grid.pack(fill="both", expand=True)
dashboard_grid.grid_columnconfigure(0, weight=3)
dashboard_grid.grid_columnconfigure(1, weight=2)
dashboard_grid.grid_rowconfigure(0, weight=1)
dashboard_grid.grid_rowconfigure(1, weight=1)

def section_card(parent, title, row, column, colspan=1):
    card = tk.Frame(parent, bg="#FFFFFF", highlightbackground=COLOR_BORDE, highlightthickness=1)
    card.grid(row=row, column=column, columnspan=colspan, sticky="nsew", padx=(0, 12) if column == 0 else (0, 0), pady=(0, 12))
    tk.Label(card, text=title, bg="#FFFFFF", fg=COLOR_TEXTO, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=18, pady=(15, 2))
    return card

trend_card = section_card(dashboard_grid, "Actividad semanal", 0, 0)
tk.Label(trend_card, text="Entradas y salidas registradas", bg="#FFFFFF", fg=COLOR_TEXTO_SEC,
         font=("Segoe UI", 9)).pack(anchor="w", padx=18)
trend = tk.Canvas(trend_card, bg="#FFFFFF", height=185, highlightthickness=0)
trend.pack(fill="both", expand=True, padx=10, pady=8)
for index, day in enumerate(("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")):
    x = 45 + index * 58
    trend.create_rectangle(x, 150 - (index % 4) * 23, x + 12, 155, fill="#40C7E7", outline="")
    trend.create_rectangle(x + 16, 150 - ((index + 2) % 5) * 19, x + 28, 155, fill="#DFFF00", outline="")
    trend.create_text(x + 12, 173, text=day, fill=COLOR_TEXTO_SEC, font=("Segoe UI", 8))

status_card = section_card(dashboard_grid, "Estado del estacionamiento", 0, 1)
status_canvas = tk.Canvas(status_card, bg="#FFFFFF", height=190, highlightthickness=0)
status_canvas.pack(fill="both", expand=True)
status_canvas.create_arc(65, 22, 195, 152, start=0, extent=135, fill="#0B2B51", outline="")
status_canvas.create_arc(65, 22, 195, 152, start=138, extent=105, fill="#40C7E7", outline="")
status_canvas.create_arc(65, 22, 195, 152, start=246, extent=110, fill="#EFE9DE", outline="")
status_canvas.create_oval(91, 48, 169, 126, fill="#FFFFFF", outline="")
status_canvas.create_text(130, 78, text="EN VIVO", fill=COLOR_TEXTO_SEC, font=("Segoe UI", 8, "bold"))
status_canvas.create_text(130, 101, text="Control", fill=COLOR_TEXTO, font=("Segoe UI", 16, "bold"))
status_canvas.create_text(130, 173, text="● Activos    ● Registrados", fill=COLOR_TEXTO_SEC, font=("Segoe UI", 8))

recent_card = section_card(dashboard_grid, "Movimientos recientes", 1, 0)
recent_list = tk.Frame(recent_card, bg="#FFFFFF")
recent_list.pack(fill="both", expand=True, padx=18, pady=(4, 15))
dashboard_recent = []

quick_card = section_card(dashboard_grid, "Acciones rápidas", 1, 1)
tk.Label(quick_card, text="Gestiona el acceso vehicular desde un solo lugar.", bg="#FFFFFF", fg=COLOR_TEXTO_SEC,
         wraplength=250, justify="left", font=("Segoe UI", 9)).pack(anchor="w", padx=18, pady=(3, 15))
tk.Button(quick_card, text="  📹  Iniciar cámara", command=lambda: mostrar_seccion("cam"),
          bg="#0B2B51", fg="#FFFFFF", activebackground="#16446F", activeforeground="#FFFFFF",
          relief="flat", bd=0, font=("Segoe UI", 10, "bold"), cursor="hand2", padx=12, pady=10).pack(fill="x", padx=18, pady=4)
tk.Button(quick_card, text="  +  Registrar placa", command=lambda: abrir_ventana_agregar_placa(),
          bg="#EAF5FA", fg="#087FB7", activebackground="#D5EDF7", relief="flat", bd=0,
          font=("Segoe UI", 10, "bold"), cursor="hand2", padx=12, pady=10).pack(fill="x", padx=18, pady=4)
tk.Button(quick_card, text="Ver todos los movimientos  →", command=lambda: mostrar_seccion("mov"),
          bg="#FFFFFF", fg=COLOR_TEXTO, relief="flat", bd=0, font=("Segoe UI", 9, "bold"),
          cursor="hand2").pack(anchor="w", padx=12, pady=(5, 0))

nav_button("dashboard", "Resumen", "▦", lambda: mostrar_seccion("dashboard"))
nav_button("cam", "Monitor en vivo", "◉", lambda: mostrar_seccion("cam"))
nav_button("reg", "Placas autorizadas", "☷", lambda: mostrar_seccion("reg"))
nav_button("mov", "Movimientos", "↕", lambda: mostrar_seccion("mov"))
tk.Frame(sidebar, bg="#315174", height=1).pack(fill="x", padx=20, pady=18)
nav_button("add", "Registrar placa", "+", lambda: abrir_ventana_agregar_placa())
tk.Button(sidebar, text="  ⎋    Cerrar sesión", command=lambda: cerrar(), anchor="w", bd=0, relief="flat",
          bg="#0B2B51", activebackground="#16446F", fg="#DCE9F7", activeforeground="#FFFFFF",
          font=("Segoe UI", 10), padx=20, pady=12, cursor="hand2").pack(side="bottom", fill="x", padx=12, pady=20)

# ===============================
# FUNCIONES DE INTERFAZ
# ===============================
def ocultar_todos_frames():
    for f in (frame_dashboard, frame_camara, frame_reg, frame_mov):
        f.pack_forget()

def mostrar_seccion(seccion):
    detener_camara()
    ocultar_todos_frames()
    for key, button in nav_buttons.items():
        button.config(bg="#16446F" if key == seccion else "#0B2B51")
    if seccion == "dashboard":
        frame_dashboard.pack(fill="both", expand=True)
        actualizar_dashboard()
    elif seccion == "cam":
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
        if not api_esta_registrada(placa):
            # Placa NO registrada - mostrar alerta SOLO UNA VEZ cada 3 segundos
            tiempo_actual = time.time()
            tiempo_registrado = placas_en_proceso.get(placa)
            
            if tiempo_registrado is None:
                # Primera vez que ve esta placa desconocida - mostrar alerta
                with lock_procesamiento:
                    placas_en_proceso[placa] = tiempo_actual
                
                root.after(0, lambda: mostrar_advertencia(
                    f"La placa {placa} no está registrada en el sistema."))
            
            # No hacer más nada - ignorar las re-detecciones durante 3 segundos
            return

        resultado = api_registrar_salida(placa)

        if resultado is None:
            # Nueva entrada
            api_registrar_entrada(placa)

            
            # Rastrear tiempo de entrada (para retraso de 3 segundos)
            placas_tiempo_entrada[placa] = time.time()
            
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
            # VERIFICAR SI HAN PASADO AL MENOS 3 SEGUNDOS DESDE LA ENTRADA
            tiempo_entrada = placas_tiempo_entrada.get(placa)
            if tiempo_entrada is None:
                # Si no hay registro de tiempo, permitir salida
                print(f"⏳ Placa {placa} sin registro de tiempo de entrada. Permitiendo salida.")
                tiempo_entrada = time.time()
            
            tiempo_transcurrido = time.time() - tiempo_entrada
            
            # Si han pasado menos de 3 segundos, no procesar salida
            if tiempo_transcurrido < 3:
                print(f"⏳ Placa {placa} detectada de nuevo pero muy rápido ({tiempo_transcurrido:.1f}s). Esperando 3s mínimo.")
                return
            
            # Proceder con la salida
            monto = resultado['monto']
            duracion = round(resultado['segundos'] / 60, 1)
            
            # Limpiar del diccionario de rastreo
            if placa in placas_tiempo_entrada:
                del placas_tiempo_entrada[placa]
            
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
    ventana.lift()

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
    entry_placa.focus_set()

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
            messagebox.showwarning(
                "Advertencia", "Debe ingresar una placa válida.", parent=ventana
            )
            return

        boton_guardar.config(state="disabled", text="Guardando...")

        def registrar_en_segundo_plano():
            exito, resultado = api_registrar_autorizada(
                placa, prop if prop else "Sin especificar"
            )

            def finalizar_registro():
                if not ventana.winfo_exists():
                    return
                if not exito:
                    boton_guardar.config(state="normal", text="💾 Guardar")
                    messagebox.showerror("No se pudo registrar", resultado, parent=ventana)
                    return

                messagebox.showinfo(
                    "Éxito",
                    f"✅ Placa {resultado} registrada correctamente.",
                    parent=ventana,
                )
                ventana.destroy()
                mostrar_seccion("reg")

            root.after(0, finalizar_registro)

        threading.Thread(target=registrar_en_segundo_plano, daemon=True).start()

    frame_botones = tk.Frame(ventana, bg=COLOR_PANEL)
    frame_botones.pack(pady=20)

    boton_guardar = tk.Button(
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
    )
    boton_guardar.pack(side=tk.LEFT, padx=5)
    
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
    if messagebox.askyesno("Confirmar", "⚠️ ¿Eliminar todos los movimientos?"):
        r = requests.delete(f"{API_BASE}/movimientos/")
        if r.status_code == 200:
            messagebox.showinfo("Éxito", "Movimientos eliminados.")
            mostrar_seccion("mov")
        else:
            messagebox.showerror("Error", "No se pudo eliminar.")

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
            r = requests.delete(f"{API_BASE}/placas/{placa}/")
            if r.status_code == 200:
                messagebox.showinfo("Éxito", f"✅ Usuario con placa {placa} eliminado.")
                ventana.destroy()
                mostrar_seccion("reg")
            else:
                messagebox.showwarning("Aviso", f"No se encontró la placa {placa}.")
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
    """Actualiza la tabla de placas registradas"""
    try:
        # Limpiar tabla
        for row in tree_reg.get_children():
            tree_reg.delete(row)

        # Obtener datos
        data = api_obtener_registradas()
        print(f"📋 Datos recibidos de placas: {data}")  # Debug
        
        # Insertar cada placa
        for p in data:
            placa = p.get("placa", "N/A")
            propietario = p.get("propietario", "Sin especificar")
            tree_reg.insert("", "end", values=(placa, propietario))
        
        print(f"✅ Tabla actualizada con {len(data)} placas")
        
    except Exception as e:
        print(f"❌ Error al actualizar tabla de registradas: {e}")
        import traceback
        traceback.print_exc()


def actualizar_tabla_movimientos():
    """Actualiza la tabla de movimientos"""
    try:
        # Limpiar tabla
        for row in tree_mov.get_children():
            tree_mov.delete(row)

        # Obtener datos
        data = api_obtener_movimientos()
        print(f"📊 Datos recibidos de movimientos: {data}")  # Debug
        
        # Insertar cada movimiento
        for mov in data:
            placa = mov.get("placa", "N/A")
            accion = mov.get("accion", "N/A")
            fecha = mov.get("fecha", "N/A")
            monto = mov.get("monto", "-")
            
            tree_mov.insert("", "end", values=(placa, accion, fecha, monto))
        
        print(f"✅ Tabla actualizada con {len(data)} movimientos")
        
    except Exception as e:
        print(f"❌ Error al actualizar tabla de movimientos: {e}")
        import traceback
        traceback.print_exc()
def actualizar_dashboard():
    """Actualiza los indicadores sin bloquear la interfaz si la API no responde."""
    try:
        placas = api_obtener_registradas()
        movimientos = api_obtener_movimientos()
        stat_total.set(str(len(placas)))
        stat_today.set(str(len(movimientos)))
        entradas = sum(1 for mov in movimientos if str(mov.get("accion", "")).upper() == "ENTRADA")
        salidas = sum(1 for mov in movimientos if str(mov.get("accion", "")).upper() == "SALIDA")
        stat_active.set(str(max(0, entradas - salidas)))
        total = 0.0
        for mov in movimientos:
            try:
                total += float(str(mov.get("monto", 0)).replace("S/", "").strip())
            except (TypeError, ValueError):
                pass
        stat_income.set(f"S/ {total:.2f}")
        for widget in dashboard_recent:
            widget.destroy()
        dashboard_recent.clear()
        recientes = movimientos[:4]
        if not recientes:
            empty = tk.Label(recent_list, text="Aún no hay movimientos registrados.", bg="#FFFFFF", fg=COLOR_TEXTO_SEC, font=("Segoe UI", 9))
            empty.pack(anchor="w", pady=10)
            dashboard_recent.append(empty)
        for mov in recientes:
            accion = str(mov.get("accion", "MOVIMIENTO")).upper()
            color = COLOR_EXITO if accion == "ENTRADA" else COLOR_BOTON
            row = tk.Frame(recent_list, bg="#FFFFFF")
            row.pack(fill="x", pady=5)
            dot = tk.Label(row, text="●", bg="#FFFFFF", fg=color, font=("Segoe UI", 12))
            dot.pack(side="left")
            tk.Label(row, text=mov.get("placa", "N/A"), bg="#FFFFFF", fg=COLOR_TEXTO, font=("Segoe UI", 10, "bold")).pack(side="left", padx=8)
            tk.Label(row, text=accion, bg="#FFFFFF", fg=COLOR_TEXTO_SEC, font=("Segoe UI", 9)).pack(side="right")
            dashboard_recent.append(row)
    except Exception:
        stat_total.set("--")
        stat_today.set("--")
        stat_active.set("--")
        stat_income.set("S/ --")

"""def actualizar_tabla_registradas():
    for row in tree_reg.get_children():
        tree_reg.delete(row)

    data = api_obtener_registradas()
    for p in data:
        tree_reg.insert("", "end", values=(p[1], p[2]))

def actualizar_tabla_movimientos():
    for row in tree_mov.get_children():
        tree_mov.delete(row)
    for fila in api_obtener_movimientos():
        placa = fila["placa"]
        entrada_ts = fila["entrada_ts"]
        salida_ts = fila["salida_ts"]
        monto = fila["monto"]
        procesada = int(fila["procesada"])
        if entrada_ts:
            tree_mov.insert("", "end", values=(placa, "ENTRADA", entrada_ts.strftime("%d/%m/%Y %H:%M:%S"), "-"))
        if procesada == 1 and salida_ts:
            tree_mov.insert("", "end", values=(placa, "SALIDA", salida_ts.strftime("%d/%m/%Y %H:%M:%S"), f"S/ {float(monto):.2f}"))
"""
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
frame_dashboard.pack(fill="both", expand=True)
nav_buttons["dashboard"].config(bg="#16446F")
root.after(100, actualizar_dashboard)
root.after(2000, limpiar_placas_antiguas)
root.mainloop()

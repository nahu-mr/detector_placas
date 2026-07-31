# 🚀 INSTRUCCIONES DE INSTALACIÓN - PlateMind

## ⚙️ PASOS PARA EJECUTAR EL PROYECTO EN OTRA MÁQUINA

### 1️⃣ Crear el Virtual Environment
```powershell
python -m venv .venv
```

### 2️⃣ Activar el Virtual Environment
```powershell
.venv\Scripts\Activate.ps1
```
*Deberías ver `(.venv)` al inicio de la línea de comando*

### 3️⃣ Instalar todas las librerías
```powershell
pip install -r requirements.txt
```

⏱️ **TIEMPO ESTIMADO: 15-25 minutos**
- Depende de tu conexión a Internet
- Con buena conexión (50+ Mbps): ~10-15 minutos
- Con conexión normal (20-50 Mbps): ~15-20 minutos
- Con conexión lenta (< 20 Mbps): ~25-30 minutos

*Esto tardará varios minutos porque hay paquetes grandes como PyTorch, OpenCV y modelos de IA. No cierres la terminal mientras se instala.*

### ⚠️ CONFIGURAR LA BASE DE DATOS (IMPORTANTE)

#### 1. Crear la base de datos en MySQL Workbench

1. Abre **MySQL Workbench**
2. Conéctate a tu servidor MySQL
3. Abre el archivo SQL que está en: `scripts/CREAR_BASE_DATOS.sql`
4. Copia todo el contenido del archivo
5. Pégalo en MySQL Workbench
6. Ejecuta el script

El script creará automáticamente la base de datos `control_placas` con todas las tablas necesarias.

#### 2. Actualizar las credenciales en settings.py
Antes de ejecutar el servidor, debes configurar tu contraseña de MySQL en:
```
Registro/Registro/settings.py
```

Busca la sección `DATABASES` y actualiza con tus credenciales:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'control_placas',        # Nombre de tu base de datos
        'USER': 'root',                  # Tu usuario MySQL
        'PASSWORD': 'TU_CONTRASEÑA',     # ⚠️ REEMPLAZA AQUÍ
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

### 4️⃣ Navegar a la carpeta de Django
```powershell
cd Registro
```

### 5️⃣ Hacer migraciones de la base de datos
```powershell
python manage.py migrate
```

### 6️⃣ Iniciar el servidor Django
```powershell
python manage.py runserver
```

El servidor estará disponible en: **http://127.0.0.1:8000/**

---

## 🔧 COMANDO COMBINADO (Todo en uno)
Si quieres hacerlo todo de una vez:
```powershell
python -m venv .venv; .venv\Scripts\Activate.ps1; pip install -r requirements.txt; cd Registro; python manage.py migrate; python manage.py runserver
```

---

## 📦 LISTA DE DEPENDENCIAS PRINCIPALES

- **Django 4.2** - Framework web
- **OpenCV** - Procesamiento de imágenes
- **PyTorch** - Deep Learning
- **EasyOCR** - Reconocimiento de texto en placas
- **Ultralytics** - Detección YOLO
- **MySQL** - Base de datos
- **Pandas** - Análisis de datos
- **Pillow** - Procesamiento de imágenes

---

## ⚠️ REQUISITOS DEL SISTEMA

- **Python 3.12.10** (Versión actual usada en este proyecto)
- Python 3.8 o superior (mínimo recomendado)
- 4GB RAM mínimo
- 5GB de espacio libre en disco
- Cámara web (para la funcionalidad de detección)
- Base de datos MySQL configurada

---

## 🐛 SOLUCIÓN DE PROBLEMAS

### Si falla la instalación de OpenCV:
```powershell
pip install --upgrade pip setuptools wheel
pip install opencv-python opencv-contrib-python
```

### Si no se activa el venv:
Ejecuta esto en PowerShell:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Si falta la base de datos:
```powershell
python manage.py migrate
```

---

✅ **¡Listo! El proyecto debería estar funcionando.**
RAMA-VERSION-FINAL
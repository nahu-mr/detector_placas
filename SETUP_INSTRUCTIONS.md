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
*Esto tardará varios minutos (especialmente OpenCV, PyTorch y modelos de IA)*

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

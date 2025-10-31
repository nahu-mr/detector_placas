# 🚗 Sistema de Detección y Control de Placas Vehiculares  
### Proyecto de Visión Artificial – Perú 🇵🇪

---

## 📖 Descripción del Proyecto
Este sistema detecta, reconoce y registra placas vehiculares **en tiempo real** utilizando técnicas de **visión por computadora** e **inteligencia artificial**.

El proyecto automatiza el control de acceso vehicular mediante una interfaz gráfica desarrollada en **Tkinter**, integrando **YOLOv8** para detección y **EasyOCR** para reconocimiento de texto, todo respaldado por una **base de datos SQLite**.

---

## 🧠 Tecnologías Utilizadas
| Tecnología | Función |
|-------------|----------|
| **Python** | Lenguaje principal |
| **Tkinter (tk)** | Interfaz gráfica: control de cámara, botones, tablas y alertas |
| **YOLOv8 (Ultralytics)** | Detección de placas vehiculares en tiempo real |
| **EasyOCR** | Reconocimiento del texto alfanumérico de la placa |
| **OpenCV** | Captura de video y procesamiento de imágenes |
| **SQLite3** | Base de datos local para registro de movimientos |

---

## ⚙️ Requisitos de instalación

Antes de ejecutar el proyecto, asegúrate de tener **Python 3.10+** y ejecuta lo siguiente:

```bash
python -m venv .venv
.venv\Scripts\activate   # En Windows


pip install --upgrade pip setuptools wheel
pip install ultralytics easyocr opencv-python pillow

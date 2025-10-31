@echo off
echo ==================================================
echo   🚗 SISTEMA DE CONTROL VEHICULAR - INSTALADOR
echo ==================================================
echo.

REM --- Crear entorno virtual si no existe ---
if not exist ".venv" (
    echo [1/5] Creando entorno virtual...
    python -m venv .venv
) else (
    echo [1/5] Entorno virtual ya existe.
)

REM --- Activar entorno virtual ---
echo [2/5] Activando entorno virtual...
call .venv\Scripts\activate

REM --- Actualizar pip, setuptools y wheel ---
echo [3/5] Actualizando herramientas base pip...
python.exe -m pip install --upgrade pip

REM --- Actualizar pip, setuptools y wheel ---
echo [4/5] Actualizando herramientas base (setuptools, wheel)...
python -m pip install --upgrade setuptools wheel


REM --- Instalar dependencias desde requirements.txt ---
echo [5/5] Instalando dependencias del proyecto...
pip install ultralytics easyocr opencv-python pillow torch torchvision mysql-connector-python tk

echo.
echo ==================================================
echo ✅ INSTALACIÓN COMPLETA
echo Para ejecutar el sistema, escribe en un power shell con CTRL + Ñ:
echo.
echo    .venv\Scripts\activate
echo    python interfaz.py
echo.
pause

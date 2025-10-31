@echo off
echo ==================================================
echo   🚗 SISTEMA DE CONTROL VEHICULAR - INSTALADOR
echo ==================================================
echo.

REM --- Crear entorno virtual si no existe ---
if not exist ".venv" (
    echo [1/4] Creando entorno virtual...
    python -m venv .venv
) else (
    echo [1/4] Entorno virtual ya existe.
)

REM --- Activar entorno virtual ---
echo [2/4] Activando entorno virtual...
call .venv\Scripts\activate

REM --- Actualizar pip, setuptools y wheel ---
echo [3/4] Actualizando herramientas base (pip, setuptools, wheel)...
python -m pip install --upgrade pip setuptools wheel

REM --- Instalar dependencias desde requirements.txt ---
echo [4/4] Instalando dependencias del proyecto...
pip install -r requirements.txt

echo.
echo ==================================================
echo ✅ INSTALACIÓN COMPLETA
echo Para ejecutar el sistema, escribe en un power shell con CTRL + Ñ:
echo.
echo    .venv\Scripts\activate
echo    python interfaz.py
echo.
pause

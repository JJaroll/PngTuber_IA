@echo off
chcp 65001 > nul
title AIterEgo - Compilador CPU (Universal)
color 0A

echo.
echo ╔══════════════════════════════════════════════════════════════════════╗
echo ║                                                                      ║
echo ║      ██╗     ██╗  █████╗ ██████╗  ██████╗ ██╗     ██╗                ║
echo ║      ██║     ██║ ██╔══██╗██╔══██╗██╔═══██╗██║     ██║                ║
echo ║      ██║     ██║ ███████║██████╔╝██║   ██║██║     ██║                ║
echo ║ ██╗  ██║██╗  ██║ ██╔══██║██╔══██╗██║   ██║██║     ██║                ║
echo ║ ╚█████╔╝╚█████╔╝ ██║  ██║██║  ██║╚██████╔╝███████╗███████╗           ║
echo ║  ╚════╝  ╚════╝  ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝           ║
echo ║                                                                      ║
echo ║   (AI)terEgo v1.0.0 - "Dando vida a los píxeles."                    ║
echo ║   GitHub: github.com/JJaroll                                         ║
echo ║                                                                      ║
echo ╚══════════════════════════════════════════════════════════════════════╝
echo.

echo ===================================================
echo   Construyendo (AI)terEgo - Version CPU (Ligera)
echo ===================================================
echo.

echo [1/5] Verificando entorno virtual (venv_cpu)...
if not exist venv_cpu (
    echo Creando nuevo entorno virtual...
    python -m venv venv_cpu
)

echo.
echo [2/5] Activando entorno e instalando dependencias exactas...
call venv_cpu\Scripts\activate.bat
python -m pip install --upgrade pip
echo Instalando PyTorch CPU...
pip install torch==2.2.1+cpu torchaudio==2.2.1+cpu --index-url https://download.pytorch.org/whl/cpu
echo Instalando dependencias del sistema...
pip install "numpy<2" "transformers<4.40" pyaudio sounddevice librosa PyQt6 pyinstaller

echo.
echo [3/5] REPARACIÓN AUTOMÁTICA DE ÍCONO (Multicapa)...
python -c "from PIL import Image; img=Image.open('assets/IA.png'); img.save('assets/app_icon.ico', format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])"

echo.
echo [4/5] Limpiando caches de compilacion...
if exist build rmdir /s /q build
if exist dist\AIterEgo_CPU rmdir /s /q dist\AIterEgo_CPU
if exist AIterEgo_CPU.spec del /f /q AIterEgo_CPU.spec

echo.
echo [5/5] Compilando con PyInstaller...
pyinstaller --clean --noconfirm --onedir --windowed --name "AIterEgo_CPU" ^
    --add-data "assets;assets" ^
    --icon "assets/app_icon.ico" ^
    --hidden-import pyaudio ^
    --hidden-import sounddevice ^
    main.py

echo.
echo ========================================================
echo   Compilacion CPU finalizada con exito.
echo   Tu ejecutable esta en: dist\AIterEgo_CPU
echo ========================================================
pause
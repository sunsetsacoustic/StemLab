@echo off
setlocal
echo SunoSplitter GPU Build Script
echo =============================

REM Check for Python 3.11 or 3.10
py -3.11 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=py -3.11
    goto :FOUND_PYTHON
)

py -3.10 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=py -3.10
    goto :FOUND_PYTHON
)

echo ERROR: Python 3.11 or 3.10 not found or not working.
echo Please install Python 3.11 from python.org and try again.
pause
exit /b 1

:FOUND_PYTHON
echo Found Python: %PY_CMD%
echo Creating virtual environment (venv_gpu)...
%PY_CMD% -m venv venv_gpu

echo Installing dependencies...
call venv_gpu\Scripts\activate
pip install --upgrade pip
pip install PyQt6 soundfile
echo Installing PyTorch with CUDA 12.1 support...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install demucs audio-separator pyinstaller

echo Building EXE...
pyinstaller --clean --noconsole --onefile --name SunoSplitter_GPU --version-file version_info.txt --add-data "src;src" --collect-all demucs --collect-all torchaudio --collect-all soundfile --collect-all numpy --hidden-import="sklearn.utils._cython_blas" --hidden-import="sklearn.neighbors.typedefs" --hidden-import="sklearn.neighbors.quad_tree" --hidden-import="sklearn.tree._utils" main.py

echo.
echo Build Complete!
echo You can find SunoSplitter_GPU.exe in the dist folder.
pause

@echo off
setlocal
echo ==========================================
echo SunoSplitter CPU Build
echo ==========================================
echo.
echo Step 1: Creating Virtual Environment (venv_cpu)...
if exist venv_cpu (
    echo Removing old venv_cpu...
    rmdir /s /q venv_cpu
)
py -3.10 -m venv venv_cpu

echo.
echo Step 2: Installing Dependencies (CPU Version)...
call venv_cpu\Scripts\activate
python -m pip install --upgrade pip
pip install PyQt6 soundfile
echo.
echo Downloading PyTorch (CPU)...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
echo.
echo Installing Demucs and other tools...
pip install demucs audio-separator pyinstaller onnxruntime

echo.
echo Step 3: Building EXE...
pyinstaller --clean --noconsole --onefile --name SunoSplitter --version-file version_info.txt --add-data "src;src" --collect-all demucs --collect-all torchaudio --collect-all soundfile --collect-all numpy --hidden-import="sklearn.utils._cython_blas" --hidden-import="sklearn.neighbors.typedefs" --hidden-import="sklearn.neighbors.quad_tree" --hidden-import="sklearn.tree._utils" main.py

echo.
echo ==========================================
echo Build Complete!
echo You can find SunoSplitter.exe in the dist folder.
echo ==========================================
pause

@echo off
setlocal
echo ==========================================
echo SunoSplitter GPU Build - Interactive Mode
echo ==========================================
echo.
echo Step 1: Checking Python 3.10...
py -3.10 --version
if %errorlevel% neq 0 (
    echo ERROR: Python 3.10 not found!
    pause
    exit /b 1
)

echo.
echo Step 2: Creating Virtual Environment (venv_gpu)...
if exist venv_gpu (
    echo Removing old venv_gpu...
    rmdir /s /q venv_gpu
)
py -3.10 -m venv venv_gpu

echo.
echo Step 3: Installing Dependencies...
echo This will show a progress bar. Please wait.
echo.
call venv_gpu\Scripts\activate
python -m pip install --upgrade pip
pip install PyQt6 soundfile
echo.
echo Downloading PyTorch (2.5 GB)...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
echo.
echo Installing Demucs and other tools...
pip install demucs audio-separator pyinstaller

echo.
echo Step 4: Building EXE...
pyinstaller --clean --noconsole --onefile --name SunoSplitter_GPU --version-file version_info.txt --add-data "src;src" --collect-all demucs --collect-all torchaudio --collect-all soundfile --collect-all numpy --hidden-import="sklearn.utils._cython_blas" --hidden-import="sklearn.neighbors.typedefs" --hidden-import="sklearn.neighbors.quad_tree" --hidden-import="sklearn.tree._utils" main.py

echo.
echo ==========================================
echo Build Complete!
echo You can find SunoSplitter_GPU.exe in the dist folder.
echo ==========================================
pause

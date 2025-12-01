@echo off
setlocal
echo ==========================================
echo SunoSplitter CPU Rebuild (Robust)
echo ==========================================
echo.
echo Step 1: Activating Environment...
call venv_cpu\Scripts\activate

echo.
echo Step 2: Verifying Dependencies...
python -m pip install --upgrade pip
python -m pip install PyQt6 soundfile torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
python -m pip install demucs audio-separator pyinstaller onnxruntime

echo.
echo Step 3: Building EXE (Explicit Imports)...
pyinstaller --clean --noconsole --onefile --name StemLab --version-file version_info.txt --add-data "src;src" --add-data "resources;resources" --collect-all demucs --collect-all torchaudio --collect-all soundfile --collect-all numpy --hidden-import="PyQt6" --hidden-import="sklearn.utils._cython_blas" --hidden-import="sklearn.neighbors.typedefs" --hidden-import="sklearn.neighbors.quad_tree" --hidden-import="sklearn.tree._utils" main.py

echo.
echo ==========================================
echo Build Complete!
echo You can find StemLab.exe in the dist folder.
echo ==========================================
pause

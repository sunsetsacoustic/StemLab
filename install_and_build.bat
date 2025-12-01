@echo off
setlocal ENABLEDELAYEDEXPANSION

rem Always run from the directory where this script lives
cd /d "%~dp0"

set "VENV_NAME=venv_cpu"

echo ==========================================
echo StemLab Setup / Build Script (CPU / GPU)
echo ==========================================

rem ------------------------------------------
rem Argument parsing
rem ------------------------------------------
set "ARG_CPU="
set "ARG_GPU="
set "ARG_BUILD_EXE="
set "ARG_NO_BUILD_EXE="
set "ARG_RECREATE_VENV="
set "ARG_REUSE_VENV="

:parse_args
if "%~1"=="" goto after_args

if /I "%~1"=="--help" goto :show_help
if /I "%~1"=="--cpu" set "ARG_CPU=1"
if /I "%~1"=="--gpu" set "ARG_GPU=1"
if /I "%~1"=="--build-exe" set "ARG_BUILD_EXE=1"
if /I "%~1"=="--no-build-exe" set "ARG_NO_BUILD_EXE=1"
if /I "%~1"=="--recreate-venv" set "ARG_RECREATE_VENV=1"
if /I "%~1"=="--reuse-venv" set "ARG_REUSE_VENV=1"

shift
goto :parse_args

:after_args
echo.

rem ------------------------------------------
rem Step 1: Locate Python 3.10
rem ------------------------------------------
set "PY_CMD="

py -3.10 --version >nul 2>&1
if %errorlevel%==0 (
    set "PY_CMD=py -3.10"
)

if not defined PY_CMD (
    python --version 2>nul | find "3.10" >nul 2>&1
    if %errorlevel%==0 (
        set "PY_CMD=python"
    )
)

if not defined PY_CMD (
    echo ERROR: Python 3.10 not found.
    echo Make sure either "py -3.10" or "python" (3.10) is available on PATH.
    goto :end
)

echo Using Python command: %PY_CMD%
echo.

rem ------------------------------------------
rem Step 2: Create or reuse virtual environment
rem ------------------------------------------
if exist "%VENV_NAME%" (
    echo Found existing virtual environment "%VENV_NAME%".

    if defined ARG_RECREATE_VENV (
        echo Recreating venv because --recreate-venv was specified...
        rmdir /s /q "%VENV_NAME%"
    ) else if defined ARG_REUSE_VENV (
        echo Reusing existing venv because --reuse-venv was specified...
    ) else (
        set /p REUSE_VENV=Reuse it instead of recreating? [Y/n]: 
        if /I "!REUSE_VENV!"=="N" (
            echo Removing old "%VENV_NAME%"...
            rmdir /s /q "%VENV_NAME%"
        ) else (
            echo Reusing existing environment.
        )
    )
)

if not exist "%VENV_NAME%" (
    echo Creating virtual environment "%VENV_NAME%"...
    %PY_CMD% -m venv "%VENV_NAME%"
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment.
        goto :end
    )
)

echo Activating virtual environment "%VENV_NAME%"...
call "%VENV_NAME%\Scripts\activate"
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment.
    goto :end
)

rem ------------------------------------------
rem Step 3: Install / update dependencies
rem ------------------------------------------
echo.
echo Upgrading pip...
python -m pip install --upgrade pip
if %errorlevel% neq 0 goto :end

rem Choose CPU vs GPU PyTorch
set "TORCH_INDEX_URL="
if defined ARG_GPU (
    set "TORCH_INDEX_URL=https://download.pytorch.org/whl/cu121"
) else if defined ARG_CPU (
    set "TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu"
) else (
    echo.
    set /p USE_GPU=Install GPU-accelerated PyTorch for NVIDIA (large download)? [y/N]: 
    if /I "!USE_GPU!"=="Y" (
        set "TORCH_INDEX_URL=https://download.pytorch.org/whl/cu121"
    ) else (
        set "TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu"
    )
)

echo.
echo Installing core packages (PyQt6, soundfile)...
python -m pip install PyQt6 soundfile
if %errorlevel% neq 0 goto :end

echo.
echo Installing PyTorch from %TORCH_INDEX_URL% ...
python -m pip install torch torchvision torchaudio --index-url %TORCH_INDEX_URL%
if %errorlevel% neq 0 goto :end

echo.
echo Installing Demucs, Audio Separator, PyInstaller, ONNX Runtime...
python -m pip install demucs audio-separator pyinstaller onnxruntime
if %errorlevel% neq 0 goto :end

echo.
echo Dependencies installed successfully.

rem ------------------------------------------
rem Step 4: Optional EXE build
rem ------------------------------------------
set "DO_BUILD_EXE="

if defined ARG_BUILD_EXE (
    set "DO_BUILD_EXE=1"
) else if defined ARG_NO_BUILD_EXE (
    set "DO_BUILD_EXE="
) else (
    echo.
    set /p BUILD_EXE=Build standalone StemLab.exe with PyInstaller now? [y/N]: 
    if /I "!BUILD_EXE!"=="Y" (
        set "DO_BUILD_EXE=1"
    ) else (
        set "DO_BUILD_EXE="
    )
)

if not defined DO_BUILD_EXE (
    echo.
    echo Skipping PyInstaller build.
    echo To run from source:
    echo   call %VENV_NAME%\Scripts\activate
    echo   python main.py
    goto :end
)

echo.
echo Building EXE with PyInstaller...

set "PYI_NAME=StemLab"
set "PYI_VERSION_FILE="
if exist "version_info.txt" (
    set "PYI_VERSION_FILE=--version-file version_info.txt"
)

pyinstaller --clean --noconsole --onefile ^
    --name "%PYI_NAME%" ^
    %PYI_VERSION_FILE% ^
    --add-data "src;src" ^
    --add-data "resources;resources" ^
    --collect-all demucs ^
    --collect-all torchaudio ^
    --collect-all soundfile ^
    --collect-all numpy ^
    --hidden-import="PyQt6" ^
    --hidden-import="sklearn.utils._cython_blas" ^
    --hidden-import="sklearn.neighbors.typedefs" ^
    --hidden-import="sklearn.neighbors.quad_tree" ^
    --hidden-import="sklearn.tree._utils" ^
    main.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: PyInstaller build failed.
    goto :end
)

echo.
echo ==========================================
echo Build Complete!
echo You can find %PYI_NAME%.exe in the dist folder.
echo ==========================================
goto :end


:show_help
echo.
echo Usage: %~nx0 [options]
echo.
echo Options:
echo   --cpu             Use CPU-only PyTorch (default if no choice given)
echo   --gpu             Use GPU (CUDA/cu121) PyTorch
echo   --recreate-venv   Recreate venv_cpu if it exists
echo   --reuse-venv      Reuse existing venv_cpu if it exists
echo   --build-exe       Build StemLab.exe with PyInstaller
echo   --no-build-exe    Do not build EXE; just set up environment
echo   --help            Show this help
echo.
echo Examples:
echo   %~nx0 --cpu --recreate-venv --no-build-exe
echo   %~nx0 --gpu --reuse-venv --build-exe
goto :end


:end
echo.
pause
endlocal

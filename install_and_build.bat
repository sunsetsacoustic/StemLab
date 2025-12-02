@echo off
setlocal

rem ==========================================
rem CONFIGURATION
rem ==========================================
rem Define the CUDA version for PyTorch (e.g., cu118, cu121, cu124)
set "CUDA_VER=cu121"

rem Base URL for PyTorch wheels
set "TORCH_BASE_URL=https://download.pytorch.org/whl"
rem ==========================================

rem Run from the directory where this script lives
cd /d "%~dp0"

echo ==========================================
echo StemLab Setup / Build Script (CPU / GPU)
echo ==========================================

echo ------------------------------------------
echo Argument parsing
echo ------------------------------------------
set "ARG_CPU="
set "ARG_GPU="
set "ARG_BUILD_EXE="
set "ARG_NO_BUILD_EXE="
set "ARG_RECREATE_VENV="
set "ARG_REUSE_VENV="

:parse_args
if "%~1"=="" goto after_args

if /I "%~1"=="--help"          goto show_help
if /I "%~1"=="--cpu"           set "ARG_CPU=1"
if /I "%~1"=="--gpu"           set "ARG_GPU=1"
if /I "%~1"=="--build-exe"     set "ARG_BUILD_EXE=1"
if /I "%~1"=="--no-build-exe"  set "ARG_NO_BUILD_EXE=1"
if /I "%~1"=="--recreate-venv" set "ARG_RECREATE_VENV=1"
if /I "%~1"=="--reuse-venv"    set "ARG_REUSE_VENV=1"

shift
goto parse_args

:after_args
echo.

rem ------------------------------------------
rem Resolve conflicting flags
rem ------------------------------------------
if defined ARG_CPU (
  if defined ARG_GPU (
    echo Warning: Both --cpu and --gpu were specified. Using GPU settings.
    set "ARG_CPU="
  )
)

if defined ARG_BUILD_EXE (
  if defined ARG_NO_BUILD_EXE (
    echo Warning: Both --build-exe and --no-build-exe were specified. Will build EXE.
    set "ARG_NO_BUILD_EXE="
  )
)

if defined ARG_RECREATE_VENV (
  if defined ARG_REUSE_VENV (
    echo Warning: Both --recreate-venv and --reuse-venv were specified. Recreating venv.
    set "ARG_REUSE_VENV="
  )
)

rem ------------------------------------------
rem Decide venv name (CPU vs GPU)
rem ------------------------------------------
set "VENV_NAME=venv_cpu"
if defined ARG_GPU (
  set "VENV_NAME=venv_gpu"
)

echo Using virtual environment folder: %VENV_NAME%
echo.

echo ------------------------------------------
echo Step 1: Locate Python 3.10
echo ------------------------------------------
set "PY_CMD="

rem Prefer the launcher explicitly targeting 3.10
py -3.10 --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py -3.10"
)

rem Fallback: check that bare "python" is exactly 3.10.x
if not defined PY_CMD (
    python -c "import sys; sys.exit(0 if sys.version_info[0]==3 and sys.version_info[1]==10 else 1)" >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=python"
    )
)

if not defined PY_CMD (
    echo ERROR: Python 3.10 not found.
    echo Make sure that "py -3.10" or "python" runs Python 3.10 and is on PATH.
    goto end
)

echo Using Python command: %PY_CMD%
echo.

echo ------------------------------------------
echo Step 2: Create or reuse virtual environment
echo ------------------------------------------
set "DID_ATTEMPT_CREATE="

if exist "%VENV_NAME%" (
    echo Found existing virtual environment "%VENV_NAME%".
    call :handle_existing_venv
) else (
    set "DID_ATTEMPT_CREATE=1"
    call :create_venv
)

if not exist "%VENV_NAME%" (
    if defined DID_ATTEMPT_CREATE (
        echo ERROR: Virtual environment "%VENV_NAME%" could not be created.
    ) else (
        echo ERROR: Virtual environment "%VENV_NAME%" does not exist.
    )
    goto end
)

echo Activating virtual environment "%VENV_NAME%"...
call "%VENV_NAME%\Scripts\activate"
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    goto end
)

echo ------------------------------------------
echo Step 3: Install / update dependencies
echo ------------------------------------------
echo.

rem ------------------------------------------
rem Setup Install Command (uv vs pip)
rem ------------------------------------------
rem Default to standard pip
set "PIP_INSTALL_CMD=python -m pip install"

echo Checking for 'uv' (fast package installer)...
rem Try to install uv into the venv. It is very small and speeds up the rest significantly.
python -m pip install uv >nul 2>&1
if not errorlevel 1 (
    echo 'uv' installed successfully. Using uv for fast installation.
    set "PIP_INSTALL_CMD=uv pip install"
) else (
    echo 'uv' installation failed or skipped. Falling back to standard pip.
    echo Upgrading pip...
    python -m pip install --upgrade pip
)

rem ------------------------------------------
rem Select Torch/ONNX Targets
rem ------------------------------------------
echo.
echo Choose CPU vs GPU Configuration...
set "TORCH_INDEX_URL="
set "ONNX_PACKAGE=onnxruntime"

if defined ARG_GPU (
    set "TORCH_INDEX_URL=%TORCH_BASE_URL%/%CUDA_VER%"
    set "ONNX_PACKAGE=onnxruntime-gpu"
) else (
    if defined ARG_CPU (
        set "TORCH_INDEX_URL=%TORCH_BASE_URL%/cpu"
    ) else (
        call :select_torch_index
    )
)

rem Double check: if select_torch_index set the URL to cuda, we must switch ONNX to gpu
if "%TORCH_INDEX_URL%"=="%TORCH_BASE_URL%/%CUDA_VER%" (
    set "ONNX_PACKAGE=onnxruntime-gpu"
)

echo.
echo Target Configuration:
echo   PyTorch URL: %TORCH_INDEX_URL%
echo   ONNX Runtime: %ONNX_PACKAGE%
echo.

rem ------------------------------------------
rem Install Packages
rem ------------------------------------------

echo Installing core packages (PyQt6, soundfile)...
%PIP_INSTALL_CMD% PyQt6 soundfile
if errorlevel 1 goto end

echo.
echo Installing PyTorch...
%PIP_INSTALL_CMD% torch torchvision torchaudio --index-url %TORCH_INDEX_URL%
if errorlevel 1 goto end

echo.
echo Installing Demucs, Audio Separator, PyInstaller, and %ONNX_PACKAGE%...
rem IMPORTANT: We repeat --index-url here. If we don't, pip might find a newer 
rem version of 'torch' on the public PyPi (CPU only) required by these libs 
rem and overwrite the CUDA version we just installed.
%PIP_INSTALL_CMD% demucs audio-separator pyinstaller %ONNX_PACKAGE% --index-url %TORCH_INDEX_URL%
if errorlevel 1 goto end

echo.
echo Dependencies installed successfully.

echo ------------------------------------------
echo Step 4: Optional EXE build
echo ------------------------------------------
set "DO_BUILD_EXE="

if defined ARG_BUILD_EXE (
    set "DO_BUILD_EXE=1"
) else (
    if defined ARG_NO_BUILD_EXE (
        set "DO_BUILD_EXE="
    ) else (
        call :ask_build_exe
    )
)

if not defined DO_BUILD_EXE (
    echo.
    echo Skipping PyInstaller build.
    echo To run from source:
    echo   call %VENV_NAME%\Scripts\activate
    echo   python main.py
    goto end
)

rem Defensive checks before PyInstaller
if not exist "main.py" (
    echo ERROR: main.py not found in %cd%.
    goto end
)
if not exist "src" (
    echo ERROR: src directory not found in %cd%.
    goto end
)
if not exist "resources" (
    echo ERROR: resources directory not found in %cd%.
    goto end
)

echo.
echo Building EXE with PyInstaller...

set "PYI_NAME=StemLab"
set "PYI_VERSION_FILE="
if exist "version_info.txt" (
    set "PYI_VERSION_FILE=--version-file version_info.txt"
)

rem Note: We explicitly quote the variables to handle spaces or empty values gracefully
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

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed.
    goto end
)

echo.
echo ==========================================
echo Build Complete!
echo You can find %PYI_NAME%.exe in the dist folder.
echo ==========================================
goto end


rem ==========================================
rem SUBROUTINES
rem ==========================================

:handle_existing_venv
if defined ARG_RECREATE_VENV (
    echo Recreating venv because --recreate-venv was specified...
    rmdir /s /q "%VENV_NAME%"
    set "DID_ATTEMPT_CREATE=1"
    call :create_venv
    goto :eof
)

if defined ARG_REUSE_VENV (
    echo Reusing existing venv because --reuse-venv was specified...
    goto :eof
)

set /p REUSE_VENV=Reuse it instead of recreating? [Y/n]: 
if /I "%REUSE_VENV%"=="N" (
    echo Removing old "%VENV_NAME%"...
    rmdir /s /q "%VENV_NAME%"
    set "DID_ATTEMPT_CREATE=1"
    call :create_venv
) else (
    echo Reusing existing environment.
)
goto :eof


:create_venv
echo Creating virtual environment "%VENV_NAME%"...
%PY_CMD% -m venv "%VENV_NAME%"
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment.
)
goto :eof


:select_torch_index
echo.
echo PyTorch CUDA Configuration: %CUDA_VER%
set /p CHOICE_GPU=Install GPU-accelerated PyTorch for NVIDIA - large download? [y/N]: 
if /I "%CHOICE_GPU%"=="Y" (
    set "TORCH_INDEX_URL=%TORCH_BASE_URL%/%CUDA_VER%"
    set "ONNX_PACKAGE=onnxruntime-gpu"
) else (
    set "TORCH_INDEX_URL=%TORCH_BASE_URL%/cpu"
)
goto :eof


:ask_build_exe
echo.
set /p CHOICE_BUILD=Build standalone StemLab.exe with PyInstaller now? [y/N]: 
if /I "%CHOICE_BUILD%"=="Y" set "DO_BUILD_EXE=1"
goto :eof


:show_help
echo.
echo Usage: %~nx0 [options]
echo.
echo Options:
echo   --cpu             Force CPU-only PyTorch wheels (no CUDA).
echo   --gpu             Use GPU (%CUDA_VER%) PyTorch wheels and venv_gpu.
echo   --recreate-venv   Recreate the virtualenv if it exists.
echo   --reuse-venv      Reuse an existing virtualenv if it exists.
echo   --build-exe       Build StemLab.exe with PyInstaller.
echo   --no-build-exe    Do not build EXE; just set up environment.
echo   --help            Show this help.
echo.
echo Without --cpu/--gpu, you will be prompted interactively for CPU vs GPU.
echo.
echo Examples:
echo   %~nx0 --cpu --recreate-venv --no-build-exe
echo   %~nx0 --gpu --reuse-venv --build-exe
goto end


:end
echo.
pause
endlocal

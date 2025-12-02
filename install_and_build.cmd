@echo off
rem -------------------------------------------------------------------
rem StemLab setup/build script (CPU/GPU)
rem This script is designed to be run from SteamLab project directory.
rem It must be saved with a .cmd extension.
rem -------------------------------------------------------------------

setlocal EnableExtensions

rem ==========================================
rem CONFIGURATION
rem ==========================================
rem Define the CUDA version for PyTorch (e.g., cu118, cu121, cu124)
set "CUDA_VER=cu121"

rem Base URL for PyTorch wheels
set "TORCH_BASE_URL=https://download.pytorch.org/whl"
rem ==========================================

rem Define the latest stable FFmpeg version for winget installation.
rem According to the official FFmpeg project, version 8.0.1 released on 2025-11-20
rem is the current stable release【665507991686221†L169-L172】.
set "FFMPEG_VERSION=8.0.1"

rem Ensure we are in the directory containing this script
cd /d "%~dp0"

echo ==========================================
echo StemLab Setup / Build Script (CPU / GPU)
echo ==========================================

echo ------------------------------------------
echo Argument parsing
echo ------------------------------------------
rem Initialize flags to empty strings
set "ARG_CPU="
set "ARG_GPU="
set "ARG_BUILD_EXE="
set "ARG_NO_BUILD_EXE="
set "ARG_RECREATE_VENV="
set "ARG_REUSE_VENV="
set "ARG_INSTALL_FFMPEG="
set "ARG_NO_INSTALL_FFMPEG="

:parse_args
if "%~1"=="" goto after_args

if /I "%~1"=="--help"          goto show_help
if /I "%~1"=="--cpu"           set "ARG_CPU=1"
if /I "%~1"=="--gpu"           set "ARG_GPU=1"
if /I "%~1"=="--build-exe"     set "ARG_BUILD_EXE=1"
if /I "%~1"=="--no-build-exe"  set "ARG_NO_BUILD_EXE=1"
if /I "%~1"=="--recreate-venv" set "ARG_RECREATE_VENV=1"
if /I "%~1"=="--reuse-venv"    set "ARG_REUSE_VENV=1"
if /I "%~1"=="--install-ffmpeg" set "ARG_INSTALL_FFMPEG=1"
if /I "%~1"=="--no-install-ffmpeg" set "ARG_NO_INSTALL_FFMPEG=1"

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

rem Resolve conflicting FFmpeg install flags
if defined ARG_INSTALL_FFMPEG (
  if defined ARG_NO_INSTALL_FFMPEG (
    echo Warning: Both --install-ffmpeg and --no-install-ffmpeg were specified. Installing FFmpeg.
    set "ARG_NO_INSTALL_FFMPEG="
  )
)

rem ------------------------------------------
rem Step 0: Determine Mode (CPU vs GPU)
rem ------------------------------------------
rem If neither flag was set, prompt the user interactively.

if defined ARG_CPU goto mode_decided
if defined ARG_GPU goto mode_decided

echo No CPU/GPU flag specified.
set /p CHOICE_GPU=Install GPU-accelerated PyTorch (%CUDA_VER%)? [y/N]: 
if /I "%CHOICE_GPU%"=="Y" (
    set "ARG_GPU=1"
) else (
    set "ARG_CPU=1"
)

:mode_decided
rem Now we are guaranteed to have either ARG_CPU or ARG_GPU set.

rem ------------------------------------------
rem Configure Venv Name and URLs based on Mode
rem ------------------------------------------
set "VENV_NAME=venv_cpu"
set "TORCH_INDEX_URL=%TORCH_BASE_URL%/cpu"
set "ONNX_PACKAGE=onnxruntime"

if defined ARG_GPU (
  set "VENV_NAME=venv_gpu"
  set "TORCH_INDEX_URL=%TORCH_BASE_URL%/%CUDA_VER%"
  set "ONNX_PACKAGE=onnxruntime-gpu"
)

echo.
echo ==========================================
echo Configuration Selected:
echo   Mode:         %VENV_NAME%
echo   Torch URL:    %TORCH_INDEX_URL%
echo   ONNX Package: %ONNX_PACKAGE%
echo ==========================================
echo.

echo ------------------------------------------
echo Step 1: Locate Python 3.10
echo ------------------------------------------
set "PY_CMD="

rem Prefer the launcher explicitly targeting 3.10
py -3.10 --version >nul 2>&1
if %ERRORLEVEL% EQU 0 set "PY_CMD=py -3.10"

rem Fallback: check that bare "python" is exactly 3.10.x
if not defined PY_CMD (
    python -c "import sys; sys.exit(0 if sys.version_info[0]==3 and sys.version_info[1]==10 else 1)" >nul 2>&1
    if %ERRORLEVEL% EQU 0 set "PY_CMD=python"
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
call "%VENV_NAME%\Scripts\activate.bat"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to activate virtual environment.
    goto end
)

echo ------------------------------------------
echo Step 3: Install / update dependencies
echo ------------------------------------------
echo.

echo Checking for FFmpeg...
where ffmpeg >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo FFmpeg found.
) else (
    echo WARNING: FFmpeg not found on PATH.
    echo audio-separator and demucs require FFmpeg to function.
    echo.
    call :handle_ffmpeg_missing
)

rem ------------------------------------------
rem Setup Install Command (uv vs pip)
rem ------------------------------------------
rem Default to standard pip
set "PIP_INSTALL_CMD=python -m pip install"

echo Checking for 'uv' (fast package installer)...
python -m pip install uv >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo 'uv' installed successfully. Using uv for fast installation.
    set "PIP_INSTALL_CMD=uv pip install"
) else (
    echo 'uv' installation failed or skipped. Falling back to standard pip.
    echo Upgrading pip...
    python -m pip install --upgrade pip >nul
)

rem ------------------------------------------
rem Install Packages
rem ------------------------------------------

echo.
echo Installing core packages (PyQt6, soundfile)...
%PIP_INSTALL_CMD% PyQt6 soundfile || goto end

echo.
echo Installing PyTorch...
%PIP_INSTALL_CMD% torch torchvision torchaudio --index-url %TORCH_INDEX_URL% || goto end

echo.
echo Installing Demucs, Audio Separator, PyInstaller, and %ONNX_PACKAGE%...
%PIP_INSTALL_CMD% demucs audio-separator pyinstaller %ONNX_PACKAGE% || goto end

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

rem 1. Set the name first so we can use it for cleanup
set "PYI_NAME=StemLab"

rem 2. Clean up previous artifacts
echo Cleaning previous build artifacts...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "%PYI_NAME%.spec" del "%PYI_NAME%.spec"

rem 3. Check for version file and set argument accordingly
set "PYI_VERSION_FILE="
if exist "version_info.txt" (
    rem Escape the quotes around the filename
    set "PYI_VERSION_FILE=--version-file ^\"version_info.txt^\""
)

rem 4. Invoke PyInstaller.  Note: caret at end of lines must not have trailing spaces.
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

if %ERRORLEVEL% NEQ 0 (
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
rem Handle an existing virtual environment based on flags or interactive prompt
if defined ARG_RECREATE_VENV (
    echo Recreating venv because --recreate-venv was specified...
    rmdir /s /q "%VENV_NAME%"
    if exist "%VENV_NAME%" (
        echo ERROR: Could not remove existing venv. Is a process using it?
        goto end
    )

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
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create virtual environment.
)
goto :eof


:ask_build_exe
echo.
set /p CHOICE_BUILD=Build standalone StemLab.exe with PyInstaller now? [y/N]: 
if /I "%CHOICE_BUILD%"=="Y" set "DO_BUILD_EXE=1"
goto :eof


:handle_ffmpeg_missing
rem Decide how to handle missing FFmpeg based on flags or interactive prompt.
rem If --install-ffmpeg is supplied, attempt installation automatically.
if defined ARG_INSTALL_FFMPEG (
    echo Installing FFmpeg via winget...
    call :install_ffmpeg
    goto :eof
)
rem If --no-install-ffmpeg is supplied, skip installation.
if defined ARG_NO_INSTALL_FFMPEG (
    echo Skipping FFmpeg installation due to flag. You should install it manually or via a package manager.
    goto :eof
)
rem In CI or non-interactive environments, do not prompt.
if defined CI (
    echo Non-interactive environment detected. Skipping FFmpeg installation prompt.
    goto :eof
)
rem Otherwise ask the user interactively.
set /p CHOICE_FFMPEG=Install FFmpeg now via winget? [y/N]: 
if /I "%CHOICE_FFMPEG%"=="Y" (
    call :install_ffmpeg
) else (
    echo Not installing FFmpeg. Some features may crash until FFmpeg is installed.
)
goto :eof

:install_ffmpeg
rem Check if winget is available
winget --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: winget is not available on this system. Please install FFmpeg manually or install winget first.
    goto :eof
)
echo Attempting to install FFmpeg version %FFMPEG_VERSION% using winget...
rem Use silent mode and accept agreements for unattended installation
winget install ffmpeg --version %FFMPEG_VERSION% --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
if %ERRORLEVEL% EQU 0 (
    echo FFmpeg installation completed. Ensure the ffmpeg executable directory is in your PATH.
) else (
    echo ERROR: winget failed to install FFmpeg. Install it manually or fix winget issues.
)
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
echo   --install-ffmpeg     Automatically install FFmpeg via winget if missing.
echo   --no-install-ffmpeg  Do not install FFmpeg even if it is missing.
echo.
echo Without --cpu/--gpu, you will be prompted interactively for CPU vs GPU.
echo.
echo Examples:
echo   %~nx0 --cpu --recreate-venv --no-build-exe
echo   %~nx0 --gpu --reuse-venv --build-exe
goto end


:end
echo.
if not defined CI pause
endlocal
exit /b

#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "StemLab Setup / Build Script (Linux/macOS)"
echo "=========================================="
echo

# Always run from the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="venv_cpu"

# --------------------------------------------------
# Argument parsing
# --------------------------------------------------
ARG_CPU=""
ARG_GPU=""
ARG_BUILD_EXE=""
ARG_NO_BUILD_EXE=""
ARG_RECREATE_VENV=""
ARG_REUSE_VENV=""

show_help() {
  cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --cpu             Use CPU-only PyTorch (default if no choice given)
  --gpu             Use GPU (CUDA/cu121) PyTorch
  --recreate-venv   Recreate venv_cpu if it exists
  --reuse-venv      Reuse existing venv_cpu if it exists
  --build-exe       Build StemLab binary with PyInstaller
  --no-build-exe    Do not build binary; just set up environment
  --help            Show this help

Examples:
  $(basename "$0") --cpu --recreate-venv --no-build-exe
  $(basename "$0") --gpu --reuse-venv --build-exe
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cpu)           ARG_CPU=1 ;;
    --gpu)           ARG_GPU=1 ;;
    --build-exe)     ARG_BUILD_EXE=1 ;;
    --no-build-exe)  ARG_NO_BUILD_EXE=1 ;;
    --recreate-venv) ARG_RECREATE_VENV=1 ;;
    --reuse-venv)    ARG_REUSE_VENV=1 ;;
    --help)          show_help; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      show_help
      exit 1
      ;;
  esac
  shift
done

# --------------------------------------------------
# Step 1: Locate Python (prefer python3)
# --------------------------------------------------
if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "ERROR: python3 or python not found on PATH." >&2
  exit 1
fi

PYTHON_VERSION="$("$PYTHON" - <<'EOF'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
EOF
)"

echo "Detected Python: $PYTHON_VERSION via '$PYTHON'"

case "$PYTHON_VERSION" in
  3.10|3.11|3.12)
    ;;
  *)
    echo "WARNING: StemLab was tested with Python 3.10; you're using $PYTHON_VERSION."
    echo "         If you hit odd issues, try Python 3.10."
    ;;
esac

# --------------------------------------------------
# Step 2: Create or reuse virtualenv
# --------------------------------------------------
if [[ -d "$VENV_DIR" ]]; then
  echo "Virtualenv '$VENV_DIR' already exists."

  if [[ -n "$ARG_RECREATE_VENV" ]]; then
    echo "Recreating venv because --recreate-venv was specified..."
    rm -rf "$VENV_DIR"
  elif [[ -n "$ARG_REUSE_VENV" ]]; then
    echo "Reusing existing venv because --reuse-venv was specified..."
  else
    read -r -p "Reuse it instead of recreating? [Y/n]: " REUSE_VENV
    if [[ "$REUSE_VENV" =~ ^[Nn]$ ]]; then
      echo "Removing old '$VENV_DIR'..."
      rm -rf "$VENV_DIR"
    else
      echo "Reusing existing environment."
    fi
  fi
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating virtual environment in '$VENV_DIR'..."
  "$PYTHON" -m venv "$VENV_DIR"
fi

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
  echo "ERROR: Cannot find '$VENV_DIR/bin/activate'." >&2
  exit 1
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo
echo "Upgrading pip..."
python -m pip install --upgrade pip

# --------------------------------------------------
# Step 3: Install dependencies (CPU/GPU)
# --------------------------------------------------
TORCH_INDEX_URL=""

if [[ -n "$ARG_GPU" ]]; then
  TORCH_INDEX_URL="https://download.pytorch.org/whl/cu121"
elif [[ -n "$ARG_CPU" ]]; then
  TORCH_INDEX_URL="https://download.pytorch.org/whl/cpu"
else
  echo
  read -r -p "Install GPU-accelerated PyTorch (NVIDIA / CUDA) instead of CPU-only? [y/N]: " USE_GPU
  if [[ "$USE_GPU" =~ ^[Yy]$ ]]; then
    TORCH_INDEX_URL="https://download.pytorch.org/whl/cu121"
  else
    TORCH_INDEX_URL="https://download.pytorch.org/whl/cpu"
  fi
fi

echo
echo "Installing core packages (PyQt6, soundfile)..."
python -m pip install PyQt6 soundfile

echo
echo "Installing PyTorch from '$TORCH_INDEX_URL'..."
python -m pip install torch torchvision torchaudio --index-url "$TORCH_INDEX_URL"

echo
echo "Installing Demucs, Audio Separator, PyInstaller, ONNX Runtime..."
python -m pip install demucs audio-separator pyinstaller onnxruntime

echo
echo "Dependencies installed successfully."

# --------------------------------------------------
# Step 4: Optional PyInstaller build
# --------------------------------------------------
DO_BUILD_EXE=""

if [[ -n "$ARG_BUILD_EXE" ]]; then
  DO_BUILD_EXE=1
elif [[ -n "$ARG_NO_BUILD_EXE" ]]; then
  DO_BUILD_EXE=""
else
  echo
  read -r -p "Build a standalone StemLab binary with PyInstaller now? [y/N]: " BUILD_EXE
  if [[ "$BUILD_EXE" =~ ^[Yy]$ ]]; then
    DO_BUILD_EXE=1
  fi
fi

if [[ -z "$DO_BUILD_EXE" ]]; then
  echo
  echo "Skipping PyInstaller build."
  echo "To run StemLab from source on this machine:"
  echo "  source $VENV_DIR/bin/activate"
  echo "  python main.py"
  exit 0
fi

NAME="StemLab"
VERSION_FILE_ARGS=()
if [[ -f "version_info.txt" ]]; then
  VERSION_FILE_ARGS=(--version-file version_info.txt)
fi

echo
echo "Building PyInstaller binary (no .exe suffix on *nix)..."

pyinstaller --clean --noconsole --onefile \
  --name "$NAME" \
  "${VERSION_FILE_ARGS[@]}" \
  --add-data "src:src" \
  --add-data "resources:resources" \
  --collect-all demucs \
  --collect-all torchaudio \
  --collect-all soundfile \
  --collect-all numpy \
  --hidden-import="PyQt6" \
  --hidden-import="sklearn.utils._cython_blas" \
  --hidden-import="sklearn.neighbors.typedefs" \
  --hidden-import="sklearn.neighbors.quad_tree" \
  --hidden-import="sklearn.tree._utils" \
  main.py

echo
echo "Build complete. Binary should be at: dist/$NAME"
echo
echo "To run StemLab from source:"
echo "  source $VENV_DIR/bin/activate"
echo "  python main.py"

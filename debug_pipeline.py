import sys
import os
import logging
import shutil

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

print("Python Version:", sys.version)
print("Current Directory:", os.getcwd())

def check_ffmpeg():
    print("\n--- Checking FFmpeg ---")
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        print(f"FFmpeg found at: {ffmpeg_path}")
        return True
    else:
        print("ERROR: FFmpeg not found in PATH!")
        return False

def test_imports():
    print("\n--- Testing Imports ---")
    try:
        import torch
        print(f"PyTorch Version: {torch.__version__}")
    except ImportError as e:
        print(f"Failed to import torch: {e}")

    try:
        import demucs.separate
        print("Demucs imported successfully")
    except ImportError as e:
        print(f"Failed to import demucs: {e}")

    try:
        from audio_separator.separator import Separator
        print("Audio Separator imported successfully")
    except ImportError as e:
        print(f"Failed to import audio_separator: {e}")
        
    try:
        from src.core.advanced_audio import AdvancedAudioProcessor
        print("AdvancedAudioProcessor imported successfully")
    except ImportError as e:
        print(f"Failed to import AdvancedAudioProcessor: {e}")
        import traceback
        traceback.print_exc()

def test_initialization():
    print("\n--- Testing Initialization ---")
    try:
        from src.core.advanced_audio import AdvancedAudioProcessor
        processor = AdvancedAudioProcessor("test_output")
        print("AdvancedAudioProcessor initialized successfully")
    except Exception as e:
        print(f"Failed to initialize AdvancedAudioProcessor: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_ffmpeg()
    test_imports()
    test_initialization()

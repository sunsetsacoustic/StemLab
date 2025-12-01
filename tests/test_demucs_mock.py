import sys
from unittest.mock import MagicMock

# Mock lameenc
sys.modules["lameenc"] = MagicMock()

try:
    import demucs
    print("Demucs imported successfully!")
    import demucs.separate
    print("Demucs.separate imported successfully!")
except Exception as e:
    print(f"Import failed: {e}")

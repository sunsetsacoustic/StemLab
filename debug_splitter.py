import sys
import os
from unittest.mock import MagicMock

# Mock lameenc
sys.modules["lameenc"] = MagicMock()

import demucs.separate
import torch
import torchaudio

import soundfile as sf

# Force soundfile backend by monkeypatching load
def custom_load(filepath, *args, **kwargs):
    # Ignore extra args, just load the file
    wav, sr = sf.read(filepath)
    wav = torch.tensor(wav).float()
    if wav.ndim == 1:
        wav = wav.unsqueeze(0)
    else:
        wav = wav.t() # soundfile returns (time, channels), torch expects (channels, time)
    return wav, sr

torchaudio.load = custom_load

def custom_save(filepath, src, sample_rate, **kwargs):
    # src is (channels, time)
    # soundfile expects (time, channels)
    src = src.detach().cpu().t().numpy()
    sf.write(filepath, src, sample_rate)

torchaudio.save = custom_save


def test_splitter():
    print("Starting Debug Splitter...")
    
    # Use the dummy file or create one
    if not os.path.exists("test_audio.wav"):
        import numpy as np
        import soundfile as sf
        sr = 44100
        duration = 5
        data = np.random.uniform(-0.1, 0.1, size=(sr * duration, 2))
        sf.write("test_audio.wav", data, sr)
    
    file_path = os.path.abspath("test_audio.wav")
    output_dir = os.path.join(os.path.dirname(file_path), "test_audio - Stems")
    
    args = [
        "-n", "htdemucs",
        "--shifts", "0",
        "-o", output_dir,
        "--filename", "{track}/{stem}.{ext}",
        file_path
    ]
    
    if not torch.cuda.is_available():
        args.append("-d")
        args.append("cpu")
        
    print(f"Running Demucs with args: {args}")
    
    try:
        demucs.separate.main(args)
        print("Demucs finished successfully.")
    except Exception as e:
        print(f"Demucs failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_splitter()

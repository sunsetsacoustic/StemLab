import numpy as np
import soundfile as sf

# Generate 5 seconds of silence/noise
sr = 44100
duration = 5
data = np.random.uniform(-0.1, 0.1, size=(sr * duration, 2))
sf.write("test_audio.wav", data, sr)
print("Created test_audio.wav")

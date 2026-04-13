import sounddevice as sd
import numpy as np

print("Micrófonos disponibles:")
print(sd.query_devices())

print("\nGrabando 3 segundos...")
duration = 3
recording = sd.rec(int(duration * 16000), samplerate=16000, channels=1, dtype='int16')
sd.wait()
print("Grabación completada. Nivel máximo:", np.max(np.abs(recording)))
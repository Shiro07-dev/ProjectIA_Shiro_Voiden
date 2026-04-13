import os
import sys
from pathlib import Path

def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_dir()

# Ruta del modelo Vosk (cámbiala si es diferente)
MODEL_PATH = os.path.join(BASE_DIR, "vosk-model-es", "vosk-model-small-es-0.42")

# Palabra de activación (en minúsculas, sin acentos)
WAKE_WORD = "veronica"

# Configuración de audio
SAMPLE_RATE = 16000
BLOCKSIZE = 8000
TIMEOUT_LISTEN = 5  # segundos para escuchar comando después de wake word

# Archivo de logs
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
"""
Asistente offline: dice "jarvis" + comando seguido, lo ejecuta directamente.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from offline.tts_local import TTSLocal
from offline.wake_word import WakeWordListener
from offline.ia_api import JarvisIA, ejecutar_accion

def main():
    print("Iniciando asistente offline...")
    tts = TTSLocal()
    wake = WakeWordListener()
    ia = JarvisIA()
    
    tts.speak("Asistente activado. Diga Jarvis seguido de su orden.")
    
    while True:
        try:
            detected, comando = wake.listen_for_command()
            if detected and comando:
                print(f"Procesando: {comando}")
                respuesta_json = ia.interpretar(comando)
                data = json.loads(respuesta_json)
                ejecutar_accion(data, tts)
            else:
                # Si no se detectó comando, esperar de nuevo
                continue
        except KeyboardInterrupt:
            print("\nSaliendo...")
            tts.speak("Hasta luego.")
            break
        except Exception as e:
            print(f"Error: {e}")
            tts.speak("Ocurrió un error.")

if __name__ == "__main__":
    main()
"""
Wake Word + comando continuo. Detecta "jarvis" y captura lo que sigue.
Mejorado: ignora silencios muy cortos, extrae mejor el comando.
"""
import vosk
import sounddevice as sd
import queue
import json
import time
from pathlib import Path

vosk.SetLogLevel(-1)

class WakeWordListener:
    def __init__(self, model_path=None):
        if model_path is None:
            base = Path(__file__).parent.parent
            candidates = [
                base / "vosk-model-es" / "vosk-model-small-es-0.42",
                base / "vosk-model-small-es-0.42",
            ]
            for p in candidates:
                if p.exists():
                    model_path = str(p)
                    break
            else:
                raise FileNotFoundError("Modelo Vosk no encontrado.")
        self.model = vosk.Model(model_path)
        self.samplerate = 16000
        self.q = queue.Queue()
        self.wake_word = "jarvis"  # palabra clave
    
    def _callback(self, indata, frames, time, status):
        self.q.put(bytes(indata))
    
    def listen_for_command(self, timeout=5):
        """
        Escucha continuamente. Cuando detecta 'jarvis', sigue escuchando
        hasta que haya silencio (o timeout) y retorna el comando completo.
        Retorna (detectado, comando)
        """
        print(f"\n🎤 Escuchando ('{self.wake_word}' + comando)...")
        with sd.RawInputStream(samplerate=self.samplerate, blocksize=8000,
                               dtype='int16', channels=1, callback=self._callback):
            rec = vosk.KaldiRecognizer(self.model, self.samplerate)
            wake_detected = False
            accumulated = ""
            silence_start = None
            start_time = time.time()
            
            while True:
                data = self.q.get()
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get('text', '').lower()
                    if text:
                        if not wake_detected:
                            if self.wake_word in text:
                                wake_detected = True
                                # Extraer comando después de la wake word
                                idx = text.find(self.wake_word) + len(self.wake_word)
                                accumulated = text[idx:].strip()
                                silence_start = None
                                print(f"✅ Wake word detectada. Comando: '{accumulated}'")
                            else:
                                # No es wake word, ignorar
                                pass
                        else:
                            # Ya detectada, acumular todo el texto
                            accumulated += " " + text
                            silence_start = None
                else:
                    partial = json.loads(rec.PartialResult())
                    part = partial.get('partial', '').lower()
                    if part:
                        if not wake_detected:
                            if self.wake_word in part:
                                wake_detected = True
                                idx = part.find(self.wake_word) + len(self.wake_word)
                                accumulated = part[idx:].strip()
                                silence_start = None
                                print(f"✅ Wake word detectada. Comando parcial: '{accumulated}'")
                            else:
                                # Mostrar solo si hay algo (para depuración)
                                if len(part) > 2:
                                    print(f"[PARCIAL] {part}", end='\r')
                        else:
                            # Actualizar comando parcial
                            accumulated = part
                            silence_start = None
                            print(f"⏺ Comando: '{accumulated}'", end='\r')
                    
                    # Detectar silencio después de la wake word
                    if wake_detected and not part:
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > 1.0:  # 1 segundo de silencio
                            print("\n✅ Comando completo capturado.")
                            return True, accumulated.strip()
                    else:
                        silence_start = None
                    
                    # Timeout global
                    if wake_detected and (time.time() - start_time) > timeout:
                        print("\n⏰ Timeout. Procesando comando parcial.")
                        return True, accumulated.strip()
                
                if not wake_detected and (time.time() - start_time) > timeout * 2:
                    # No se detectó wake word después de un tiempo, reiniciar
                    return False, ""

if __name__ == "__main__":
    ww = WakeWordListener()
    detected, cmd = ww.listen_for_command()
    if detected:
        print(f"Comando final: '{cmd}'")
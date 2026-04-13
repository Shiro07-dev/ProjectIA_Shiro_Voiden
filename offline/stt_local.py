"""
STT offline usando Vosk.
"""
import vosk
import sounddevice as sd
import queue
import json
import time

class STTLocal:
    def __init__(self, model_path=None):
        from .wake_word import WakeWordListener
        temp = WakeWordListener(model_path)
        self.model = temp.model
        self.samplerate = 16000
        self.q = queue.Queue()
    
    def _callback(self, indata, frames, time, status):
        self.q.put(bytes(indata))
    
    def transcribe(self, segundos=5):
        print(f"🎙️ Escuchando por {segundos} segundos...")
        with sd.RawInputStream(samplerate=self.samplerate, blocksize=8000,
                               dtype='int16', channels=1, callback=self._callback):
            rec = vosk.KaldiRecognizer(self.model, self.samplerate)
            texto = []
            start = time.time()
            while time.time() - start < segundos:
                try:
                    data = self.q.get(timeout=0.5)
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        t = result.get('text', '')
                        if t:
                            texto.append(t)
                except queue.Empty:
                    continue
            # Resultado final
            final = json.loads(rec.FinalResult())
            if final.get('text'):
                texto.append(final['text'])
            resultado = ' '.join(texto).strip()
            print(f"📝 Transcripción: '{resultado}'")
            return resultado

if __name__ == "__main__":
    stt = STTLocal()
    stt.transcribe(4)
"""
TTS Local usando pyttsx3 (funciona con Windows)
"""
import pyttsx3
import time

class TTSLocal:
    def __init__(self):
        self.engine = None
        self._init_engine()
    
    def _init_engine(self):
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 1.0)
            # Intentar seleccionar voz en español
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if 'spanish' in voice.name.lower() or 'español' in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
            print("[TTS] ✅ pyttsx3 listo")
        except Exception as e:
            print(f"[TTS] Error: {e}")
            self.engine = None
    
    def speak(self, text):
        if not text:
            return False
        print(f"[Javier] {text}")   # Siempre se imprime
        if self.engine is None:
            return False
        try:
            self.engine.say(text)
            self.engine.runAndWait()
            time.sleep(0.2)
            return True
        except Exception as e:
            print(f"[TTS] Error al hablar: {e}")
            return False
"""
Intérprete de comandos local (offline) con NLP difuso.
Reconoce intenciones en lenguaje natural sin frases exactas.
"""
import json
import re
import datetime
import subprocess
import platform
import webbrowser
import os
from pathlib import Path
from rapidfuzz import fuzz, process

try:
    import pyautogui
    PYAUTOGUI_OK = True
except ImportError:
    PYAUTOGUI_OK = False

# ============================================================
# INTENCIONES con palabras clave y acción asociada
# ============================================================
INTENCIONES = [
    # --- Abrir aplicaciones (cualquier frase que contenga abrir + algo) ---
    {"palabras": ["abre", "abrir", "ábreme", "inicia", "ejecuta", "lanzar", "open", "launch"], "accion": "abrir_aplicacion", "necesita_objeto": True},
    
    # --- Cerrar aplicaciones ---
    {"palabras": ["cierra", "cerrar", "mata", "termina", "close", "kill"], "accion": "cerrar_aplicacion", "necesita_objeto": True},
    
    # --- Volumen ---
    {"palabras": ["sube", "subir", "aumenta", "incrementa", "más volumen", "más sonido", "louder"], "accion": "ajustar_volumen", "params": {"cambio": 10}},
    {"palabras": ["baja", "bajar", "disminuye", "reduce", "menos volumen", "menos sonido", "softer"], "accion": "ajustar_volumen", "params": {"cambio": -10}},
    {"palabras": ["silencia", "mute", "silencio", "sin sonido"], "accion": "silenciar_audio"},
    {"palabras": ["activa sonido", "quita silencio", "unmute", "recupera sonido"], "accion": "quitar_silencio"},
    
    # --- Brillo ---
    {"palabras": ["sube brillo", "aumenta brillo", "más brillo", "brillante"], "accion": "ajustar_brillo", "params": {"cambio": 10}},
    {"palabras": ["baja brillo", "disminuye brillo", "menos brillo", "oscurece"], "accion": "ajustar_brillo", "params": {"cambio": -10}},
    
    # --- Multimedia ---
    {"palabras": ["pausa", "pausar", "para", "detén", "detener"], "accion": "multimedia", "params": {"tecla": "playpause"}},
    {"palabras": ["play", "reproduce", "continúa", "reanuda", "seguir"], "accion": "multimedia", "params": {"tecla": "playpause"}},
    {"palabras": ["siguiente", "próxima", "next", "cambiar canción", "otra canción"], "accion": "multimedia", "params": {"tecla": "nexttrack"}},
    {"palabras": ["anterior", "previo", "previous", "atrás", "regresar canción"], "accion": "multimedia", "params": {"tecla": "prevtrack"}},
    
    # --- Sistema (apagar, reiniciar) ---
    {"palabras": ["apagar", "shutdown", "power off", "apaga el pc", "apaga la computadora"], "accion": "apagar_equipo", "confirmar": True},
    {"palabras": ["reiniciar", "restart", "reinicar pc", "reinicia el equipo"], "accion": "reiniciar_equipo", "confirmar": True},
    {"palabras": ["bloquear pantalla", "lock screen", "bloquear pc", "bloquear equipo"], "accion": "bloquear_pantalla"},
    {"palabras": ["cerrar sesión", "log off", "sign out"], "accion": "cerrar_sesion", "confirmar": True},
    {"palabras": ["suspender", "sleep", "dormir", "suspende pc"], "accion": "suspender_equipo"},
    {"palabras": ["hibernar", "hibernate"], "accion": "hibernar_equipo"},
    
    # --- Ventanas ---
    {"palabras": ["minimizar todo", "minimizar todas", "show desktop", "ver escritorio", "escritorio limpio"], "accion": "minimizar_todo"},
    {"palabras": ["maximizar ventana", "maximizar", "expandir ventana"], "accion": "maximizar_ventana"},
    {"palabras": ["cerrar ventana", "close window", "cerrar esta ventana"], "accion": "cerrar_ventana_activa"},
    
    # --- Teclado ---
    {"palabras": ["presiona", "pulsa", "press", "toca", "aprieta"], "accion": "presionar_tecla", "necesita_objeto": True},
    {"palabras": ["escribe", "type", "teclea", "escribir"], "accion": "escribir_texto", "necesita_objeto": True},
    
    # --- Captura de pantalla ---
    {"palabras": ["captura pantalla", "saca captura", "screenshot", "foto pantalla", "imagen pantalla"], "accion": "captura_pantalla"},
    
    # --- Carpetas ---
    {"palabras": ["abre descargas", "abrir descargas", "ve a descargas"], "accion": "abrir_carpeta", "params": {"carpeta": "downloads"}},
    {"palabras": ["abre documentos", "abrir documentos", "mis documentos"], "accion": "abrir_carpeta", "params": {"carpeta": "documents"}},
    {"palabras": ["abre escritorio", "abrir escritorio", "ver escritorio"], "accion": "abrir_carpeta", "params": {"carpeta": "desktop"}},
    {"palabras": ["abre imágenes", "abrir imágenes", "mis fotos"], "accion": "abrir_carpeta", "params": {"carpeta": "pictures"}},
    {"palabras": ["abre vídeos", "abrir videos", "mis videos"], "accion": "abrir_carpeta", "params": {"carpeta": "videos"}},
    {"palabras": ["abre música", "abrir música", "mi música"], "accion": "abrir_carpeta", "params": {"carpeta": "music"}},
    
    # --- Web ---
    {"palabras": ["abre youtube", "abrir youtube", "youtube", "ve a youtube"], "accion": "abrir_url", "params": {"url": "https://www.youtube.com"}},
    {"palabras": ["abre google", "abrir google", "google", "ve a google"], "accion": "abrir_url", "params": {"url": "https://www.google.com"}},
    {"palabras": ["abre gmail", "abrir gmail", "correo gmail"], "accion": "abrir_url", "params": {"url": "https://mail.google.com"}},
    {"palabras": ["abre github", "abrir github", "github"], "accion": "abrir_url", "params": {"url": "https://github.com"}},
    
    # --- Hora y fecha ---
    {"palabras": ["qué hora es", "hora actual", "dime la hora", "que hora", "hora"], "accion": "decir_hora"},
    {"palabras": ["qué fecha es", "fecha actual", "dime la fecha", "que fecha", "fecha"], "accion": "decir_fecha"},
    
    # --- Conversación ---
    {"palabras": ["hola", "buenos días", "buenas tardes", "buenas noches", "hey", "saludos"], "accion": "saludo", "resp": "¡Hola! ¿En qué puedo ayudarte?"},
    {"palabras": ["gracias", "thank you", "thanks", "agradecido"], "accion": "respuesta", "resp": "De nada."},
    {"palabras": ["adiós", "chao", "bye", "hasta luego", "nos vemos"], "accion": "despedida", "resp": "Hasta luego. Estaré aquí cuando me necesites."},
    {"palabras": ["qué puedes hacer", "capacidades", "funciones", "que sabes hacer", "ayuda"], "accion": "capacidades", "resp": "Puedo abrir y cerrar aplicaciones, controlar volumen y brillo, multimedia, capturar pantalla, darte la hora, abrir carpetas, escribir texto, presionar teclas, y controlar ventanas."},
    {"palabras": ["quién eres", "tu nombre", "como te llamas", "presentate"], "accion": "identidad", "resp": "Soy Jarvis, tu asistente offline. Estoy aquí para ayudarte a controlar tu PC."},
]

# Aplicaciones conocidas (para abrir/cerrar)
APPS = {
    "spotify": "spotify",
    "chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "discord": "Discord",
    "telegram": "Telegram",
    "whatsapp": "WhatsApp",
    "steam": "steam",
    "code": "code",
    "vs code": "code",
    "visual studio code": "code",
    "notepad": "notepad.exe",
    "bloc de notas": "notepad.exe",
    "calculadora": "calc.exe",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "cmd": "cmd.exe",
    "terminal": "cmd.exe",
    "powershell": "powershell.exe",
    "explorador": "explorer.exe",
    "explorer": "explorer.exe",
    "paint": "mspaint.exe",
    "vlc": "vlc",
    "zoom": "zoom",
    "teams": "teams",
    "outlook": "outlook",
}

# Lista plana de frases de intención para matching difuso
INTENCIONES_FLAT = []
for i, intencion in enumerate(INTENCIONES):
    for frase in intencion["palabras"]:
        INTENCIONES_FLAT.append((frase, i))

class JarvisIA:
    def __init__(self):
        pass
    
    def _extraer_intencion(self, texto):
        """Usa fuzzy matching para encontrar la intención más cercana."""
        texto = texto.lower().strip()
        # Buscar coincidencia difusa con las frases clave
        mejor = process.extractOne(texto, [frase for frase, _ in INTENCIONES_FLAT], scorer=fuzz.partial_ratio)
        if mejor and mejor[1] > 70:  # Umbral de similitud 70%
            frase_match, indice = INTENCIONES_FLAT[mejor[2]]
            intencion = INTENCIONES[indice]
            accion = intencion["accion"]
            params = intencion.get("params", {}).copy()
            respuesta = intencion.get("resp", "")
            confirmar = intencion.get("confirmar", False)
            
            # Si la intención necesita un objeto (nombre de app, tecla, texto)
            if intencion.get("necesita_objeto", False):
                # Extraer posible objeto (palabra después de la acción)
                # Buscar la parte que no coincide con la frase clave
                resto = texto.replace(frase_match, "").strip()
                if resto:
                    # Si es abrir/cerrar, buscar en apps conocidas o tomar lo que sigue
                    if accion in ["abrir_aplicacion", "cerrar_aplicacion"]:
                        # Buscar la app más cercana en la lista de APPS
                        app_match = process.extractOne(resto, list(APPS.keys()), scorer=fuzz.partial_ratio)
                        if app_match and app_match[1] > 60:
                            params["app"] = app_match[0] if accion == "abrir_aplicacion" else app_match[0]
                        else:
                            params["app"] = resto.split()[0] if resto else ""
                    elif accion == "presionar_tecla":
                        params["tecla"] = resto.split()[0] if resto else "enter"
                    elif accion == "escribir_texto":
                        params["texto"] = resto
                else:
                    # Si no hay objeto, quizás la frase completa ya contiene el objeto (ej: "abre chrome")
                    # Intentar extraer con regex simple
                    if accion in ["abrir_aplicacion", "cerrar_aplicacion"]:
                        # Buscar cualquier palabra que pueda ser una app
                        palabras = texto.split()
                        for p in palabras:
                            if p in APPS:
                                params["app"] = p
                                break
                        if "app" not in params:
                            # Tomar la última palabra
                            params["app"] = palabras[-1] if palabras else ""
            return accion, params, respuesta, confirmar
        return None, None, None, None
    
    def interpretar(self, texto):
        if not texto:
            return json.dumps({"accion": "no_entendido", "respuesta": "No he escuchado nada."})
        
        accion, params, respuesta, confirmar = self._extraer_intencion(texto)
        if accion:
            resultado = {
                "accion": accion,
                "parametros": params or {},
                "respuesta": respuesta or "",
                "confirmacion": confirmar or False
            }
            if accion == "decir_hora":
                ahora = datetime.datetime.now()
                resultado["respuesta"] = f"Son las {ahora.strftime('%H:%M')}."
            elif accion == "decir_fecha":
                ahora = datetime.datetime.now()
                resultado["respuesta"] = f"Hoy es {ahora.strftime('%d/%m/%Y')}."
            return json.dumps(resultado)
        
        # Fallback: si no hay coincidencia, intentar extraer "abrir X" simple
        match = re.search(r'\b(abre|abrir|ábreme|inicia)\s+([a-záéíóúñ]+)', texto.lower())
        if match:
            app = match.group(2)
            return json.dumps({
                "accion": "abrir_aplicacion",
                "parametros": {"app": app},
                "respuesta": f"Abriendo {app}."
            })
        
        return json.dumps({"accion": "no_entendido", "respuesta": "No entendí el comando."})

# ============================================================
# EJECUCIÓN DE ACCIONES (igual que antes, pero la incluyo por completitud)
# ============================================================
def ejecutar_accion(data, tts):
    accion = data.get("accion")
    params = data.get("parametros", {})
    respuesta = data.get("respuesta", "")
    confirmar = data.get("confirmacion", False)
    
    if respuesta:
        tts.speak(respuesta)
    
    if confirmar:
        tts.speak("¿Desea continuar? Diga sí o no.")
        # Aquí podrías implementar escucha de confirmación
        tts.speak("Procediendo.")
    
    if accion == "abrir_aplicacion":
        app = params.get("app", "")
        abrir_app(app)
    elif accion == "cerrar_aplicacion":
        proceso = params.get("proceso", "")
        cerrar_app(proceso)
    elif accion == "ajustar_volumen":
        ajustar_volumen(params.get("cambio", 10))
    elif accion == "silenciar_audio":
        silenciar_audio()
    elif accion == "quitar_silencio":
        quitar_silencio()
    elif accion == "ajustar_brillo":
        ajustar_brillo(params.get("cambio", 10))
    elif accion == "multimedia":
        enviar_tecla_multimedia(params.get("tecla", "playpause"))
    elif accion == "apagar_equipo":
        subprocess.run(["shutdown", "/s", "/t", "10"])
    elif accion == "reiniciar_equipo":
        subprocess.run(["shutdown", "/r", "/t", "10"])
    elif accion == "bloquear_pantalla":
        if platform.system() == "Windows":
            import ctypes
            ctypes.windll.user32.LockWorkStation()
    elif accion == "cerrar_sesion":
        subprocess.run(["shutdown", "/l"])
    elif accion == "suspender_equipo":
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"])
    elif accion == "hibernar_equipo":
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "1", "1", "0"])
    elif accion == "minimizar_todo":
        if PYAUTOGUI_OK:
            pyautogui.hotkey("win", "d")
    elif accion == "maximizar_ventana":
        if PYAUTOGUI_OK:
            pyautogui.hotkey("win", "up")
    elif accion == "cerrar_ventana_activa":
        if PYAUTOGUI_OK:
            pyautogui.hotkey("alt", "f4")
    elif accion == "presionar_tecla":
        tecla = params.get("tecla", "")
        if tecla and PYAUTOGUI_OK:
            pyautogui.press(tecla)
    elif accion == "escribir_texto":
        texto = params.get("texto", "")
        if texto and PYAUTOGUI_OK:
            pyautogui.write(texto)
    elif accion == "captura_pantalla":
        tomar_captura()
    elif accion == "abrir_carpeta":
        carpeta = params.get("carpeta", "")
        abrir_carpeta_especial(carpeta)
    elif accion == "abrir_url":
        url = params.get("url")
        webbrowser.open(url)
    elif accion in ("saludo", "respuesta", "despedida", "capacidades", "identidad", "no_entendido", "buscar_respuesta"):
        pass
    else:
        tts.speak("Acción no implementada.")

# ------------------------------------------------------------
# Funciones auxiliares (las mismas que antes)
# ------------------------------------------------------------
def abrir_app(nombre):
    nombre = nombre.lower().strip()
    comando = APPS.get(nombre, nombre)
    try:
        subprocess.Popen(comando, shell=True)
        print(f"[Acción] Abriendo {nombre}")
    except Exception as e:
        print(f"Error abriendo {nombre}: {e}")

def cerrar_app(nombre):
    nombre = nombre.lower().strip()
    comando = APPS.get(nombre, nombre)
    try:
        subprocess.run(f"taskkill /f /im {comando}.exe", shell=True, capture_output=True)
        print(f"[Acción] Cerrando {nombre}")
    except Exception as e:
        print(f"Error cerrando {nombre}: {e}")

def ajustar_volumen(cambio):
    if PYAUTOGUI_OK:
        tecla = "volumeup" if cambio > 0 else "volumedown"
        for _ in range(abs(cambio)//2):
            pyautogui.press(tecla)
        print(f"[Acción] Volumen {'+' if cambio>0 else ''}{cambio}%")
    else:
        print("pyautogui no instalado")

def silenciar_audio():
    if PYAUTOGUI_OK:
        pyautogui.press("volumemute")
        print("[Acción] Silenciado")

def quitar_silencio():
    if PYAUTOGUI_OK:
        pyautogui.press("volumemute")
        print("[Acción] Sonido activado")

def ajustar_brillo(cambio):
    try:
        result = subprocess.run(
            ["powershell", "-Command", "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"],
            capture_output=True, text=True
        )
        if result.stdout.strip():
            current = int(result.stdout.strip())
            nuevo = max(0, min(100, current + cambio))
            subprocess.run(
                ["powershell", "-Command", f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{nuevo})"],
                capture_output=True
            )
            print(f"[Acción] Brillo {cambio:+}% → {nuevo}%")
    except Exception as e:
        print(f"Error brillo: {e}")

def enviar_tecla_multimedia(tecla):
    if PYAUTOGUI_OK:
        pyautogui.press(tecla)
        print(f"[Acción] Tecla multimedia: {tecla}")

def tomar_captura():
    if PYAUTOGUI_OK:
        import time
        nombre = f"captura_{time.strftime('%Y%m%d_%H%M%S')}.png"
        desktop = Path.home() / "Desktop"
        ruta = desktop / nombre
        pyautogui.screenshot(str(ruta))
        print(f"[Acción] Captura guardada en {ruta}")

def abrir_carpeta_especial(carpeta):
    carpetas = {
        "downloads": Path.home() / "Downloads",
        "documents": Path.home() / "Documents",
        "desktop": Path.home() / "Desktop",
        "pictures": Path.home() / "Pictures",
        "videos": Path.home() / "Videos",
        "music": Path.home() / "Music",
    }
    ruta = carpetas.get(carpeta.lower(), Path.home())
    if ruta.exists():
        os.startfile(str(ruta)) if platform.system() == "Windows" else webbrowser.open(str(ruta))
        print(f"[Acción] Abriendo carpeta {carpeta}")
    else:
        print(f"Carpeta {carpeta} no encontrada")
"""
Modo ONLINE con bajo consumo de internet.
Usa STT local (Vosk) para capturar voz, envía texto a Gemini,
recibe respuesta en texto y usa TTS local para hablar.
"""
import json
import time
import threading
from pathlib import Path

import google.generativeai as genai
from offline.stt_local import STTLocal
from offline.tts_local import TTSLocal
from offline.wake_word import WakeWordListener
from ui import JarvisUI

# Configuración
BASE_DIR = Path(__file__).resolve().parent
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH = BASE_DIR / "core" / "prompt.txt"

# Importar herramientas (asegúrate de que las rutas sean correctas)
from actions.flight_finder import flight_finder
from actions.open_app import open_app
from actions.weather_report import weather_action
from actions.send_message import send_message
from actions.reminder import reminder
from actions.computer_settings import computer_settings
from actions.screen_processor import screen_process
from actions.youtube_video import youtube_video
from actions.cmd_control import cmd_control
from actions.desktop import desktop_control
from actions.browser_control import browser_control
from actions.file_controller import file_controller
from actions.code_helper import code_helper
from actions.dev_agent import dev_agent
from actions.web_search import web_search as web_search_action
from actions.computer_control import computer_control
from actions.game_updater import game_updater

TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": "Opens an application",
        "parameters": {
            "type": "OBJECT",
            "properties": {"app_name": {"type": "STRING"}},
            "required": ["app_name"]
        }
    },
    {
        "name": "web_search",
        "description": "Searches the web for any information.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Search query"},
                "mode": {"type": "STRING", "description": "search (default) or compare"},
                "items": {"type": "ARRAY", "items": {"type": "STRING"}},
                "aspect": {"type": "STRING"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "weather_report",
        "description": "Gets real-time weather information for a city.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"city": {"type": "STRING"}},
            "required": ["city"]
        }
    },
    {
        "name": "send_message",
        "description": "Sends a text message via WhatsApp, Telegram, etc.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver": {"type": "STRING"},
                "message_text": {"type": "STRING"},
                "platform": {"type": "STRING"}
            },
            "required": ["receiver", "message_text", "platform"]
        }
    },
    {
        "name": "reminder",
        "description": "Sets a timed reminder using Windows Task Scheduler.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date": {"type": "STRING"},
                "time": {"type": "STRING"},
                "message": {"type": "STRING"}
            },
            "required": ["date", "time", "message"]
        }
    },
    {
        "name": "youtube_video",
        "description": "Controls YouTube.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play | summarize | get_info | trending"},
                "query": {"type": "STRING"},
                "save": {"type": "BOOLEAN"},
                "region": {"type": "STRING"},
                "url": {"type": "STRING"}
            },
            "required": []
        }
    },
    {
        "name": "screen_process",
        "description": "Captures and analyzes the screen or webcam image.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "angle": {"type": "STRING", "description": "'screen' or 'camera'"},
                "text": {"type": "STRING"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "computer_settings",
        "description": "Controls the computer: volume, brightness, window management, etc.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING"},
                "description": {"type": "STRING"},
                "value": {"type": "STRING"}
            },
            "required": []
        }
    },
    {
        "name": "browser_control",
        "description": "Controls the web browser.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING"},
                "url": {"type": "STRING"},
                "query": {"type": "STRING"},
                "selector": {"type": "STRING"},
                "text": {"type": "STRING"},
                "description": {"type": "STRING"},
                "direction": {"type": "STRING"},
                "key": {"type": "STRING"},
                "incognito": {"type": "BOOLEAN"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "file_controller",
        "description": "Manages files and folders.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING"},
                "path": {"type": "STRING"},
                "destination": {"type": "STRING"},
                "new_name": {"type": "STRING"},
                "content": {"type": "STRING"},
                "name": {"type": "STRING"},
                "extension": {"type": "STRING"},
                "count": {"type": "INTEGER"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "cmd_control",
        "description": "Runs CMD/terminal commands.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "task": {"type": "STRING"},
                "visible": {"type": "BOOLEAN"},
                "command": {"type": "STRING"}
            },
            "required": ["task"]
        }
    },
    {
        "name": "desktop_control",
        "description": "Controls the desktop: wallpaper, organize, clean, etc.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING"},
                "path": {"type": "STRING"},
                "url": {"type": "STRING"},
                "mode": {"type": "STRING"},
                "task": {"type": "STRING"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "code_helper",
        "description": "Writes, edits, explains, runs, or builds code files.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING"},
                "description": {"type": "STRING"},
                "language": {"type": "STRING"},
                "output_path": {"type": "STRING"},
                "file_path": {"type": "STRING"},
                "code": {"type": "STRING"},
                "args": {"type": "STRING"},
                "timeout": {"type": "INTEGER"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "dev_agent",
        "description": "Builds complete multi-file projects.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "description": {"type": "STRING"},
                "language": {"type": "STRING"},
                "project_name": {"type": "STRING"},
                "timeout": {"type": "INTEGER"}
            },
            "required": ["description"]
        }
    },
    {
        "name": "agent_task",
        "description": "Executes complex multi-step tasks.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "goal": {"type": "STRING"},
                "priority": {"type": "STRING"}
            },
            "required": ["goal"]
        }
    },
    {
        "name": "computer_control",
        "description": "Direct computer control: type, click, hotkeys, etc.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING"},
                "text": {"type": "STRING"},
                "x": {"type": "INTEGER"},
                "y": {"type": "INTEGER"},
                "keys": {"type": "STRING"},
                "key": {"type": "STRING"},
                "direction": {"type": "STRING"},
                "amount": {"type": "INTEGER"},
                "seconds": {"type": "NUMBER"},
                "title": {"type": "STRING"},
                "description": {"type": "STRING"},
                "type": {"type": "STRING"},
                "field": {"type": "STRING"},
                "clear_first": {"type": "BOOLEAN"},
                "path": {"type": "STRING"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "game_updater",
        "description": "Updates Steam/Epic games.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING"},
                "platform": {"type": "STRING"},
                "game_name": {"type": "STRING"},
                "app_id": {"type": "STRING"},
                "hour": {"type": "INTEGER"},
                "minute": {"type": "INTEGER"},
                "shutdown_when_done": {"type": "BOOLEAN"}
            },
            "required": []
        }
    },
    {
        "name": "flight_finder",
        "description": "Searches Google Flights.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "origin": {"type": "STRING"},
                "destination": {"type": "STRING"},
                "date": {"type": "STRING"},
                "return_date": {"type": "STRING"},
                "passengers": {"type": "INTEGER"},
                "cabin": {"type": "STRING"},
                "save": {"type": "BOOLEAN"}
            },
            "required": ["origin", "destination", "date"]
        }
    },
    {
        "name": "save_memory",
        "description": "Save an important personal fact to long-term memory.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {"type": "STRING"},
                "key": {"type": "STRING"},
                "value": {"type": "STRING"}
            },
            "required": ["category", "key", "value"]
        }
    }
]

def get_api_key():
    try:
        with open(API_CONFIG_PATH, "r") as f:
            return json.load(f).get("gemini_api_key", "")
    except:
        return ""

def _load_system_prompt():
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except:
        return "You are JARVIS, a helpful AI assistant. Be concise and use tools when needed."

class OnlineLightAssistant:
    def __init__(self, ui: JarvisUI):
        self.ui = ui
        self.tts = TTSLocal()
        self.stt = STTLocal()
        self.wake = WakeWordListener()
        self.model = None
        self._running = True
        self._init_model()
    
    def _init_model(self):
        api_key = get_api_key()
        if not api_key:
            self.ui.write_log("ERROR: No API key para Gemini.")
            return
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=_load_system_prompt(),
            tools=TOOL_DECLARATIONS
        )
        self.ui.write_log("✅ Modo ONLINE (texto) listo. Bajo consumo.")
    
    def _call_tool(self, tool_call):
        name = tool_call.name
        args = dict(tool_call.args)
        self.ui.set_state("THINKING")
        result = "Done."
        try:
            if name == "open_app":
                result = open_app(parameters=args, player=self.ui) or f"Opened {args.get('app_name')}."
            elif name == "web_search":
                result = web_search_action(parameters=args, player=self.ui) or "Search completed."
            elif name == "weather_report":
                result = weather_action(parameters=args, player=self.ui) or "Weather retrieved."
            elif name == "send_message":
                result = send_message(parameters=args, player=self.ui) or "Message sent."
            elif name == "reminder":
                result = reminder(parameters=args, player=self.ui) or "Reminder set."
            elif name == "youtube_video":
                result = youtube_video(parameters=args, player=self.ui) or "YouTube action done."
            elif name == "screen_process":
                threading.Thread(target=screen_process, kwargs={"parameters": args, "player": self.ui}, daemon=True).start()
                result = "Vision module activated."
            elif name == "computer_settings":
                result = computer_settings(parameters=args, player=self.ui) or "Setting applied."
            elif name == "browser_control":
                result = browser_control(parameters=args, player=self.ui) or "Browser action done."
            elif name == "file_controller":
                result = file_controller(parameters=args, player=self.ui) or "File operation done."
            elif name == "cmd_control":
                result = cmd_control(parameters=args, player=self.ui) or "Command executed."
            elif name == "desktop_control":
                result = desktop_control(parameters=args, player=self.ui) or "Desktop action done."
            elif name == "code_helper":
                result = code_helper(parameters=args, player=self.ui, speak=self.tts.speak) or "Code helper done."
            elif name == "dev_agent":
                result = dev_agent(parameters=args, player=self.ui, speak=self.tts.speak) or "Dev agent done."
            elif name == "agent_task":
                from agent.task_queue import get_queue, TaskPriority
                priority = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL}.get(args.get("priority", "normal"), TaskPriority.NORMAL)
                task_id = get_queue().submit(goal=args.get("goal", ""), priority=priority, speak=self.tts.speak)
                result = f"Task started (ID: {task_id})."
            elif name == "computer_control":
                result = computer_control(parameters=args, player=self.ui) or "Computer control done."
            elif name == "game_updater":
                result = game_updater(parameters=args, player=self.ui, speak=self.tts.speak) or "Game updater done."
            elif name == "flight_finder":
                result = flight_finder(parameters=args, player=self.ui, speak=self.tts.speak) or "Flight search done."
            else:
                result = f"Unknown tool: {name}"
        except Exception as e:
            result = f"Error: {e}"
        self.ui.set_state("LISTENING")
        return result
    
    def run(self):
        """Bucle principal: espera wake word, captura comando, envía a Gemini, habla respuesta."""
        self.tts.speak("Modo online activado. Di Jarvis seguido de tu pregunta o comando.")
        self.ui.set_state("ONLINE")
        
        while self._running:
            try:
                # 1. Esperar wake word y capturar comando (igual que en offline)
                print("[Online] Esperando 'jarvis'...")
                detected, comando = self.wake.listen_for_command()
                if not detected:
                    continue
                if not comando:
                    self.tts.speak("No entendí la orden.")
                    continue
                
                # 2. Tenemos un comando de voz
                self.ui.write_log(f"Tú (voz): {comando}")
                self.ui.set_state("THINKING")
                
                # 3. Enviar a Gemini (sin auto-ejecución de herramientas)
                chat = self.model.start_chat()
                response = chat.send_message(comando)
                
                # 4. Procesar respuesta de texto
                if response.text:
                    self.ui.write_log(f"Jarvis: {response.text}")
                    self.tts.speak(response.text)
                
                # 5. Procesar llamadas a herramientas (si las hay)
                if response.candidates and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if part.function_call:
                            tool_result = self._call_tool(part.function_call)
                            # Opcional: enviar resultado de vuelta a Gemini para continuar
                            # Aquí no lo hacemos por simplicidad
                
                # 6. Pequeña pausa para evitar saturar
                time.sleep(0.5)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.ui.write_log(f"Error en bucle online: {e}")
                print(f"[Online] Error: {e}")
                time.sleep(2)
        
        self.tts.speak("Modo online finalizado.")
    
    def stop(self):
        self._running = False
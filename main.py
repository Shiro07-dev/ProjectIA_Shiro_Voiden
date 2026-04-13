import asyncio
import threading
import json
import sys
import traceback
import socket
import time
from pathlib import Path

# Asegurar ruta para importar módulos offline
sys.path.insert(0, str(Path(__file__).parent))

from ui import JarvisUI

# --- Módulos offline ---
from offline.tts_local import TTSLocal
from offline.wake_word import WakeWordListener
from offline.stt_local import STTLocal
from offline.ia_api import JarvisIA, ejecutar_accion

# --- Módulos online (importaciones originales de MARK XXXV) ---
from memory.memory_manager import (
    load_memory, update_memory, format_memory_for_prompt,
    should_extract_memory, extract_memory
)
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

# --- Dependencias online (Gemini) ---
try:
    from google import genai
    from google.genai import types
    ONLINE_AVAILABLE = True
except ImportError:
    ONLINE_AVAILABLE = False

# --- Configuración ---
BASE_DIR = Path(__file__).resolve().parent
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH = BASE_DIR / "core" / "prompt.txt"
LIVE_MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================
def has_internet(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception:
        return False

def get_api_key():
    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("gemini_api_key", "")
    except:
        return ""

def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "You are JARVIS, Tony Stark's AI assistant. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )

# ============================================================
# MODO OFFLINE (clase completa, ya probada)
# ============================================================
class OfflineAssistant:
    def __init__(self, ui: JarvisUI):
        self.ui = ui
        self.tts = TTSLocal()
        self.wake = WakeWordListener()
        self.stt = STTLocal()
        self.ia = JarvisIA()
        self._running = True

    def run(self):
        self.tts.speak("Modo offline activado. Diga Jarvis seguido de su orden.")
        self.ui.set_state("OFFLINE")
        while self._running:
            try:
                detected, comando = self.wake.listen_for_command()
                if detected and comando:
                    self.ui.write_log(f"Tú: {comando}")
                    respuesta_json = self.ia.interpretar(comando)
                    data = json.loads(respuesta_json)
                    ejecutar_accion(data, self.tts)
                elif detected:
                    self.tts.speak("No entendí la orden.")
                time.sleep(0.1)
            except Exception as e:
                self.ui.write_log(f"Error offline: {e}")
                time.sleep(1)
        self.tts.speak("Modo offline finalizado.")

    def stop(self):
        self._running = False

# ============================================================
# MODO ONLINE (Gemini Live) - Clase completa
# ============================================================
_last_memory_input = ""

def _update_memory_async(user_text: str, jarvis_text: str) -> None:
    global _last_memory_input
    user_text = (user_text or "").strip()
    jarvis_text = (jarvis_text or "").strip()
    if len(user_text) < 5 or user_text == _last_memory_input:
        return
    _last_memory_input = user_text
    try:
        api_key = get_api_key()
        if not should_extract_memory(user_text, jarvis_text, api_key):
            return
        data = extract_memory(user_text, jarvis_text, api_key)
        if data:
            update_memory(data)
            print(f"[Memory] ✅ {list(data.keys())}")
    except Exception as e:
        if "429" not in str(e):
            print(f"[Memory] ⚠️ {e}")

# Tool declarations (resumido por brevedad, pero completo en tu código original)
# Incluyo la lista completa tal como la tenías (es muy larga, pero necesaria)
TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": "Opens any application on the Windows computer.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {"type": "STRING", "description": "Exact name of the application"}
            },
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

class JarvisLive:
    def __init__(self, ui: JarvisUI):
        self.ui = ui
        self.session = None
        self.audio_in_queue = None
        self.out_queue = None
        self._loop = None
        self._is_speaking = False
        self._speaking_lock = threading.Lock()
        self.ui.on_text_command = self._on_text_command

    def _on_text_command(self, text: str):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")

    def speak(self, text: str):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"Sir, {tool_name} encountered an error. {short}")

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime
        memory = load_memory()
        mem_str = format_memory_for_prompt(memory)
        sys_prompt = _load_system_prompt()
        now = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
        time_ctx = f"[CURRENT DATE & TIME]\nRight now it is: {time_str}\n\n"
        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str)
        parts.append(sys_prompt)
        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            session_resumption=types.SessionResumptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Charon")
                )
            ),
        )

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})
        print(f"[JARVIS] 🔧 {name}  {args}")
        self.ui.set_state("THINKING")

        if name == "save_memory":
            category = args.get("category", "notes")
            key = args.get("key", "")
            value = args.get("value", "")
            if key and value:
                update_memory({category: {key: {"value": value}}})
                print(f"[Memory] 💾 save_memory: {category}/{key} = {value}")
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "ok", "silent": True}
            )

        loop = asyncio.get_event_loop()
        result = "Done."

        try:
            if name == "open_app":
                r = await loop.run_in_executor(None, lambda: open_app(parameters=args, response=None, player=self.ui))
                result = r or f"Opened {args.get('app_name')}."
            elif name == "weather_report":
                r = await loop.run_in_executor(None, lambda: weather_action(parameters=args, player=self.ui))
                result = r or "Weather delivered."
            elif name == "browser_control":
                r = await loop.run_in_executor(None, lambda: browser_control(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "file_controller":
                r = await loop.run_in_executor(None, lambda: file_controller(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "send_message":
                r = await loop.run_in_executor(None, lambda: send_message(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or f"Message sent to {args.get('receiver')}."
            elif name == "reminder":
                r = await loop.run_in_executor(None, lambda: reminder(parameters=args, response=None, player=self.ui))
                result = r or "Reminder set."
            elif name == "youtube_video":
                r = await loop.run_in_executor(None, lambda: youtube_video(parameters=args, response=None, player=self.ui))
                result = r or "Done."
            elif name == "screen_process":
                threading.Thread(target=screen_process, kwargs={"parameters": args, "response": None, "player": self.ui, "session_memory": None}, daemon=True).start()
                result = "Vision module activated. Stay silent."
            elif name == "computer_settings":
                r = await loop.run_in_executor(None, lambda: computer_settings(parameters=args, response=None, player=self.ui))
                result = r or "Done."
            elif name == "cmd_control":
                r = await loop.run_in_executor(None, lambda: cmd_control(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "desktop_control":
                r = await loop.run_in_executor(None, lambda: desktop_control(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "code_helper":
                r = await loop.run_in_executor(None, lambda: code_helper(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."
            elif name == "dev_agent":
                r = await loop.run_in_executor(None, lambda: dev_agent(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."
            elif name == "agent_task":
                from agent.task_queue import get_queue, TaskPriority
                priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL, "high": TaskPriority.HIGH}
                priority = priority_map.get(args.get("priority", "normal").lower(), TaskPriority.NORMAL)
                task_id = get_queue().submit(goal=args.get("goal", ""), priority=priority, speak=self.speak)
                result = f"Task started (ID: {task_id})."
            elif name == "web_search":
                r = await loop.run_in_executor(None, lambda: web_search_action(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "computer_control":
                r = await loop.run_in_executor(None, lambda: computer_control(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "game_updater":
                r = await loop.run_in_executor(None, lambda: game_updater(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."
            elif name == "flight_finder":
                r = await loop.run_in_executor(None, lambda: flight_finder(parameters=args, player=self.ui))
                result = r or "Done."
            else:
                result = f"Unknown tool: {name}"
        except Exception as e:
            result = f"Tool '{name}' failed: {e}"
            traceback.print_exc()
            self.speak_error(name, e)

        if not self.ui.muted:
            self.ui.set_state("LISTENING")
        print(f"[JARVIS] 📤 {name} → {str(result)[:80]}")
        return types.FunctionResponse(id=fc.id, name=name, response={"result": result})

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send_realtime_input(media=msg)

    async def _listen_audio(self):
        import sounddevice as sd
        print("[JARVIS] 🎤 Mic started")
        loop = asyncio.get_event_loop()
        def callback(indata, frames, time_info, status):
            with self._speaking_lock:
                jarvis_speaking = self._is_speaking
            if not jarvis_speaking and not self.ui.muted:
                data = indata.tobytes()
                loop.call_soon_threadsafe(self.out_queue.put_nowait, {"data": data, "mime_type": "audio/pcm"})
        try:
            with sd.InputStream(samplerate=SEND_SAMPLE_RATE, channels=CHANNELS, dtype="int16", blocksize=CHUNK_SIZE, callback=callback):
                print("[JARVIS] 🎤 Mic stream open")
                while True:
                    await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[JARVIS] ❌ Mic: {e}")
            raise

    async def _receive_audio(self):
        print("[JARVIS] 👂 Recv started")
        out_buf, in_buf = [], []
        try:
            while True:
                async for response in self.session.receive():
                    if response.data:
                        self.audio_in_queue.put_nowait(response.data)
                    if response.server_content:
                        sc = response.server_content
                        if sc.output_transcription and sc.output_transcription.text:
                            self.set_speaking(True)
                            txt = sc.output_transcription.text.strip()
                            if txt:
                                out_buf.append(txt)
                        if sc.input_transcription and sc.input_transcription.text:
                            txt = sc.input_transcription.text.strip()
                            if txt:
                                in_buf.append(txt)
                        if sc.turn_complete:
                            self.set_speaking(False)
                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                self.ui.write_log(f"You: {full_in}")
                            in_buf = []
                            full_out = " ".join(out_buf).strip()
                            if full_out:
                                self.ui.write_log(f"Jarvis: {full_out}")
                            out_buf = []
                            if full_in and len(full_in) > 5:
                                threading.Thread(target=_update_memory_async, args=(full_in, full_out), daemon=True).start()
                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"[JARVIS] 📞 {fc.name}")
                            fr = await self._execute_tool(fc)
                            fn_responses.append(fr)
                        await self.session.send_tool_response(function_responses=fn_responses)
        except Exception as e:
            print(f"[JARVIS] ❌ Recv: {e}")
            traceback.print_exc()
            raise

    async def _play_audio(self):
        import sounddevice as sd
        print("[JARVIS] 🔊 Play started")
        stream = sd.RawOutputStream(samplerate=RECEIVE_SAMPLE_RATE, channels=CHANNELS, dtype="int16", blocksize=CHUNK_SIZE)
        stream.start()
        try:
            while True:
                chunk = await self.audio_in_queue.get()
                self.set_speaking(True)
                await asyncio.to_thread(stream.write, chunk)
        except Exception as e:
            print(f"[JARVIS] ❌ Play: {e}")
            raise
        finally:
            self.set_speaking(False)
            stream.stop()
            stream.close()

    async def run(self):
        client = genai.Client(api_key=get_api_key(), http_options={"api_version": "v1beta"})
        while True:
            try:
                print("[JARVIS] 🔌 Connecting...")
                self.ui.set_state("THINKING")
                config = self._build_config()
                async with client.aio.live.connect(model=LIVE_MODEL, config=config) as session, asyncio.TaskGroup() as tg:
                    self.session = session
                    self._loop = asyncio.get_event_loop()
                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue = asyncio.Queue(maxsize=10)
                    print("[JARVIS] ✅ Connected.")
                    self.ui.set_state("LISTENING")
                    self.ui.write_log("SYS: JARVIS online.")
                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())
            except Exception as e:
                print(f"[JARVIS] ⚠️ {e}")
                traceback.print_exc()
            self.set_speaking(False)
            self.ui.set_state("THINKING")
            print("[JARVIS] 🔄 Reconnecting in 3s...")
            await asyncio.sleep(3)

# ============================================================
# CLASE UNIFICADA (decide online/offline automáticamente)
# ============================================================
class UnifiedAssistant:
    def __init__(self, ui: JarvisUI):
        self.ui = ui
        self.online = has_internet() and ONLINE_AVAILABLE and bool(get_api_key())
        self.mode = "ONLINE" if self.online else "OFFLINE"
        self.ui.write_log(f"SYS: Modo {self.mode} detectado.")
        self.ui.set_state(self.mode)

        if self.online:
            self.assistant = JarvisLive(ui)
        else:
            self.assistant = OfflineAssistant(ui)

        self._thread = None

    def start(self):
        if self.online:
            try:
                asyncio.run(self.assistant.run())
            except KeyboardInterrupt:
                print("Cerrando modo online...")
        else:
            self._thread = threading.Thread(target=self.assistant.run, daemon=True)
            self._thread.start()

    def stop(self):
        if hasattr(self.assistant, 'stop'):
            self.assistant.stop()

# ============================================================
# MAIN (sin selector manual, usa detección automática)
# ============================================================
def main():
    ui = JarvisUI("face.png")
    ui.wait_for_api_key()
    assistant = UnifiedAssistant(ui)

    def run_assistant():
        assistant.start()

    threading.Thread(target=run_assistant, daemon=True).start()
    try:
        ui.root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        assistant.stop()

if __name__ == "__main__":
    main()
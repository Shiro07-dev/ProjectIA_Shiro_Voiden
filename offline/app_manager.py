import psutil
import subprocess
import os
from jarvis_core.logger import log_event

class AppManager:
    @staticmethod
    def open_app(app_path):
        try:
            subprocess.Popen(f'"{app_path}"', shell=True)
            log_event(f"Aplicación abierta: {app_path}")
            return True
        except Exception as e:
            log_event(f"Error abriendo app: {e}", level="error")
            return False

    @staticmethod
    def close_app(process_name):
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                proc.terminate()
                log_event(f"Aplicación cerrada: {process_name}")
                return True
        log_event(f"No se encontró proceso: {process_name}", level="warning")
        return False

    @staticmethod
    def force_kill_app(process_name):
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                proc.kill()
                log_event(f"Aplicación forzada a cerrar: {process_name}")
                return True
        log_event(f"No se encontró proceso: {process_name}", level="warning")
        return False

    @staticmethod
    def list_open_apps():
        apps = set()
        for proc in psutil.process_iter(['name']):
            if proc.info['name']:
                apps.add(proc.info['name'])
        log_event(f"Aplicaciones abiertas: {apps}")
        return list(apps)

    @staticmethod
    def find_app_path(app_name):
        common_dirs = [
            os.environ.get("PROGRAMFILES"),
            os.environ.get("PROGRAMFILES(X86)"),
            os.environ.get("LOCALAPPDATA")
        ]
        for directory in common_dirs:
            if directory:
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        if app_name.lower() in file.lower() and file.lower().endswith(".exe"):
                            app_path = os.path.join(root, file)
                            log_event(f"Ruta encontrada para {app_name}: {app_path}")
                            return app_path
        log_event(f"No se encontró la ruta para {app_name}", level="warning")
        return None

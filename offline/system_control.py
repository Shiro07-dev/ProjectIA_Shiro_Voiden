import ctypes
import subprocess
import psutil
from jarvis_core.logger import log_event

class SystemControl:
    @staticmethod
    def shutdown():
        log_event("Apagando el sistema")
        subprocess.run(["shutdown", "/s", "/t", "0"])

    @staticmethod
    def restart():
        log_event("Reiniciando el sistema")
        subprocess.run(["shutdown", "/r", "/t", "0"])

    @staticmethod
    def sleep():
        log_event("Suspensión del sistema")
        ctypes.windll.PowrProf.SetSuspendState(0, 1, 0)

    @staticmethod
    def hibernate():
        log_event("Hibernando el sistema")
        ctypes.windll.PowrProf.SetSuspendState(1, 1, 0)

    @staticmethod
    def lock():
        log_event("Bloqueando pantalla")
        ctypes.windll.user32.LockWorkStation()

    @staticmethod
    def get_battery_status():
        battery = psutil.sensors_battery()
        if battery:
            status = {
                "percent": battery.percent,
                "plugged": battery.power_plugged
            }
            log_event(f"Estado batería: {status}")
            return status
        else:
            log_event("No se detecta batería", level="warning")
            return None

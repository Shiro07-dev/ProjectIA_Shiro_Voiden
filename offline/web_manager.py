import os
import webbrowser
import requests
from jarvis_core.logger import log_event

class WebManager:
    @staticmethod
    def open_url(url):
        webbrowser.open(url)
        log_event(f"URL abierta: {url}")

    @staticmethod
    def download_file(url, dest):
        r = requests.get(url, stream=True)
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        log_event(f"Archivo descargado: {url} -> {dest}")

    @staticmethod
    def search(query):
        url = f"https://www.google.com/search?q={query}"
        webbrowser.open(url)
        log_event(f"Búsqueda realizada: {query}")

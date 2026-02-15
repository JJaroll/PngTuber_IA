"""
(AI)terEgo
-----------
Una aplicación de avatar virtual controlada por voz e Inteligencia Artificial.

Desarrollado por: JJaroll
GitHub: https://github.com/JJaroll
Fecha: 10/02/2026
Licencia: MIT
"""

__author__ = "JJaroll"
__version__ = "1.0.0"
__maintainer__ = "JJaroll"
__status__ = "Production"

import json
import urllib.request
from PyQt6.QtCore import QThread, pyqtSignal

# --- CONSTANTES ---
CURRENT_VERSION = "1.1.0"
UPDATE_URL = "https://pastebin.com/raw/xux8fcwt" # Placeholder

class UpdateChecker(QThread):
    # Modificamos la señal para enviar dos textos: (url, version_nueva)
    update_available = pyqtSignal(str, str) 

    def run(self):
        try:
            req = urllib.request.Request(
                UPDATE_URL, 
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                remote_version = data.get("version", "0.0.0")
                download_url = data.get("url", "")
                
                # Comparamos versiones
                if remote_version > CURRENT_VERSION:
                    # Emitimos URL y la Versión detectada
                    self.update_available.emit(download_url, remote_version)

        except Exception as e:
            print(f"[ERROR] Update check failed: {e}")

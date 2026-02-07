import json
import os
from PyQt6.QtCore import QObject, QTimer

class ConfigManager(QObject):
    def __init__(self, filepath="settings.json"):
        super().__init__()
        self.filepath = filepath
        self.default_config = {
            "current_profile": "Default",
            "bounce_enabled": True,
            "bounce_amplitude": 10,
            "bounce_speed": 0.3,
            "shadow_enabled": True,
            "is_muted": False,
            "background_color": "transparent",
            "microphone_index": None
        }
        
        # 1. Cargar en memoria RAM al iniciar (Lectura Única)
        self.config_cache = self.load_config()
        
        # 2. Configurar el Timer de Guardado Diferido (Debounce)
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(1000) # Espera 1 segundo antes de escribir en disco
        self.save_timer.timeout.connect(self._save_to_disk_actual)

    def load_config(self):
        """Carga el JSON del disco o devuelve los valores por defecto."""
        if not os.path.exists(self.filepath):
            return self.default_config.copy()
        
        try:
            with open(self.filepath, "r") as f:
                data = json.load(f)
                # Asegurar que existan todas las claves por defecto (Merge)
                for key, value in self.default_config.items():
                    if key not in data:
                        data[key] = value
                return data
        except Exception as e:
            print(f"Error cargando config: {e}")
            return self.default_config.copy()

    def _save_to_disk_actual(self):
        """Esta función es la que realmente toca el disco duro."""
        try:
            with open(self.filepath, "w") as f:
                json.dump(self.config_cache, f, indent=4)
            print("💾 Configuración guardada en disco (Async).")
        except Exception as e:
            print(f"Error guardando config: {e}")

    def set(self, key, value):
        """
        Actualiza el valor en memoria y reinicia el temporizador de guardado.
        Si llamas a esto 100 veces en 1 segundo, solo guardará 1 vez al final.
        """
        # Si el valor no cambió, no hacemos nada
        if self.config_cache.get(key) == value:
            return

        # Actualizar memoria (rápido)
        self.config_cache[key] = value
        
        # Reiniciar el timer (retrasar la escritura en disco)
        self.save_timer.start()

    def get(self, key):
        """Obtiene el valor desde la memoria RAM (Instantáneo)."""
        return self.config_cache.get(key, self.default_config.get(key))
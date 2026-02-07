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
        
        self.config_cache = self.load_config()
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(1000) # Guardar 1 segundo después del último cambio
        self.save_timer.timeout.connect(self._save_to_disk_actual)

    def load_config(self):
        if not os.path.exists(self.filepath):
            return self.default_config.copy()
        try:
            with open(self.filepath, "r") as f:
                data = json.load(f)
                for key, value in self.default_config.items():
                    if key not in data: data[key] = value
                return data
        except: return self.default_config.copy()

    def _save_to_disk_actual(self):
        try:
            with open(self.filepath, "w") as f:
                json.dump(self.config_cache, f, indent=4)
        except Exception as e:
            print(f"Error guardando: {e}")

    def set(self, key, value):
        if self.config_cache.get(key) == value: return
        self.config_cache[key] = value
        self.save_timer.start() # Reinicia el contador

    def get(self, key, default=None):
        return self.config_cache.get(key, default if default is not None else self.default_config.get(key))
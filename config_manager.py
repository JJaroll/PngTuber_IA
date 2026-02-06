import json
import os

class ConfigManager:
    def __init__(self, filepath="settings.json"):
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

    def load_config(self):
        if not os.path.exists(self.filepath):
            return self.default_config
        
        try:
            with open(self.filepath, "r") as f:
                config = json.load(f)
                # Merge with defaults to ensure all keys exist
                for key, value in self.default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.default_config

    def save_config(self, config):
        try:
            with open(self.filepath, "w") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

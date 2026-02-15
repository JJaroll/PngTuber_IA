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

import sys
from PyQt6.QtCore import QObject, pyqtSignal, QEvent, Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QKeySequence

class HotkeyManager(QObject):
    hotkey_triggered = pyqtSignal(str)

    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.listening = False
        self.key_map = {} 
        self.load_hotkeys()

    def load_hotkeys(self):
        """Traduce la configuración a códigos numéricos de Qt"""
        raw_hotkeys = self.config_manager.get("hotkeys", {})
        
        # Mapeo por defecto
        default_hotkeys = {
            "mute_toggle": "M",
            "ai_mode": "X",
            "neutral": "1",
            "happiness": "2",
            "sadness": "3",
            "anger": "4",
            "surprise": "5",
            "fear": "6",
            "disgust": "7"
        }

        final_hotkeys = default_hotkeys.copy()
        final_hotkeys.update(raw_hotkeys)

        self.key_map = {}
        
        for action, key_str in final_hotkeys.items():
            if key_str:
                try:
                    # Limpiamos y formateamos la tecla
                    clean_str = str(key_str).replace("<", "").replace(">", "").title()
                    # QKeySequence calcula el código entero único para esa tecla
                    seq = QKeySequence(clean_str)
                    if not seq.isEmpty():
                        qt_code = seq[0].toCombined()
                        self.key_map[qt_code] = action
                except Exception as e:
                    print(f"Error mapeando tecla {key_str}: {e}")

    def start_listening(self):
        if not self.listening:
            app = QApplication.instance()
            if app:
                app.installEventFilter(self)
                self.listening = True
                print("⌨️  Gestor de atajos iniciado (Modo Nativo PyQt)")

    def stop_listening(self):
        if self.listening:
            app = QApplication.instance()
            if app:
                app.removeEventFilter(self)
            self.listening = False

    def _safe_get_value(self, obj):
        try:
            return obj.value # Para PyQt6 Enums
        except AttributeError:
            try:
                return int(obj) # Para enteros normales
            except:
                return 0

    def eventFilter(self, obj, event):
        try:
            if event.type() == QEvent.Type.KeyPress:
                key_val = self._safe_get_value(event.key())
                mod_val = self._safe_get_value(event.modifiers())
                
                # Ignorar si es solo una tecla de control (Ctrl, Shift, etc presionados solos)
                if 16777248 <= key_val <= 16777255: 
                    return super().eventFilter(obj, event)
                current_combo = key_val | mod_val
                
                # 4. Verificar coincidencia
                if current_combo in self.key_map:
                    action = self.key_map[current_combo]
                    print(f"⚡ Acción ejecutada: {action}")
                    self.hotkey_triggered.emit(action)
                    return True # Consumir evento
                    
        except Exception as e:
            # En caso de error, NO abortamos la app, solo lo reportamos y continuamos
            print(f"⚠️ Error recuperable en teclas: {e}")
            
        # Dejar pasar el evento normalmente
        return super().eventFilter(obj, event)

    def update_hotkey(self, action, new_key):
        current = self.config_manager.get("hotkeys", {})
        current[action] = new_key
        self.config_manager.set("hotkeys", current)
        self.load_hotkeys()
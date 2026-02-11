"""
PNGTuber IA
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

import time
from multiprocessing import Queue
from pynput import keyboard
from pynput.keyboard import Key, KeyCode

def run_hotkey_listener(queue, mapping):
    
    pynput_mapping = {}
    for key_str, action in mapping.items():
        if not key_str: continue
        
        if len(key_str) == 1:
            pynput_mapping[KeyCode.from_char(key_str)] = action
            if key_str.lower() != key_str.upper():
                pynput_mapping[KeyCode.from_char(key_str.lower())] = action
                pynput_mapping[KeyCode.from_char(key_str.upper())] = action
        else:
            try:
                key_obj = getattr(Key, key_str.lower(), None)
                if key_obj:
                    pynput_mapping[key_obj] = action
            except: pass

    def on_press(key):
        try:
            action = pynput_mapping.get(key)
            
            if not action and hasattr(key, 'char') and key.char:
                action = pynput_mapping.get(KeyCode.from_char(key.char.lower()))
            
            if action:
                queue.put(action)
        except Exception:
            pass

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

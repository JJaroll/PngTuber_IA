import time
from multiprocessing import Queue
from pynput import keyboard
from pynput.keyboard import Key, KeyCode

def run_hotkey_listener(queue, mapping):
    """
    Función que se ejecuta en un proceso separado.
    queue: multiprocessing.Queue para enviar acciones al proceso principal.
    mapping: dict con mapeo de teclas {key_str: action_name}
    """
    
    # Reconstruir el mapeo a objetos pynput
    # El mapping llega como diccionario de strings: {"m": "mute_toggle", "f1": "action"}
    # key_str puede ser un char o un nombre de tecla especial.
    
    pynput_mapping = {}
    for key_str, action in mapping.items():
        if not key_str: continue
        
        # Intentar convertir
        if len(key_str) == 1:
            pynput_mapping[KeyCode.from_char(key_str)] = action
            # También soportar mayúsculas/minúsculas
            if key_str.lower() != key_str.upper():
                pynput_mapping[KeyCode.from_char(key_str.lower())] = action
                pynput_mapping[KeyCode.from_char(key_str.upper())] = action
        else:
            # Tecla especial
            try:
                key_obj = getattr(Key, key_str.lower(), None)
                if key_obj:
                    pynput_mapping[key_obj] = action
            except: pass

    def on_press(key):
        try:
            # Buscar en mapeo
            action = pynput_mapping.get(key)
            
            # Intento secundario para chars
            if not action and hasattr(key, 'char') and key.char:
                # Buscar por char minúscula
                action = pynput_mapping.get(KeyCode.from_char(key.char.lower()))
            
            if action:
                queue.put(action)
        except Exception:
            pass

    # Iniciar listener bloqueante
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

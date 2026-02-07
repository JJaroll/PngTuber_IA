from PyQt6.QtCore import QObject, pyqtSignal, QTimer
# NO IMPORTAMOS pynput AQUÍ para evitar conflictos en el proceso principal
import multiprocessing
from hotkey_process import run_hotkey_listener

class HotkeyManager(QObject):
    hotkey_triggered = pyqtSignal(str)

    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.process = None
        self.queue = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_queue)
        
        # Mapeo invertido para la UI: action -> key
        # Pero para el proceso necesitamos key -> action
        self.mapping = {}
        self.reverse_mapping = {} # key_str -> action (lo que enviamos al proceso)
        self.reload_mapping()

    def reload_mapping(self):
        hotkeys = self.config_manager.get("hotkeys", {})
        self.mapping = hotkeys
        
        # Preparar mapeo para el proceso: key -> action
        self.reverse_mapping = {}
        for action, key in hotkeys.items():
            if key:
                self.reverse_mapping[str(key).lower()] = action
        
        # Si el proceso está corriendo, habría que reiniciarlo para aplicar cambios
        if self.process and self.process.is_alive():
            self.stop_listening()
            self.start_listening()

    def start_listening(self):
        if self.process and self.process.is_alive():
            return

        if not self.config_manager.get("enable_hotkeys", True):
            print("Hotkeys deshabilitados por configuración.")
            return

        try:
            self.queue = multiprocessing.Queue()
            # Pasamos el diccionario inverso {tecla: accion}
            self.process = multiprocessing.Process(
                target=run_hotkey_listener, 
                args=(self.queue, self.reverse_mapping)
            )
            self.process.daemon = True # Se muere si el principal muere
            self.process.start()
            
            self.timer.start(50) # Revisar cada 50ms
            print("Proceso de hotkeys iniciado (PID: {})".format(self.process.pid))
            
        except Exception as e:
            print(f"Error iniciando proceso de hotkeys: {e}")

    def stop_listening(self):
        self.timer.stop()
        if self.process:
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(timeout=1)
            self.process = None
            self.queue = None

    def check_queue(self):
        if not self.queue: return
        while not self.queue.empty():
            try:
                action = self.queue.get_nowait()
                if action:
                    self.hotkey_triggered.emit(action)
            except: 
                break

    def update_hotkey(self, action, key_str):
        current = self.config_manager.get("hotkeys", {})
        current[action] = key_str
        self.config_manager.set("hotkeys", current)
        self.reload_mapping()

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox)
from PyQt6.QtCore import Qt
try:
    from pynput.keyboard import Key, KeyCode
except: pass # Solo para verificacion visual si fuera necesario

class HotkeyRecorderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Grabando...")
        self.setFixedSize(300, 150)
        self.layout = QVBoxLayout(self)
        self.label = QLabel("Presiona una tecla ahora...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.layout.addWidget(self.label)
        
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        self.layout.addWidget(cancel)

        self.key_result = None

    def keyPressEvent(self, event):
        key = event.key()
        text = event.text()
        
        result = ""
        # 1. Caracteres imprimibles (letras, números)
        if text and text.isprintable():
            result = text.lower()
        else:
            # 2. Teclas especiales comunes mapeadas a nombres de pynput
            key_map = {
                Qt.Key.Key_Escape: 'esc',
                Qt.Key.Key_Return: 'enter',
                Qt.Key.Key_Enter: 'enter',
                Qt.Key.Key_Space: 'space',
                Qt.Key.Key_Backspace: 'backspace',
                Qt.Key.Key_Tab: 'tab',
                Qt.Key.Key_Up: 'up',
                Qt.Key.Key_Down: 'down',
                Qt.Key.Key_Left: 'left',
                Qt.Key.Key_Right: 'right',
                Qt.Key.Key_Delete: 'delete'
            }
            
            if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
                result = f"f{key - Qt.Key.Key_F1 + 1}"
            elif key in key_map:
                result = key_map[key]
        
        if result:
            self.key_result = result
            self.accept()

class HotkeyConfigDialog(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.config_manager = main_window.config_manager
        self.hotkey_manager = main_window.hotkey_manager
        
        self.setWindowTitle("Configuración de Hotkeys")
        self.resize(500, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Acción", "Tecla Actual", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        
        layout.addWidget(self.table)
        
        self.load_hotkeys()

        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def load_hotkeys(self):
        hotkeys = self.config_manager.get("hotkeys", {})
        friendly_names = {
            "mute_toggle": "🔇 Silenciar / Activar",
            "ai_mode": "🤖 Activar Modo IA",
            "neutral": "😐 Emoción: Neutral",
            "disgust": "🤢 Emoción: Asco (Disgust)",
            "fear": "😨 Emoción: Miedo (Fear)",
            "happiness": "😄 Emoción: Felicidad",
            "sadness": "😢 Emoción: Tristeza",
            "anger": "😡 Emoción: Enojo"
        }

        self.table.setRowCount(0)
        
        order = ["mute_toggle", "ai_mode", "neutral", "happiness", "sadness", "anger", "fear", "disgust"]
        
        row = 0
        for action in order:
            if action not in hotkeys: continue
            self.add_row(row, action, friendly_names.get(action, action), hotkeys[action])
            row += 1
            
        for action, key in hotkeys.items():
            if action not in order:
                self.add_row(row, action, friendly_names.get(action, action), key)
                row += 1

    def add_row(self, row, action, name, key_str):
        self.table.insertRow(row)
        
        item_name = QTableWidgetItem(name)
        item_name.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self.table.setItem(row, 0, item_name)
        
        item_key = QTableWidgetItem(str(key_str).upper())
        item_key.setFlags(Qt.ItemFlag.ItemIsEnabled)
        item_key.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 1, item_key)

        btn = QPushButton("Cambiar Tecla")
        btn.clicked.connect(lambda _, a=action: self.record_key(a))
        self.table.setCellWidget(row, 2, btn)

    def record_key(self, action):
        # Si la tecla presionada es un hotkey global, se ejecutará la acción mientras grabamos
        dialog = HotkeyRecorderDialog(self)
        if dialog.exec():
            new_key = dialog.key_result
            if new_key:
                self.hotkey_manager.update_hotkey(action, new_key)
                self.load_hotkeys()

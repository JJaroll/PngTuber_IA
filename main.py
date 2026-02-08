import sys
import numpy as np
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QSizeGrip, QGraphicsDropShadowEffect, QPushButton
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor

# Imports Locales
from profile_manager import AvatarProfileManager
from background import BackgroundManager
from mac_gui import MacWindowControls
from config_manager import ConfigManager
from hotkey_manager import HotkeyManager
from core_systems import AudioMonitorThread, EmotionThread

class PNGTuberApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 1. Cargar Configuración
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()

        # Variables de Estado
        self.current_emotion = "neutral"
        self.is_speaking = False
        self.is_muted = self.config.get("is_muted", False)
        
        # Configuración Visual (Recuperada del JSON)
        self.bounce_enabled = self.config.get("bounce_enabled", True)
        self.bounce_amplitude = self.config.get("bounce_amplitude", 10)
        self.bounce_speed = self.config.get("bounce_speed", 0.3)
        self.bounce_phase = 0
        self.shadow_enabled = self.config.get("shadow_enabled", True)
        self.current_background = self.config.get("background_color", "transparent")

        # 2. Iniciar Gestores
        self.profile_manager = AvatarProfileManager()
        profile_name = self.config.get("current_profile", "Default")
        self.profile_manager.set_profile(profile_name)

        # 3. Interfaz Gráfica
        self.init_ui()

        # 4. Sistemas de Audio e IA (Hilos)
        saved_mic = self.config.get("microphone_index")
        self.audio_thread = AudioMonitorThread(device_index=saved_mic)
        self.audio_thread.volume_signal.connect(self.update_mouth)
        self.audio_thread.audio_data_signal.connect(self.handle_audio)
        self.audio_thread.start()

        self.emotion_thread = EmotionThread()
        self.emotion_thread.emotion_signal.connect(self.update_emotion)
        self.emotion_thread.start()

        self.bounce_timer = QTimer()
        self.bounce_timer.timeout.connect(self.animate_bounce)
        self.bounce_timer.start(30)
 
        # 6. Gestor de Hotkeys
        self.ai_mode = True
        self.hotkey_manager = HotkeyManager(self.config_manager)
        self.hotkey_manager.hotkey_triggered.connect(self.handle_hotkey)
        QTimer.singleShot(1000, self.hotkey_manager.start_listening)
        
        # Estado inicial
        self.update_avatar()

    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(400, 400)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(5, 5, 5, 5)

        # Barra Superior (Mac Style)
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(13, 13, 0, 0)
        self.mac_controls = MacWindowControls(self)
        self.mac_controls.close_signal.connect(self.close)
        self.mac_controls.minimize_signal.connect(self.showMinimized)
        top_bar.addWidget(self.mac_controls)
        top_bar.addStretch()
        self.layout.addLayout(top_bar)

        # Avatar
        self.avatar_label = QLabel(self)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.avatar_label)

        # Botón Mute (Abajo)
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(10, 0, 10, 10)
        self.mute_btn = QPushButton("🔊")
        self.mute_btn.setFixedSize(30, 30)
        self.mute_btn.setCheckable(True)
        self.mute_btn.setChecked(self.is_muted)
        self.mute_btn.setStyleSheet("QPushButton { background-color: rgba(255,255,255,200); border-radius: 15px; border: 1px solid #ccc; } QPushButton:checked { background-color: #ff6666; border: 1px solid red; }")
        self.mute_btn.clicked.connect(self.set_muted)
        bottom_bar.addWidget(self.mute_btn)
        bottom_bar.addStretch()
        self.layout.addLayout(bottom_bar)

        # Efectos (Sombra y Resize)
        self.shadow_effect = QGraphicsDropShadowEffect()
        self.shadow_effect.setBlurRadius(20)
        self.shadow_effect.setColor(QColor(0, 0, 0, 150))
        self.shadow_effect.setOffset(0, 5)
        self.set_shadow_enabled(self.shadow_enabled)

        self.sizegrip = QSizeGrip(self)
        self.sizegrip.setStyleSheet("QSizeGrip { background-color: transparent; width: 20px; height: 20px; }")

        # Gestor de Fondo (Menú Contextual)
        self.bg_manager = BackgroundManager(self, self.profile_manager, self.config_manager)
        self.bg_manager.change_background(self.current_background)

    # --- LÓGICA DE ANIMACIÓN ---
    def animate_bounce(self):
        if self.bounce_enabled and self.is_speaking:
            self.bounce_phase += self.bounce_speed
            offset = int(abs(np.sin(self.bounce_phase)) * self.bounce_amplitude)
            self.avatar_label.setContentsMargins(0, 0, 0, offset)
        elif self.bounce_phase != 0:
            self.bounce_phase = 0
            self.avatar_label.setContentsMargins(0, 0, 0, 0)

    def update_avatar(self):
        state = "open" if self.is_speaking else "closed"
        path = self.profile_manager.get_image_path(self.current_emotion, state)
        pix = QPixmap(path)
        if pix.isNull():
            path = self.profile_manager.get_image_path("neutral", state) # Fallback
            pix = QPixmap(path)
        
        if not pix.isNull():
            self.avatar_label.setPixmap(pix.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    # --- CONECTORES (Señales) ---
    def handle_audio(self, chunk):
        if not self.is_muted:
            self.emotion_thread.add_audio(chunk)

    def update_mouth(self, speaking):
        if self.is_muted: speaking = False
        if self.is_speaking != speaking:
            self.is_speaking = speaking
            self.update_avatar()

    def update_emotion(self, emo):
        if self.ai_mode and self.current_emotion != emo:
            self.current_emotion = emo
            self.update_avatar()

    def handle_hotkey(self, action):
        print(f"Hotkey: {action}")
        if action == "mute_toggle":
            self.set_muted(not self.is_muted)
        elif action == "ai_mode":
            self.ai_mode = True
            print("🤖 Modo IA Activado")
        elif action in ["neutral", "happiness", "anger", "sadness", "fear", "disgust"]:
            self.ai_mode = False

            manual_map = {
                "neutral": "neutral",
                "happiness": "happy",
                "anger": "angry", 
                "sadness": "sad",
                "fear": "sad", 
                "disgust": "angry"
            }
            
            target_emo = manual_map.get(action, "neutral")
            self.current_emotion = target_emo
            self.update_avatar()
            print(f"🛑 Modo Manual: {action} -> {target_emo}")

    # --- SETTERS (Aquí conectamos con background.py) ---
    def set_microphone(self, index):
        print(f"🎤 Cambiando micrófono a ID: {index}")
        self.audio_thread.change_device(index)
        self.config_manager.set("microphone_index", index)

    def set_muted(self, muted):
        self.is_muted = muted
        self.mute_btn.setChecked(muted)
        self.mute_btn.setText("🔇" if muted else "🔊")
        self.config_manager.set("is_muted", muted)
        if muted:
            self.is_speaking = False
            self.update_avatar()

    def set_bounce_enabled(self, enabled):
        self.bounce_enabled = enabled
        self.config_manager.set("bounce_enabled", enabled)
        if not enabled: # Reset visual inmediato
            self.bounce_phase = 0
            self.avatar_label.setContentsMargins(0, 0, 0, 0)

    def set_bounce_amplitude(self, value):
        self.bounce_amplitude = value
        self.config_manager.set("bounce_amplitude", value)

    def set_bounce_speed(self, value):
        self.bounce_speed = value
        self.config_manager.set("bounce_speed", value)

    def set_shadow_enabled(self, enabled):
        self.shadow_enabled = enabled
        self.config_manager.set("shadow_enabled", enabled)
        if enabled:
            self.avatar_label.setGraphicsEffect(self.shadow_effect)
        else:
            self.avatar_label.setGraphicsEffect(None)

    # --- EVENTOS DE VENTANA ---
    def resizeEvent(self, event):
        rect = self.rect()
        self.sizegrip.move(rect.right() - self.sizegrip.width(), rect.bottom() - self.sizegrip.height())
        super().resizeEvent(event)

    def contextMenuEvent(self, event):
        self.bg_manager.show_context_menu(event.pos())

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(100, lambda: self.resize(self.width() + 1, self.height()))
        QTimer.singleShot(200, lambda: self.resize(self.width() - 1, self.height()))

    def closeEvent(self, event):
        self.hotkey_manager.stop_listening()
        self.audio_thread.stop()
        self.emotion_thread.stop()
        event.accept()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PNGTuberApp()
    window.show()
    sys.exit(app.exec())
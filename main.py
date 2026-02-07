import sys
import numpy as np
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QSizeGrip, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor

# --- IMPORTAMOS MÓDULOS ---
from profile_manager import AvatarProfileManager
from background import BackgroundManager
from mac_gui import MacWindowControls
from config_manager import ConfigManager
from core_systems import AudioMonitorThread, EmotionThread # <--- NUEVO MÓDULO

class PNGTuberApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 1. Configuración y Estado
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        self.profile_manager = AvatarProfileManager()
        
        # Estado interno
        self.current_emotion = "neutral"
        self.is_speaking = False
        self.is_muted = self.config.get("is_muted", False)
        
        # Cargar configuración visual
        self.bounce_enabled = self.config.get("bounce_enabled", True)
        self.bounce_amplitude = self.config.get("bounce_amplitude", 10)
        self.bounce_speed = self.config.get("bounce_speed", 0.3)
        self.shadow_enabled = self.config.get("shadow_enabled", True)
        self.current_background = self.config.get("background_color", "transparent")
        
        # Cargar perfil guardado
        last_profile = self.config.get("current_profile", "Default")
        self.profile_manager.set_profile(last_profile)

        # 2. Setup Interfaz
        self.init_ui()

        # 3. Iniciar Sistemas (Hilos)
        # Micrófono guardado
        mic_index = self.config.get("microphone_index")
        
        self.audio_thread = AudioMonitorThread(device_index=mic_index)
        self.audio_thread.volume_signal.connect(self.update_mouth)
        self.audio_thread.audio_data_signal.connect(self.handle_audio)
        self.audio_thread.start()

        self.emotion_thread = EmotionThread()
        self.emotion_thread.emotion_signal.connect(self.update_emotion)
        self.emotion_thread.start()

        # 4. Timer de Animación
        self.bounce_timer = QTimer()
        self.bounce_timer.timeout.connect(self.animate_bounce)
        self.bounce_phase = 0
        self.bounce_timer.start(30) # 30 FPS

        self.update_avatar()

    def init_ui(self):
        """Configura toda la interfaz gráfica"""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(400, 400)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Barra Mac
        self.mac_controls = MacWindowControls(self)
        self.mac_controls.close_signal.connect(self.close)
        self.mac_controls.minimize_signal.connect(self.showMinimized)
        
        top = QHBoxLayout()
        top.setContentsMargins(13, 13, 0, 0)
        top.addWidget(self.mac_controls)
        top.addStretch()
        self.layout.addLayout(top)

        # Avatar
        self.avatar_label = QLabel(self)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.avatar_label)

        # Sombra (Aplicar configuración inicial)
        self.shadow_effect = QGraphicsDropShadowEffect()
        self.shadow_effect.setBlurRadius(20)
        self.shadow_effect.setColor(QColor(0, 0, 0, 150))
        self.shadow_effect.setOffset(0, 5)
        self.shadow_effect.setEnabled(self.shadow_enabled)
        self.avatar_label.setGraphicsEffect(self.shadow_effect)

        # Resize Grip
        self.sizegrip = QSizeGrip(self)
        self.sizegrip.setStyleSheet("QSizeGrip { background-color: transparent; width: 20px; height: 20px; }")

        # Gestor de Fondo y Menú
        self.bg_manager = BackgroundManager(self, self.profile_manager, self.config_manager)
        
        # Aplicar fondo inicial
        self.bg_manager.change_background(self.current_background)

    # --- LÓGICA VISUAL ---
    def showEvent(self, event):
        super().showEvent(event)
        # Fix Transparencia MacOS (Doble Salto)
        QTimer.singleShot(100, lambda: self.resize(self.width() + 1, self.height()))
        QTimer.singleShot(200, lambda: self.resize(self.width() - 1, self.height()))

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
            fallback = self.profile_manager.get_image_path("neutral", state)
            pix = QPixmap(fallback)
            if pix.isNull(): self.draw_placeholder()
            else: self.set_pix(pix)
        else:
            self.set_pix(pix)

    def set_pix(self, pix):
        self.avatar_label.setPixmap(pix.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def draw_placeholder(self):
        img = QImage(400, 400, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setBrush(Qt.GlobalColor.blue)
        p.drawEllipse(50, 50, 300, 300)
        p.end()
        self.avatar_label.setPixmap(QPixmap.fromImage(img))

    # --- SEÑALES Y SETTERS ---
    def handle_audio(self, chunk):
        if not self.is_muted:
            self.emotion_thread.add_audio(chunk)

    def update_mouth(self, speaking):
        if self.is_muted: speaking = False
        if self.is_speaking != speaking:
            self.is_speaking = speaking
            self.update_avatar()

    def update_emotion(self, emo):
        if self.current_emotion != emo:
            self.current_emotion = emo
            self.update_avatar()

    # --- SETTERS PARA CONFIGURACIÓN EN CALIENTE ---
    def set_muted(self, muted):
        self.is_muted = muted
        self.config_manager.set("is_muted", muted)
        if muted: 
            self.is_speaking = False
            self.update_avatar()

    def set_shadow_enabled(self, enabled):
        self.shadow_enabled = enabled
        self.shadow_effect.setEnabled(enabled)
        self.config_manager.set("shadow_enabled", enabled)

    def set_bounce_enabled(self, enabled):
        self.bounce_enabled = enabled
        self.config_manager.set("bounce_enabled", enabled)
    
    def set_bounce_amplitude(self, value):
        self.bounce_amplitude = value
        self.config_manager.set("bounce_amplitude", value)

    def set_bounce_speed(self, value):
        self.bounce_speed = value
        self.config_manager.set("bounce_speed", value)

    def set_microphone(self, index):
        self.audio_thread.set_device(index)
        self.config_manager.set("microphone_index", index)

    # --- EVENTOS VENTANA ---
    def resizeEvent(self, event):
        rect = self.rect()
        self.sizegrip.move(rect.right() - self.sizegrip.width(), rect.bottom() - self.sizegrip.height())
        super().resizeEvent(event)

    def contextMenuEvent(self, event):
        self.bg_manager.show_context_menu(event.pos())

    def closeEvent(self, event):
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
    print("✨ AI-PNGTuber PRO (Modularizado & Optimizado) Iniciado.")
    sys.exit(app.exec())
import sys
import json
import urllib.request
import numpy as np
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QSizeGrip, QGraphicsDropShadowEffect, QPushButton, QSlider, QSizePolicy, QProgressBar, QMessageBox
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QUrl, QPoint
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QTransform, QShortcut, QKeySequence, QDesktopServices, QPen, QFont

CURRENT_VERSION = "1.0.0"
UPDATE_URL = "https://pastebin.com/raw/kPjwkJu2" # Placeholder

class UpdateChecker(QThread):
    update_available = pyqtSignal(str)

    def run(self):
        try:
            req = urllib.request.Request(
                UPDATE_URL, 
                headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'}
            )
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                remote_version = data.get("version", "0.0.0")
                download_url = data.get("url", "")
                
                print(f"[DEBUG] Check Update: {CURRENT_VERSION} vs {remote_version}")

                # Simple version comparison (assumes X.Y.Z format)
                if remote_version > CURRENT_VERSION:
                    print(f"[DEBUG] Update found: {download_url}")
                    self.update_available.emit(download_url)
                else:
                    print("[DEBUG] No update found.")

        except Exception as e:
            print(f"[ERROR] Update check failed: {e}")

class TutorialOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setGeometry(parent.rect())
        self.setVisible(False)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fondo semitransparente
        painter.fillRect(self.rect(), QColor(0, 0, 0, 150))
        
        # Configuración de Texto y Líneas
        pen = QPen(Qt.GlobalColor.white)
        pen.setWidth(2)
        painter.setPen(pen)
        
        font_title = QFont("Arial", 16, QFont.Weight.Bold)
        painter.setFont(font_title)
        
        rect = self.rect()
        center = rect.center()
        
        # 1. Flip & Menu (Centro)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Flip: Ctrl+F\nClick derecho: Menú")
        
        # 2. Volumen (Abajo, aprox)
        # Asumimos que la barra de volumen está en los últimos 20px
        start_arrow = QPoint(center.x(), rect.bottom() - 60)
        end_arrow = QPoint(center.x(), rect.bottom() - 20)
        painter.drawLine(start_arrow, end_arrow)
        
        painter.setFont(QFont("Arial", 12))
        painter.drawText(start_arrow.x() - 60, start_arrow.y() - 5, "Barra de Volumen")
        
        # 3. Mensaje de cierre
        painter.setFont(QFont("Arial", 10, QFont.Weight.Normal))
        painter.drawText(rect.adjusted(0, 0, 0, -50), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, "Haz clic para comenzar")

    def mousePressEvent(self, event):
        if self.parent_window:
            self.parent_window.mark_tutorial_completed()
        self.close()
        self.deleteLater()

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
        self.mic_sensitivity = self.config.get("mic_sensitivity", 1.0)
        self.audio_threshold = self.config.get("audio_threshold", 0.02)
        
        # Configuración Visual (Recuperada del JSON)
        self.bounce_enabled = self.config.get("bounce_enabled", True)
        self.bounce_amplitude = self.config.get("bounce_amplitude", 10)
        self.bounce_speed = self.config.get("bounce_speed", 0.3)
        self.bounce_phase = 0
        self.shadow_enabled = self.config.get("shadow_enabled", True)
        self.current_background = self.config.get("background_color", "transparent")
        self.is_flipped = False

        # 2. Iniciar Gestores
        self.profile_manager = AvatarProfileManager()
        profile_name = self.config.get("current_profile", "Default")
        self.profile_manager.set_profile(profile_name)

        # 3. Interfaz Gráfica
        self.init_ui()

        # 4. Sistemas de Audio e IA (Hilos)
        saved_mic = self.config.get("microphone_index")
        self.audio_thread = AudioMonitorThread(device_index=saved_mic, threshold=self.audio_threshold, sensitivity=self.mic_sensitivity)
        self.audio_thread.volume_signal.connect(self.update_mouth)
        self.audio_thread.audio_data_signal.connect(self.handle_audio)
        self.audio_thread.start()

        self.emotion_thread = EmotionThread()
        self.emotion_thread.emotion_signal.connect(self.update_emotion)
        self.emotion_thread.start()



        # 5. Update Checker
        self.update_checker = UpdateChecker()
        self.update_checker.update_available.connect(self.show_update_dialog)
        self.update_checker.start()

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

        # Shortcuts
        self.flip_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.flip_shortcut.activated.connect(self.toggle_flip)

        # 7. Tutorial (Onboarding)
        if not self.config.get("tutorial_completed", False):
            QTimer.singleShot(500, self.show_tutorial)

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
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        self.avatar_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.layout.addWidget(self.avatar_label, 1)

        # Botón Mute (Abajo)
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(10, 0, 10, 10)
        
        # Mute Button
        self.mute_btn = QPushButton("🔊")
        self.mute_btn.setFixedSize(30, 30)
        self.mute_btn.setCheckable(True)
        self.mute_btn.setChecked(self.is_muted)
        self.mute_btn.setStyleSheet("QPushButton { background-color: rgba(255,255,255,200); border-radius: 15px; border: 1px solid #ccc; } QPushButton:checked { background-color: #ff6666; border: 1px solid red; }")
        self.mute_btn.clicked.connect(self.set_muted)
        bottom_bar.addWidget(self.mute_btn)

        # Separador pequeño
        bottom_bar.addSpacing(10)

        # Botones de Emociones / Hotkeys
        hotkey_buttons = [
            ("🤖", "ai_mode", "Modo IA (Automático)"),
            ("😐", "neutral", "Neutral"),
            ("😄", "happiness", "Feliz"),
            ("😠", "anger", "Enojado"),
            ("😢", "sadness", "Triste")
        ]

        for icon, action, tooltip in hotkey_buttons:
            btn = QPushButton(icon)
            btn.setFixedSize(30, 30)
            btn.setToolTip(tooltip)
            btn.setStyleSheet("""
                QPushButton { 
                    background-color: rgba(255,255,255,150); 
                    border-radius: 15px; 
                    border: 1px solid rgba(0,0,0,50); 
                    font-size: 14px;
                } 
                QPushButton:hover { 
                    background-color: rgba(255,255,255,230); 
                    border: 1px solid rgba(0,0,0,100);
                }
                QPushButton:pressed {
                    background-color: rgba(200,200,200,230);
                }
            """)
            # Usamos lambda con default arg para capturar el valor actual de action
            btn.clicked.connect(lambda _, a=action: self.handle_hotkey(a))
            bottom_bar.addWidget(btn)

        bottom_bar.addStretch()

        # Barra de Volumen Visual
        self.volume_bar = QProgressBar()
        self.volume_bar.setRange(0, 100)
        self.volume_bar.setTextVisible(False)
        self.volume_bar.setFixedHeight(8)  # Delgada
        self.volume_bar.setStyleSheet("""
            QProgressBar {
                background-color: #333333;
                border: 1px solid #555555;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #00FF00;
                border-radius: 4px; 
            }
        """)
        bottom_bar.addWidget(self.volume_bar)
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

    # --- LÓGICA DE FLIP ---
    def toggle_flip(self):
        self.is_flipped = not self.is_flipped
        self.update_avatar()

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
            # Aplicar Flip si es necesario
            if self.is_flipped:
                pix = pix.transformed(QTransform().scale(-1, 1))

            # Escalar manteniendo aspect ratio dentro de las dimensiones disponibles
            w = self.avatar_label.width()
            h = self.avatar_label.height()
            if w > 0 and h > 0:
                self.avatar_label.setPixmap(pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    # --- CONECTORES (Señales) ---
    def handle_audio(self, chunk):
        if not self.is_muted:
            self.emotion_thread.add_audio(chunk)
            
            # Calcular nivel de volumen para la barra visual de manera simple con numpy
            try:
                rms = np.sqrt(np.mean(chunk**2))
                # Multiplicamos para que sea visible (ajustar factor según micrófono/necesidad)
                level = int(rms * 500) 
                self.volume_bar.setValue(min(100, level))
            except:
                pass
        else:
            self.volume_bar.setValue(0)

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

    def set_mic_sensitivity(self, value):
        self.mic_sensitivity = value
        self.audio_thread.set_sensitivity(value)
        self.config_manager.set("mic_sensitivity", value)

    def set_audio_threshold(self, value):
        self.audio_threshold = value
        self.audio_thread.set_threshold(value)
        self.config_manager.set("audio_threshold", value)

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
        self.update_avatar()
        
        # Actualizar overlay si existe
        if hasattr(self, 'tutorial') and self.tutorial and self.tutorial.isVisible():
             self.tutorial.setGeometry(rect)
             
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

    def show_update_dialog(self, url):
        msg = QMessageBox(self)
        msg.setWindowTitle("Actualización Disponible")
        msg.setText("¡Hay una nueva versión de PNGTuber disponible!")
        msg.setInformativeText("¿Deseas descargarla ahora?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl(url))

    def show_tutorial(self):
        self.tutorial = TutorialOverlay(self)
        self.tutorial.show()

    def mark_tutorial_completed(self):
        print("✅ Tutorial completado")
        self.config_manager.set("tutorial_completed", True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PNGTuberApp()
    window.show()
    sys.exit(app.exec())
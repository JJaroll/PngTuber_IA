import sys
import time
import threading
import numpy as np
import pyaudio
import torch
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QSizeGrip, QGraphicsDropShadowEffect, QPushButton
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor
from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor

# --- IMPORTAMOS LOS NUEVOS MÓDULOS ---
from profile_manager import AvatarProfileManager
from background import BackgroundManager
from mac_gui import MacWindowControls
from config_manager import ConfigManager

# --- CONFIGURACIÓN ---
CHUNK_SIZE = 1024
FORMAT = pyaudio.paFloat32
CHANNELS = 1
RATE = 16000
VOLUME_THRESHOLD = 0.02
EMOTION_WINDOW_SECONDS = 2.0
MODEL_NAME = "somosnlp-hackathon-2022/wav2vec2-base-finetuned-sentiment-classification-MESD"
# BOUNCE constants moved to instance variables

EMOTION_MAP = {
    "anger": "angry", "disgust": "angry", "fear": "sad",
    "happiness": "happy", "sadness": "sad", "neutral": "neutral"
}

# --- HILOS DE AUDIO E IA (Sin cambios en lógica interna) ---
class AudioMonitorThread(QThread):
    volume_signal = pyqtSignal(bool)
    audio_data_signal = pyqtSignal(np.ndarray)

    def __init__(self, device_index=None):
        super().__init__()
        self.running = True
        self.device_index = device_index
        self.p = pyaudio.PyAudio()
        self.start_stream()

    def start_stream(self):
        try:
            self.stream = self.p.open(
                format=FORMAT, 
                channels=CHANNELS, 
                rate=RATE, 
                input=True, 
                input_device_index=self.device_index,
                frames_per_buffer=CHUNK_SIZE
            )
        except Exception as e:
            print(f"Error abriendo stream: {e}")
            self.stream = None

    def change_device(self, index):
        self.running = False
        self.wait() # Esperar a que el loop termine
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        self.device_index = index
        self.start_stream()
        
        # Reiniciar thread
        self.running = True
        self.start()

    @staticmethod
    def list_devices():
        p = pyaudio.PyAudio()
        devices = []
        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        for i in range(0, numdevices):
            if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                name = p.get_device_info_by_host_api_device_index(0, i).get('name')
                devices.append((i, name))
        p.terminate()
        return devices

    def run(self):
        if not self.stream: return
        try:
            while self.running:
                try:
                    data = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
                    chunk = np.frombuffer(data, dtype=np.float32)
                    rms = np.sqrt(np.mean(chunk**2))
                    self.volume_signal.emit(rms > VOLUME_THRESHOLD)
                    self.audio_data_signal.emit(chunk)
                except: break
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            # No terminamos PyAudio aquí porque queremos reusarlo
            # self.p.terminate() 

    def stop(self): self.running = False 

class EmotionThread(QThread):
    emotion_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.audio_buffer = np.array([], dtype=np.float32)
        self.buffer_lock = threading.Lock()
        self.points = int(RATE * EMOTION_WINDOW_SECONDS)
        
        if torch.backends.mps.is_available(): self.device = torch.device("mps")
        elif torch.cuda.is_available(): self.device = torch.device("cuda")
        else: self.device = torch.device("cpu")

        try:
            self.feat = Wav2Vec2FeatureExtractor.from_pretrained(MODEL_NAME)
            self.model = Wav2Vec2ForSequenceClassification.from_pretrained(MODEL_NAME).to(self.device)
        except Exception as e:
            print(f"Error IA: {e}")
            self.running = False

    def add_audio(self, chunk):
        with self.buffer_lock:
            self.audio_buffer = np.concatenate((self.audio_buffer, chunk))
            if len(self.audio_buffer) > self.points * 2:
                self.audio_buffer = self.audio_buffer[-self.points * 2:]

    def run(self):
        while self.running:
            proc = None
            with self.buffer_lock:
                if len(self.audio_buffer) >= self.points:
                    proc = self.audio_buffer[-self.points:]
                    self.audio_buffer = np.array([], dtype=np.float32)
            if proc is not None: self.predict(proc)
            time.sleep(0.1)

    def predict(self, audio):
        try:
            if np.sqrt(np.mean(audio**2)) < VOLUME_THRESHOLD:
                self.emotion_signal.emit("neutral")
                return
            inp = self.feat(audio, sampling_rate=RATE, return_tensors="pt", padding=True).input_values.to(self.device)
            with torch.no_grad(): logits = self.model(inp).logits
            pid = torch.argmax(logits, dim=-1).item()
            lbl = str(self.model.config.id2label[pid]).lower()
            self.emotion_signal.emit(EMOTION_MAP.get(lbl, "neutral"))
        except: pass

    def stop(self): self.running = False

# --- APP PRINCIPAL ---
class PNGTuberApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # --- CONFIGURATION MANAGER ---
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()

        # --- Variables de Estado (Cargadas de config) ---
        self.current_emotion = "neutral"
        self.is_speaking = False
        
        # Audio / Mute
        self.is_muted = self.config.get("is_muted", False)
        
        # Rebote
        self.bounce_enabled = self.config.get("bounce_enabled", True)
        self.bounce_amplitude = self.config.get("bounce_amplitude", 10)
        self.bounce_speed = self.config.get("bounce_speed", 0.3)
        self.bounce_phase = 0

        # Fondo
        self.current_background = self.config.get("background_color", "transparent")

        # 1. Inicializar Gestor de Perfiles
        self.profile_manager = AvatarProfileManager()

        # 2. Configuración Ventana (MODO TRANSPARENTE)
        # Quitamos bordes nativos y activamos transparencia
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(400, 400)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(5, 5, 5, 5)

        # 3. Insertar Barra Mac Personalizada
        self.mac_controls = MacWindowControls(self)
        self.mac_controls.close_signal.connect(self.close)
        self.mac_controls.minimize_signal.connect(self.showMinimized)
        
        # Layout horizontal superior para los botones
        top_bar = QHBoxLayout()
        # Margen (Izquierda, Arriba, Derecha, Abajo) -> 13px izq/arriba simula padding nativo
        top_bar.setContentsMargins(13, 13, 0, 0) 
        top_bar.addWidget(self.mac_controls)
        top_bar.addStretch() # Empuja los botones a la izquierda
        
        self.layout.addLayout(top_bar)

        # 4. Avatar Label
        self.avatar_label = QLabel(self)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.avatar_label)

        # 5. Barra Inferior (Botón Mute)
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(10, 0, 10, 10)
        
        self.mute_btn = QPushButton("🔊")
        self.mute_btn.setCheckable(True)
        self.mute_btn.setFixedSize(30, 30)
        self.mute_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 200);
                border-radius: 15px;
                font-size: 14px;
                border: 1px solid #ccc;
            }
            QPushButton:checked {
                background-color: rgba(255, 100, 100, 200);
                border: 1px solid red;
            }
            QPushButton:hover {
                background-color: white;
            }
        """)
        self.mute_btn.clicked.connect(self.set_muted)
        
        bottom_bar.addWidget(self.mute_btn)
        bottom_bar.addStretch() # Empuja a la izquierda
        self.layout.addLayout(bottom_bar)

        # --- Sombra Suave ---
        self.shadow_enabled = True
        self.set_shadow_enabled(True)

        # --- Resize Grip (Agarradera invisible) ---
        self.sizegrip = QSizeGrip(self)
        self.sizegrip.setStyleSheet("QSizeGrip { background-color: transparent; width: 20px; height: 20px; }")

        # --- Timer de Animación ---
        self.bounce_timer = QTimer()
        self.bounce_timer.timeout.connect(self.animate_bounce)
        self.bounce_phase = 0
        self.bounce_timer.start(30) # 30 FPS

        # 5. Gestor de Fondo (Le pasamos el profile_manager)
        self.bg_manager = BackgroundManager(self, self.profile_manager, self.config_manager)

        # 6. Iniciar Hilos
        self.audio_thread = AudioMonitorThread()
        self.audio_thread.volume_signal.connect(self.update_mouth)
        self.audio_thread.audio_data_signal.connect(self.handle_audio)
        self.audio_thread.start()

        self.emotion_thread = EmotionThread()
        # --- APLICAR ESTADO GUARDADO ---
        # 1. Perfil
        saved_profile = self.config.get("current_profile", "Default")
        if saved_profile in self.profile_manager.profiles:
            self.profile_manager.current_profile = saved_profile
        
        # 2. Micrófono
        saved_mic = self.config.get("microphone_index")
        if saved_mic is not None:
            self.audio_thread.device_index = saved_mic
            # El thread ya inició, pero si lo cambiamos, deberíamos reiniciarlo o dejar que change_device lo haga
            # Como change_device reinicia el thread, es mejor llamarlo si es distinto al default
            # Pero para simplificar, confiamos en que device_index se use si reiniciamos o en el próximo start
            # Forzamos cambio si es necesario:
            self.audio_thread.change_device(saved_mic)

        # 3. Aplicar Fondo
        if self.current_background == "transparent":
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.central_widget.setStyleSheet("background: transparent;")
        else:
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            self.central_widget.setStyleSheet(f"background-color: {self.current_background}; border-radius: 20px; border: 1px solid rgba(0,0,0,50);")

        # 4. Sombra (Seteado en UI pero validamos aquí)
        self.shadow_enabled = self.config.get("shadow_enabled", True)
        self.set_shadow_enabled(self.shadow_enabled)
        
        # 5. Mute (Sync UI)
        self.set_muted(self.is_muted)

        self.update_avatar()

    def animate_bounce(self):
        if self.is_speaking and self.bounce_enabled:
            self.bounce_phase += self.bounce_speed
            # Usamos seno absoluto para crear el salto hacia arriba
            offset = int(abs(np.sin(self.bounce_phase)) * self.bounce_amplitude)
            # Aplicamos margen inferior para empujar la imagen arriba
            self.avatar_label.setContentsMargins(0, 0, 0, offset)
        elif self.bounce_phase != 0:
            # Reset suave
            self.bounce_phase = 0
            self.avatar_label.setContentsMargins(0, 0, 0, 0)

    def set_bounce_enabled(self, enabled):
        self.bounce_enabled = enabled
        if not enabled:
            # Reset inmediato si se desactiva
            self.bounce_phase = 0
            self.avatar_label.setContentsMargins(0, 0, 0, 0)

    def set_bounce_amplitude(self, value):
        self.bounce_amplitude = value

    def set_bounce_speed(self, value):
        self.bounce_speed = value

    def resizeEvent(self, event):
        # Mantiene la agarradera siempre en la esquina inferior derecha
        rect = self.rect()
        self.sizegrip.move(rect.right() - self.sizegrip.width(), rect.bottom() - self.sizegrip.height())
        super().resizeEvent(event)

    def contextMenuEvent(self, event):
        self.bg_manager.show_context_menu(event.pos())

    def handle_audio(self, chunk):
        if self.is_muted: return
        self.emotion_thread.add_audio(chunk)

    def update_mouth(self, speaking):
        if self.is_muted: speaking = False
        
        if self.is_speaking != speaking:
            self.is_speaking = speaking
            self.update_avatar()

    def set_microphone(self, index):
        print(f"🎤 Cambiando micrófono a ID: {index}")
        self.audio_thread.change_device(index)

    def set_muted(self, muted):
        self.is_muted = muted
        # Sincronizar botón si fue llamado externamente (menú)
        if self.mute_btn.isChecked() != muted:
            self.mute_btn.setChecked(muted)
            
        self.mute_btn.setText("🔇" if muted else "🔊")
        
        if muted:
            self.is_speaking = False
            self.current_emotion = "neutral"
            self.update_avatar()
        print(f"🔇 Silencio: {muted}")

    def set_shadow_enabled(self, enabled):
        self.shadow_enabled = enabled
        if enabled:
            effect = QGraphicsDropShadowEffect()
            effect.setBlurRadius(20)
            effect.setColor(QColor(0, 0, 0, 150))
            effect.setOffset(0, 5)
            self.avatar_label.setGraphicsEffect(effect)
        else:
            self.avatar_label.setGraphicsEffect(None)

    def update_emotion(self, emo):
        if self.current_emotion != emo:
            self.current_emotion = emo
            self.update_avatar()

    def update_avatar(self):
        state = "open" if self.is_speaking else "closed"
        # Usamos el ProfileManager para obtener la ruta
        path = self.profile_manager.get_image_path(self.current_emotion, state)
        
        pix = QPixmap(path)
        if pix.isNull():
            # Fallback a neutral del mismo perfil
            fallback = self.profile_manager.get_image_path("neutral", state)
            pix = QPixmap(fallback)
            if pix.isNull():
                self.draw_placeholder()
            else:
                self.avatar_label.setPixmap(pix.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.avatar_label.setPixmap(pix.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def draw_placeholder(self):
        img = QImage(400, 400, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setBrush(Qt.GlobalColor.blue)
        p.drawEllipse(50, 50, 300, 300)
        p.end()
        self.avatar_label.setPixmap(QPixmap.fromImage(img))

    def closeEvent(self, event):
        # Guardar Configuración
        config = {
            "current_profile": self.profile_manager.current_profile,
            "bounce_enabled": self.bounce_enabled,
            "bounce_amplitude": self.bounce_amplitude,
            "bounce_speed": self.bounce_speed,
            "shadow_enabled": self.shadow_enabled,
            "is_muted": self.is_muted,
            "background_color": self.current_background,
            "microphone_index": self.audio_thread.device_index
        }
        self.config_manager.save_config(config)

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

    def showEvent(self, event):
        super().showEvent(event)
        # Force a small resize to ensure transparency mask is applied correctly on macOS
        # sometimes the initial paint event doesn't catch the translucent attribute
        self.resize(self.width(), self.height())
        self.update()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PNGTuberApp()
    window.show()
    print("✨ AI-PNGTuber Modularizado Iniciado.")
    sys.exit(app.exec())

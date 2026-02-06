import sys
import time
import threading
import numpy as np
import pyaudio
import torch
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QPainter
from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor

# --- IMPORTAMOS LOS NUEVOS MÓDULOS ---
from profile_manager import AvatarProfileManager
from background import BackgroundManager
from mac_gui import MacWindowControls

# --- CONFIGURACIÓN ---
CHUNK_SIZE = 1024
FORMAT = pyaudio.paFloat32
CHANNELS = 1
RATE = 16000
VOLUME_THRESHOLD = 0.02
EMOTION_WINDOW_SECONDS = 2.0
MODEL_NAME = "somosnlp-hackathon-2022/wav2vec2-base-finetuned-sentiment-classification-MESD"

EMOTION_MAP = {
    "anger": "angry", "disgust": "angry", "fear": "sad",
    "happiness": "happy", "sadness": "sad", "neutral": "neutral"
}

# --- HILOS DE AUDIO E IA (Sin cambios en lógica interna) ---
class AudioMonitorThread(QThread):
    volume_signal = pyqtSignal(bool)
    audio_data_signal = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self.running = True
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK_SIZE)

    def run(self):
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
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()

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
        self.current_emotion = "neutral"
        self.is_speaking = False

        # 1. Inicializar Gestor de Perfiles
        self.profile_manager = AvatarProfileManager()

        # 2. Configuración Ventana
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(400, 400)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # 3. Interfaz Mac
        self.mac_controls = MacWindowControls(self)
        self.mac_controls.close_signal.connect(self.close)
        self.mac_controls.minimize_signal.connect(self.showMinimized)
        
        top = QHBoxLayout()
        top.setContentsMargins(10, 10, 0, 0)
        top.addWidget(self.mac_controls)
        top.addStretch()
        self.layout.addLayout(top)

        # 4. Avatar Label
        self.avatar_label = QLabel(self)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.avatar_label)

        # 5. Gestor de Fondo (Le pasamos el profile_manager)
        self.bg_manager = BackgroundManager(self, self.profile_manager)

        # 6. Iniciar Hilos
        self.audio_thread = AudioMonitorThread()
        self.audio_thread.volume_signal.connect(self.update_mouth)
        self.audio_thread.audio_data_signal.connect(self.handle_audio)
        self.audio_thread.start()

        self.emotion_thread = EmotionThread()
        self.emotion_thread.emotion_signal.connect(self.update_emotion)
        self.emotion_thread.start()

        self.update_avatar()

    def contextMenuEvent(self, event):
        self.bg_manager.show_context_menu(event.pos())

    def handle_audio(self, chunk):
        self.emotion_thread.add_audio(chunk)

    def update_mouth(self, speaking):
        if self.is_speaking != speaking:
            self.is_speaking = speaking
            self.update_avatar()

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
            if pix.isNull(): self.draw_placeholder()
            else: self.avatar_label.setPixmap(pix.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
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
    print("✨ AI-PNGTuber Modularizado Iniciado.")
    sys.exit(app.exec())

import sys
import time
import queue
import threading
import numpy as np
import pyaudio
import torch
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QImage
from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor

# --- Configuración ---
CHUNK_SIZE = 1024
FORMAT = pyaudio.paFloat32
CHANNELS = 1
RATE = 16000  # Wav2Vec2 suele requerir 16kHz
VOLUME_THRESHOLD = 0.02  # Ajustado para RMS (approx -34dB). Subir si detecta ruido.
EMOTION_WINDOW_SECONDS = 2.0
MODEL_NAME = "somosnlp-hackathon-2022/wav2vec2-base-finetuned-sentiment-classification-MESD"

# Mapeo de emociones
EMOTION_MAP = {
    "anger": "angry",
    "disgust": "angry",  # Asco -> Cara de enojo
    "fear": "sad",       # Miedo -> Cara de susto/tristeza
    "happiness": "happy",
    "sadness": "sad",
    "neutral": "neutral"
}

# Rutas de imágenes
AVATAR_IMAGES = {
    "neutral_closed": "avatars/neutral_closed.PNG",
    "neutral_open": "avatars/neutral_open.PNG",
    "happy_closed": "avatars/happy_closed.PNG",
    "happy_open": "avatars/happy_open.PNG",
    "angry_closed": "avatars/angry_closed.PNG",
    "angry_open": "avatars/angry_open.PNG",
    "sad_closed": "avatars/sad_closed.PNG",
    "sad_open": "avatars/sad_open.PNG",
}

class AudioMonitorThread(QThread):
    volume_signal = pyqtSignal(bool)  # True si habla (boca abierta), False si no
    audio_data_signal = pyqtSignal(np.ndarray) # Envía chunks para emoción

    def __init__(self):
        super().__init__()
        self.running = True
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=FORMAT,
                                  channels=CHANNELS,
                                  rate=RATE,
                                  input=True,
                                  frames_per_buffer=CHUNK_SIZE)

    def run(self):
        try:
            while self.running:
                try:
                    data = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
                    audio_chunk = np.frombuffer(data, dtype=np.float32)
                    
                    # Detectar volumen usando RMS (Root Mean Square)
                    rms = np.sqrt(np.mean(audio_chunk**2))
                    is_speaking = rms > VOLUME_THRESHOLD
                    self.volume_signal.emit(bool(is_speaking))

                    # Enviar datos para análisis de emoción
                    self.audio_data_signal.emit(audio_chunk)

                except Exception as e:
                    print(f"Error en audio thread: {e}")
                    break
        finally:
            # Limpieza segura en el mismo hilo
            if self.stream.is_active():
                self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()
            print("Audio thread cerrado correctamente.")

    def stop(self):
        self.running = False

class EmotionThread(QThread):
    emotion_signal = pyqtSignal(str) # "neutral", "happy", "angry", "sad"

    def __init__(self):
        super().__init__()
        self.running = True
        self.audio_buffer = np.array([], dtype=np.float32)
        self.buffer_lock = threading.Lock()
        self.points_per_window = int(RATE * EMOTION_WINDOW_SECONDS)
        
        # Cargar modelo e inferencia en MPS
        print("Cargando modelo de emociones en MPS...")
        try:
            self.device = torch.device("mps")
            self.feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(MODEL_NAME)
            self.model = Wav2Vec2ForSequenceClassification.from_pretrained(MODEL_NAME).to(self.device)
            print("Modelo cargado exitosamente en MPS.")
        except Exception as e:
            print(f"Error cargando modelo: {e}")
            self.running = False

    def add_audio(self, chunk):
        with self.buffer_lock:
            self.audio_buffer = np.concatenate((self.audio_buffer, chunk))
            # Mantener solo un poco más de lo necesario para evitar crecimiento infinito si el procesamiento es lento
            if len(self.audio_buffer) > self.points_per_window * 2:
                self.audio_buffer = self.audio_buffer[-self.points_per_window * 2:]

    def run(self):
        while self.running:
            process_audio = None
            with self.buffer_lock:
                if len(self.audio_buffer) >= self.points_per_window:
                    # Tomar los últimos 1.5 segundos
                    process_audio = self.audio_buffer[-self.points_per_window:]
                    # Limpiar buffer parcialmente (overlap si se desea, aquí simple)
                    self.audio_buffer = np.array([], dtype=np.float32) 
            
            if process_audio is not None:
                self.predict_emotion(process_audio)
            
            time.sleep(0.1) # No saturar el hilo

    def predict_emotion(self, audio_data):
        try:
            # Gating de silencio: Si el volumen promedio del segmento es muy bajo, forzar neutral
            window_rms = np.sqrt(np.mean(audio_data**2))
            if window_rms < VOLUME_THRESHOLD:
                self.emotion_signal.emit("neutral")
                # print(f"Silencio detectado ({window_rms:.4f} < {VOLUME_THRESHOLD}). Forzando neutral.")
                return

            inputs = self.feature_extractor(audio_data, sampling_rate=RATE, return_tensors="pt", padding=True)
            input_values = inputs.input_values.to(self.device)

            with torch.no_grad():
                logits = self.model(input_values).logits

            # --- LÓGICA FLEXIBLE ---
            predicted_class_id = torch.argmax(logits, dim=-1).item()
            
            # Obtenemos la etiqueta del modelo (puede ser 'anger' o 'ang' o '0')
            raw_label = self.model.config.id2label[predicted_class_id]
            
            # Convertimos a minúsculas para evitar errores (Ej: 'Anger' -> 'anger')
            predicted_label = str(raw_label).lower()
            
            # Buscamos en el mapa, si no existe, mantenemos la emoción actual o neutral
            emotion = EMOTION_MAP.get(predicted_label, "neutral")
            
            self.emotion_signal.emit(emotion)
            print(f"IA: {raw_label} ({predicted_class_id}) -> Avatar: {emotion}")

        except Exception as e:
            print(f"Error inferencia: {e}")

    def stop(self):
        self.running = False

class PNGTuberApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.current_emotion = "neutral"
        self.is_speaking = False

        # Configuración de ventana
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(400, 400) # Tamaño inicial

        # Widget central
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Importar y añadir controles de Mac
        from mac_gui import MacWindowControls
        self.mac_controls = MacWindowControls(self)
        self.mac_controls.close_signal.connect(self.close)
        self.mac_controls.minimize_signal.connect(self.showMinimized)
        
        # Añadir controles al layout superior
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(10, 10, 0, 0) # Margen para que no quede pegado
        controls_layout.addWidget(self.mac_controls)
        controls_layout.addStretch() # Empujar a la izquierda
        
        self.layout.addLayout(controls_layout)

        # Avatar Label
        self.avatar_label = QLabel(self)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.avatar_label)

        # Placeholder visuals (generar imágenes dummy si no existen)
        self.generate_placeholders()

        # Iniciar hilos
        self.audio_thread = AudioMonitorThread()
        self.audio_thread.volume_signal.connect(self.update_mouth_state)
        self.audio_thread.audio_data_signal.connect(self.handle_audio_data)
        self.audio_thread.start()

        self.emotion_thread = EmotionThread()
        self.emotion_thread.emotion_signal.connect(self.update_emotion)
        self.emotion_thread.start()

        self.update_avatar()

    def handle_audio_data(self, chunk):
        self.emotion_thread.add_audio(chunk)

    def update_mouth_state(self, is_speaking):
        if self.is_speaking != is_speaking:
            self.is_speaking = is_speaking
            self.update_avatar()

    def update_emotion(self, emotion):
        if self.current_emotion != emotion:
            self.current_emotion = emotion
            self.update_avatar()

    def update_avatar(self):
        state = "open" if self.is_speaking else "closed"
        key = f"{self.current_emotion}_{state}"
        
        # Fallback a neutral si la emoción no tiene imagen específica
        if key not in AVATAR_IMAGES:
             key = f"neutral_{state}"

        image_path = AVATAR_IMAGES.get(key, "")
        
        # Cargar imagen (o placeholder si falla)
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            # Crear un placeholder de color si no hay imagen
            color = Qt.GlobalColor.green if self.is_speaking else Qt.GlobalColor.blue
            if self.current_emotion == "angry": color = Qt.GlobalColor.red
            if self.current_emotion == "happy": color = Qt.GlobalColor.yellow
            if self.current_emotion == "sad": color = Qt.GlobalColor.darkGray
            
            img = QImage(400, 400, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            from PyQt6.QtGui import QPainter, QColor
            painter = QPainter(img)
            painter.setBrush(color)
            painter.drawEllipse(50, 50, 300, 300)
            painter.end()
            pixmap = QPixmap.fromImage(img)

        self.avatar_label.setPixmap(pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def generate_placeholders(self):
        # Esta función es solo para que la app no crashee sin imágenes.
        # En producción, el usuario debe poner sus PNGs en la carpeta avatars/
        import os
        if not os.path.exists("avatars"):
            os.makedirs("avatars")
            print("Creada carpeta 'avatars'. Por favor coloca tus imágenes ahí.")

    def closeEvent(self, event):
        self.audio_thread.stop()
        self.emotion_thread.stop()
        self.audio_thread.wait()
        self.emotion_thread.wait()
        event.accept()

    # Mover ventana al hacer clic y arrastrar
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
    print("AI-PNGTuber iniciada. Presiona Ctrl+C en la terminal o cierra la ventana para salir.")
    sys.exit(app.exec())

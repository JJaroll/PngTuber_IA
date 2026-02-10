import time
import threading
import numpy as np
import pyaudio
import torch
from PyQt6.QtCore import QThread, pyqtSignal
from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor

# --- CONFIGURACIÓN ---
CHUNK_SIZE = 1024
FORMAT = pyaudio.paFloat32
CHANNELS = 1
RATE = 16000
VOLUME_THRESHOLD = 0.02
EMOTION_WINDOW_SECONDS = 2.0
MODEL_NAME = "somosnlp-hackathon-2022/wav2vec2-base-finetuned-sentiment-classification-MESD"

# --- Mapeo de emociones ---
EMOTION_MAP = {
    "anger": "angry", "disgust": "angry", "fear": "sad",
    "happiness": "happy", "sadness": "sad", "neutral": "neutral"
}

class AudioMonitorThread(QThread):
    volume_signal = pyqtSignal(bool)
    audio_data_signal = pyqtSignal(np.ndarray)

    def __init__(self, device_index=None, threshold=VOLUME_THRESHOLD, sensitivity=1.0):
        super().__init__()
        self.running = True
        self.device_index = device_index
        self.threshold = threshold
        self.sensitivity = sensitivity
        self.p = pyaudio.PyAudio()
        self.stream = None
        
        # --- NUEVO: Variables para cambio seguro de hilo ---
        self.pending_device_index = None
        self.trigger_device_change = False
        # -------------------------------------------------
        
        self.start_stream()

    def start_stream(self):
        # Cerrar stream anterior si existe
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except: pass

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
        """Solicita el cambio de micrófono de manera segura (flag)"""
        # En lugar de reiniciar aquí, solo marcamos la solicitud
        self.pending_device_index = index
        self.trigger_device_change = True

    def set_sensitivity(self, value):
        self.sensitivity = value

    def set_threshold(self, value):
        self.threshold = value

    def list_devices(self):
        """Devuelve la lista de micrófonos para el menú"""
        devices = []
        try:
            info = self.p.get_host_api_info_by_index(0)
            num_devices = info.get('deviceCount')
            for i in range(num_devices):
                if (self.p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                    name = self.p.get_device_info_by_host_api_device_index(0, i).get('name')
                    devices.append((i, name))
        except: pass
        return devices

    def run(self):
        while self.running:
            # 1. VERIFICAR SI HAY UN CAMBIO PENDIENTE
            if self.trigger_device_change:
                self.device_index = self.pending_device_index
                self.start_stream() # El propio hilo reinicia su stream
                self.trigger_device_change = False

            # 2. LEER AUDIO
            if self.stream and self.stream.is_active():
                try:
                    data = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
                    chunk = np.frombuffer(data, dtype=np.float32)
                    
                    # Aplicar sensibilidad
                    chunk = chunk * self.sensitivity
                    
                    rms = np.sqrt(np.mean(chunk**2))
                    self.volume_signal.emit(rms > self.threshold)
                    self.audio_data_signal.emit(chunk)
                except:
                    time.sleep(0.1) # Pausa breve si hay error de lectura
                    continue
            else:
                time.sleep(0.1)

    def stop(self):
        self.running = False
        self.wait()
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except: pass
        self.p.terminate()

class EmotionThread(QThread):
    emotion_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.audio_buffer = np.array([], dtype=np.float32)
        self.buffer_lock = threading.Lock()
        self.points = int(RATE * EMOTION_WINDOW_SECONDS)
        
        # Detección automática de hardware para PyTorch
        if torch.backends.mps.is_available(): self.device = torch.device("mps")
        elif torch.cuda.is_available(): self.device = torch.device("cuda")
        else: self.device = torch.device("cpu")

        try:
            self.feat = Wav2Vec2FeatureExtractor.from_pretrained(MODEL_NAME)
            self.model = Wav2Vec2ForSequenceClassification.from_pretrained(MODEL_NAME).to(self.device)
        except Exception as e:
            print(f"Error cargando IA: {e}")
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
            
            if proc is not None: 
                self.predict(proc)
            time.sleep(0.1)

    def predict(self, audio):
        try:
            if np.sqrt(np.mean(audio**2)) < VOLUME_THRESHOLD:
                self.emotion_signal.emit("neutral")
                return
            inp = self.feat(audio, sampling_rate=RATE, return_tensors="pt", padding=True).input_values.to(self.device)
            with torch.no_grad(): 
                logits = self.model(inp).logits
            pid = torch.argmax(logits, dim=-1).item()
            lbl = str(self.model.config.id2label[pid]).lower()
            self.emotion_signal.emit(EMOTION_MAP.get(lbl, "neutral"))
        except: pass

    def stop(self):
        self.running = False
        self.wait()
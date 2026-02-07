import time
import threading
import numpy as np
import pyaudio
import torch
from PyQt6.QtCore import QThread, pyqtSignal
from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor

# --- CONFIGURACIÓN DE AUDIO E IA ---
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

class AudioMonitorThread(QThread):
    """Hilo encargado de escuchar el micrófono y calcular el volumen RMS"""
    volume_signal = pyqtSignal(bool)       # ¿Está hablando?
    audio_data_signal = pyqtSignal(np.ndarray) # Datos crudos para la IA

    def __init__(self, device_index=None):
        super().__init__()
        self.running = True
        self.device_index = device_index
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.start_stream()

    def start_stream(self):
        """Inicia o reinicia el stream de audio"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()

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
            print(f"Error abriendo stream de audio: {e}")

    def run(self):
        try:
            while self.running:
                if self.stream and self.stream.is_active():
                    try:
                        data = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
                        chunk = np.frombuffer(data, dtype=np.float32)
                        
                        # Calcular volumen
                        rms = np.sqrt(np.mean(chunk**2))
                        self.volume_signal.emit(rms > VOLUME_THRESHOLD)
                        
                        # Enviar a la IA
                        self.audio_data_signal.emit(chunk)
                    except Exception:
                        continue
                else:
                    time.sleep(0.1)
        finally:
            self.cleanup()

    def set_device(self, index):
        """Cambia el micrófono en caliente"""
        self.device_index = index
        self.start_stream()

    def list_devices(self):
        """Devuelve una lista de (index, nombre) de micrófonos"""
        devices = []
        info = self.p.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        for i in range(num_devices):
            if (self.p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                name = self.p.get_device_info_by_host_api_device_index(0, i).get('name')
                devices.append((i, name))
        return devices

    def cleanup(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()

    def stop(self):
        self.running = False
        self.wait()

class EmotionThread(QThread):
    """Hilo encargado de cargar el modelo IA y predecir emociones"""
    emotion_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.audio_buffer = np.array([], dtype=np.float32)
        self.buffer_lock = threading.Lock()
        self.points = int(RATE * EMOTION_WINDOW_SECONDS)
        
        # Selección de dispositivo optimizada
        if torch.backends.mps.is_available(): 
            self.device = torch.device("mps") # Mac M1/M2/M3
            print("🚀 Usando Aceleración Apple Metal (MPS)")
        elif torch.cuda.is_available(): 
            self.device = torch.device("cuda") # NVIDIA
            print("🚀 Usando Aceleración CUDA")
        else: 
            self.device = torch.device("cpu")
            print("⚠️ Usando CPU (Más lento)")

        # Carga del modelo (Puede tardar un poco)
        try:
            self.feat = Wav2Vec2FeatureExtractor.from_pretrained(MODEL_NAME)
            self.model = Wav2Vec2ForSequenceClassification.from_pretrained(MODEL_NAME).to(self.device)
        except Exception as e:
            print(f"Error cargando IA: {e}")
            self.running = False

    def add_audio(self, chunk):
        with self.buffer_lock:
            self.audio_buffer = np.concatenate((self.audio_buffer, chunk))
            # Mantener solo los últimos segundos necesarios
            if len(self.audio_buffer) > self.points * 2:
                self.audio_buffer = self.audio_buffer[-self.points * 2:]

    def run(self):
        while self.running:
            proc = None
            with self.buffer_lock:
                if len(self.audio_buffer) >= self.points:
                    proc = self.audio_buffer[-self.points:]
                    self.audio_buffer = np.array([], dtype=np.float32) # Limpiar buffer procesado
            
            if proc is not None: 
                self.predict(proc)
            
            time.sleep(0.1) # No saturar el hilo

    def predict(self, audio):
        try:
            # Si hay silencio absoluto, no gastar recursos en IA
            if np.sqrt(np.mean(audio**2)) < VOLUME_THRESHOLD:
                self.emotion_signal.emit("neutral")
                return

            # Inferencia
            inp = self.feat(audio, sampling_rate=RATE, return_tensors="pt", padding=True).input_values.to(self.device)
            with torch.no_grad(): 
                logits = self.model(inp).logits
            
            pid = torch.argmax(logits, dim=-1).item()
            lbl = str(self.model.config.id2label[pid]).lower()
            
            # Mapeo a nuestras emociones
            self.emotion_signal.emit(EMOTION_MAP.get(lbl, "neutral"))
        except Exception as e:
            print(f"Error predicción: {e}")

    def stop(self):
        self.running = False
        self.wait()
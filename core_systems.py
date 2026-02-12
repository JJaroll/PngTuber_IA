"""
PNGTuber IA
-----------
Una aplicación de avatar virtual controlada por voz e Inteligencia Artificial.

Desarrollado por: JJaroll
GitHub: https://github.com/JJaroll
Fecha: 10/02/2026
Licencia: MIT
"""

__author__ = "JJaroll"
__version__ = "1.0.0"
__maintainer__ = "JJaroll"
__status__ = "Production"

import time
import threading
import numpy as np
import pyaudio
import torch
from torch import nn
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from transformers import AutoModelForAudioClassification, Wav2Vec2FeatureExtractor, Wav2Vec2PreTrainedModel, Wav2Vec2Model
from huggingface_hub import snapshot_download
import sys
import re

# --- CONFIGURACIÓN ---
CHUNK_SIZE = 1024
FORMAT = pyaudio.paFloat32
CHANNELS = 1
RATE = 16000
VOLUME_THRESHOLD = 0.02
EMOTION_WINDOW_SECONDS = 2.0
MODEL_NAME = "somosnlp-hackathon-2022/wav2vec2-base-finetuned-sentiment-classification-MESD"

# --- Mapeo de emociones ---

# --- MODELOS SOPORTADOS ---
SUPPORTED_MODELS = {
    "spanish": {
        "name": "Español (SomosNLP)",
        "id": "somosnlp-hackathon-2022/wav2vec2-base-finetuned-sentiment-classification-MESD",
        "avatar_states": ["neutral", "happy", "sad", "angry"],
        "mapping": {
            "anger": "angry", "disgust": "angry", "fear": "sad",
            "happiness": "happy", "sadness": "sad", "neutral": "neutral"
        }
    },
    "english": {
        "name": "Global (Ehcalabres)",
        "id": "ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition",
        "avatar_states": ["neutral", "happy", "sad", "angry", "surprise", "disgust", "fear"],
        "mapping": {
            "angry": "angry",
            "calm": "neutral",
            "disgust": "disgust",
            "fearful": "fear",
            "happy": "happy",
            "neutral": "neutral",
            "sad": "sad",
            "surprised": "surprise"
        }
    }
}

# --- Hilo de Descarga ---
class DownloadStream(QObject):
    """Intercepta la salida de stderr (tqdm) para emitir señales de progreso y logs."""
    progress_signal = pyqtSignal(int)
    log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.cancel_requested = False
        self.buffer = ""

    def write(self, text):
        if self.cancel_requested:
            raise Exception("Download Cancelled by User")

        self.log_signal.emit(text)

        match = re.search(r"(\d+)%", text)
        if match:
            try:
                percent = int(match.group(1))
                self.progress_signal.emit(percent)
            except: pass

    def flush(self):
        pass

class EhcalabresHead(nn.Module):
    """La 'cabeza' específica que estructura las capas internas"""
    def __init__(self, config):
        super().__init__()
        # Replicamos exactamente 'classifier.dense'
        self.dense = nn.Linear(config.hidden_size, config.hidden_size)
        self.dropout = nn.Dropout(getattr(config, "final_dropout", 0.1))
        # Replicamos exactamente 'classifier.output'
        self.output = nn.Linear(config.hidden_size, config.num_labels)

    def forward(self, features, **kwargs):
        x = features
        x = self.dropout(x)
        x = self.dense(x)
        x = torch.tanh(x)
        x = self.dropout(x)
        x = self.output(x)
        return x

class EhcalabresModel(Wav2Vec2PreTrainedModel):
    """El modelo principal que contiene la cabeza"""
    def __init__(self, config):
        super().__init__(config)
        self.wav2vec2 = Wav2Vec2Model(config)
        self.dropout = nn.Dropout(getattr(config, "final_dropout", 0.1))
        
        # AQUÍ ESTÁ LA MAGIA:
        # Al llamar a esto 'self.classifier' y usar la clase de arriba...
        # ...se crean automáticamente 'classifier.dense' y 'classifier.output'
        self.classifier = EhcalabresHead(config)
        
        self.init_weights()

    def forward(self, input_values):
        outputs = self.wav2vec2(input_values)
        hidden_states = outputs[0]
        # Promedio (Mean Pooling)
        hidden_states = torch.mean(hidden_states, dim=1)
        logits = self.classifier(hidden_states)
        return type('ModelOutput', (object,), {'logits': logits})
class ModelDownloaderThread(QThread):
    finished_signal = pyqtSignal(bool, str)
    progress_update = pyqtSignal(int)
    log_update = pyqtSignal(str)

    def __init__(self, model_id):
        super().__init__()
        self.model_id = model_id
        self.stream = DownloadStream()
        
        self.stream.progress_signal.connect(self.progress_update.emit)
        self.stream.log_signal.connect(self.log_update.emit)

    def cancel(self):
        self.stream.cancel_requested = True

    def run(self):
        original_stderr = sys.stderr
        sys.stderr = self.stream
        
        try:
            print(f"⬇️ Iniciando descarga de: {self.model_id}")
            self.log_update.emit(f"Iniciando descarga de: {self.model_id}\n")
            
            snapshot_download(repo_id=self.model_id)
            
            self.finished_signal.emit(True, "Descarga completada")
        except Exception as e:
            msg = str(e)
            if "Download Cancelled" in msg:
                self.finished_signal.emit(False, "Cancelado por el usuario.")
            else:
                self.finished_signal.emit(False, msg)
        finally:
            sys.stderr = original_stderr # Restaurar siempre

def is_model_cached(model_id):
    try:
        snapshot_download(repo_id=model_id, local_files_only=True)
        return True
    except:
        return False

def get_model_path(model_id):
    try:
        return snapshot_download(repo_id=model_id, local_files_only=True)
    except:
        return None

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
        
        # Variables para cambio seguro de hilo
        self.pending_device_index = None
        self.trigger_device_change = False
        
        self.start_stream()

    def start_stream(self):
        # Cerrar stream anterior si existe
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except: pass
        self.stream = None # Asegurarse de que el stream se resetee

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
        self.pending_device_index = index
        self.trigger_device_change = True

    def set_sensitivity(self, value):
        self.sensitivity = value

    def set_threshold(self, value):
        self.threshold = value

    def list_devices(self):
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
                self.start_stream()
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

        self.feat = None
        self.model = None
        self.current_model_key = None
        self.map = {}

    def set_model(self, model_key):
        config = SUPPORTED_MODELS.get(model_key)
        if not config: return
        
        self.current_model_key = model_key
        self.map = config["mapping"]
        model_id = config["id"]

        print(f"🧠 Cargando modelo: {config['name']} ({model_id})...")
        try:
            self.feat = Wav2Vec2FeatureExtractor.from_pretrained(model_id)
            if "ehcalabres" in model_id:
                # Usamos nuestra clase personalizada
                self.model = EhcalabresModel.from_pretrained(model_id).to(self.device)
            else:
                # Usamos la carga estándar para otros modelos
                self.model = AutoModelForAudioClassification.from_pretrained(model_id).to(self.device)
            print("✅ Modelo IA cargado correctamente.")
        except Exception as e:
            print(f"❌ Error cargando modelo: {e}")
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
            
            if proc is not None and self.model is not None: 
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
            
            mapped_emotion = self.map.get(lbl, "neutral")
            self.emotion_signal.emit(mapped_emotion)
        except Exception as e: 
            pass

    def stop(self):
        self.running = False
        self.wait()
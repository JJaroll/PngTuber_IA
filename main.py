import sys
import numpy as np
from PyQt6.QtWidgets import (QApplication, QLabel, QMainWindow, QVBoxLayout, 
                             QWidget, QHBoxLayout, QSizeGrip, QGraphicsDropShadowEffect, 
                             QPushButton, QSizePolicy, QMessageBox, QSystemTrayIcon, QMenu)
from PyQt6.QtCore import Qt, QTimer, QUrl, QPoint, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import (QPixmap, QPainter, QColor, QTransform, QShortcut, 
                         QKeySequence, QDesktopServices, QPen, QFont, QBrush, QIcon, QAction)

# --- IMPORTS LOCALES ---
from profile_manager import AvatarProfileManager
from background import BackgroundManager
from mac_gui import MacWindowControls
from config_manager import ConfigManager
from hotkey_manager import HotkeyManager
from core_systems import AudioMonitorThread, EmotionThread, SUPPORTED_MODELS, ModelDownloaderThread, is_model_cached
from update_manager import UpdateChecker, CURRENT_VERSION
from settings_window import SettingsDialog
from ui_components import PillProgressBar, DownloadDialog, TutorialOverlay

class PNGTuberApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Configuración
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        self.current_version = CURRENT_VERSION

        # Estado
        self.current_emotion = "neutral"
        self.is_speaking = False
        self.is_muted = self.config.get("is_muted", False)
        self.mic_sensitivity = self.config.get("mic_sensitivity", 1.0)
        self.audio_threshold = self.config.get("audio_threshold", 0.02)
        
        # Visual
        self.bounce_enabled = self.config.get("bounce_enabled", True)
        self.bounce_amplitude = self.config.get("bounce_amplitude", 10)
        self.bounce_speed = self.config.get("bounce_speed", 0.3)
        self.bounce_phase = 0
        self.shadow_enabled = self.config.get("shadow_enabled", True)
        self.current_background = self.config.get("background_color", "transparent")
        self.is_flipped = False

        # Gestores
        self.profile_manager = AvatarProfileManager()
        profile_name = self.config.get("current_profile", "Default")
        self.profile_manager.set_profile(profile_name)

        self.init_ui()

        # Audio e IA
        saved_mic = self.config.get("microphone_index")
        self.audio_thread = AudioMonitorThread(device_index=saved_mic, threshold=self.audio_threshold, sensitivity=self.mic_sensitivity)
        self.audio_thread.volume_signal.connect(self.update_mouth)
        self.audio_thread.audio_data_signal.connect(self.handle_audio)
        self.audio_thread.start()

        self.emotion_thread = None
        QTimer.singleShot(100, self.check_initial_model)

        # Update Checker
        self.update_checker = None
        if self.config_manager.get("check_updates", True):
            self.update_checker = UpdateChecker()   
            self.update_checker.update_available.connect(self.on_update_found) 
            self.update_checker.start()

        # Animación
        self.bounce_timer = QTimer()
        self.bounce_timer.timeout.connect(self.animate_bounce)
        self.bounce_timer.start(30)
 
        # Hotkeys
        self.ai_mode = True
        self.hotkey_manager = HotkeyManager(self.config_manager)
        self.hotkey_manager.hotkey_triggered.connect(self.handle_hotkey)
        QTimer.singleShot(1000, self.hotkey_manager.start_listening)
        
        self.update_avatar()

        # Timer para animación de "Thinking" (AI Mode)
        self.ai_pulse_timer = QTimer()
        self.ai_pulse_timer.timeout.connect(self.animate_ai_pulse)
        self.ai_pulse_alpha = 0
        self.ai_pulse_direction = 1

        self.flip_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.flip_shortcut.activated.connect(self.toggle_flip)

        if not self.config.get("tutorial_completed", False):
            QTimer.singleShot(500, self.show_tutorial)

        # System Tray
        self.init_system_tray()
        self.will_quit = False
        self.tray_message_shown = False

    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(500, 500) # Un poco más grande para que quepa el dock

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(5, 5, 5, 5)

        # --- BARRA SUPERIOR (Mac Style + Update Badge) ---
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(13, 13, 13, 0) # Margen derecho agregado (13)
        
        # 1. Controles Mac (Izquierda)
        self.mac_controls = MacWindowControls(self)
        self.mac_controls.close_signal.connect(self.close)
        self.mac_controls.minimize_signal.connect(self.showMinimized)
        top_bar.addWidget(self.mac_controls)
        
        # 2. Espacio flexible
        top_bar.addStretch()

        # 3. Botón de Actualización (Derecha - Oculto por defecto)
        self.update_btn = QPushButton("⬇️  Update Available")
        self.update_btn.setVisible(False) # Oculto hasta que haya update
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn.setFixedHeight(24)
        
        # Estilo de "Píldora" translúcida oscura
        self.update_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 120);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 12px;
                padding-left: 10px;
                padding-right: 10px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 180);
                border: 1px solid rgba(255, 255, 255, 80);
            }
        """)
        # Al hacer clic, abrimos el diálogo de confirmación
        self.update_btn.clicked.connect(self.confirm_update)
        
        top_bar.addWidget(self.update_btn)
        
        self.layout.addLayout(top_bar)

        # --- AVATAR ---
        self.avatar_label = QLabel(self)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        self.avatar_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.layout.addWidget(self.avatar_label, 1)

        # --- DOCK INFERIOR ---
        
        # 1. Crear el contenedor físico para el fondo y bordes
        self.bottom_container = QWidget()
        self.bottom_container.setFixedHeight(60)
        self.bottom_container.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 220);
                border-radius: 30px;
                border: 1px solid rgba(255, 255, 255, 30);
            }
        """)
        
        # 2. Layout interno
        bottom_layout = QHBoxLayout(self.bottom_container)
        bottom_layout.setContentsMargins(15, 5, 15, 5)
        bottom_layout.setSpacing(10)

        # Estilo común de botones
        btn_style = """
            QPushButton { 
                background-color: rgba(255,255,255,200); 
                border-radius: 18px; 
                border: none;
                font-size: 16px;
            } 
            QPushButton:hover { background-color: rgba(255,255,255,255); }
            QPushButton:pressed { background-color: rgba(200,200,200,255); }
        """

        # --- GRUPO 1: UTILIDADES (Izquierda) ---
        
        # Mute
        self.mute_btn = QPushButton("🔊")
        self.mute_btn.setFixedSize(36, 36)
        self.mute_btn.setCheckable(True)
        self.mute_btn.setChecked(self.is_muted)
        self.mute_btn.setToolTip("Silenciar / Activar Micrófono")
        self.mute_btn.setStyleSheet(btn_style + "QPushButton:checked { background-color: #ff5555; color: white; }")
        self.mute_btn.clicked.connect(self.set_muted)
        bottom_layout.addWidget(self.mute_btn)

        # Flip
        self.flip_btn = QPushButton("🔄")
        self.flip_btn.setFixedSize(36, 36)
        self.flip_btn.setToolTip("Voltear Avatar (Espejo)")
        self.flip_btn.setStyleSheet(btn_style)
        self.flip_btn.clicked.connect(self.toggle_flip)
        bottom_layout.addWidget(self.flip_btn)

        # Configuración
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedSize(36, 36)
        self.settings_btn.setToolTip("Abrir Configuración")
        self.settings_btn.setStyleSheet(btn_style)
        self.settings_btn.clicked.connect(self.open_settings_window)
        bottom_layout.addWidget(self.settings_btn)

        # --- SEPARADOR ---
        line = QWidget()
        line.setFixedSize(1, 25)
        line.setStyleSheet("background-color: rgba(255,255,255,50);")
        bottom_layout.addWidget(line)

        # --- GRUPO 2: EMOCIONES (Derecha) ---
        # 1. Lista de Emociones PRINCIPALES (Siempre visibles)
        self.emotions_layout = QHBoxLayout() # Layout específico para botones
        self.emotions_layout.setSpacing(10)
        bottom_layout.addLayout(self.emotions_layout) # Añadirlo al layout principal del dock



        # 2. Botón de EXPANDIR (Flecha)
        self.expand_btn = QPushButton("›") # Usamos un carácter chevron para estilo
        self.expand_btn.setFixedSize(24, 36) # Un poco más estrecho
        self.expand_btn.setToolTip("Ver más emociones")
        # Estilo ligeramente diferente para distinguirlo (letra más grande y negrita)
        self.expand_btn.setStyleSheet("""
            QPushButton { 
                background-color: rgba(255,255,255,50); 
                border-radius: 12px; 
                border: none;
                color: white;
                font-size: 20px;
                font-weight: bold;
                padding-bottom: 3px;
            } 
            QPushButton:hover { background-color: rgba(255,255,255,100); }
        """)
        self.expand_btn.clicked.connect(self.toggle_emotions_menu)
        bottom_layout.addWidget(self.expand_btn)

        # 3. Lista de Emociones EXTRAS (Ocultas por defecto)
        secondary_buttons = [
            ("😠", "anger", "Enojado"),
            ("😨", "fear", "Miedo"),
            ("🤢", "disgust", "Asco")
        ]

        self.extra_emotion_btns = [] # Guardamos referencias para poder mostrarlos luego

        for icon, action, tooltip in secondary_buttons:
            btn = QPushButton(icon)
            btn.setFixedSize(36, 36)
            btn.setToolTip(tooltip)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(lambda _, a=action: self.handle_hotkey(a))
            
            # MAGIA AQUÍ: Los agregamos al layout pero los ocultamos
            bottom_layout.addWidget(btn)
            btn.setVisible(False) 
            self.extra_emotion_btns.append(btn)

        # --- GRUPO 3: VOLUMEN (Extremo Derecha) ---
        self.volume_bar = PillProgressBar()
        self.volume_bar.setFixedWidth(100)
        self.volume_bar._bg_color = QColor("#000000") # Fondo negro para combinar con el dock
        bottom_layout.addWidget(self.volume_bar)
        
        # Añadir dock al layout principal centrado
        center_dock_layout = QHBoxLayout()
        center_dock_layout.addStretch()
        center_dock_layout.addWidget(self.bottom_container)
        center_dock_layout.addStretch()
        
        self.layout.addLayout(center_dock_layout)
        self.layout.addSpacing(10)

        self.last_color_hex = "#00E64D"

        # Efectos (Sombra y Resize)
        self.shadow_effect = QGraphicsDropShadowEffect()
        self.shadow_effect.setBlurRadius(20)
        self.shadow_effect.setColor(QColor(0, 0, 0, 150))
        self.shadow_effect.setOffset(0, 5)
        self.set_shadow_enabled(self.shadow_enabled)

        self.sizegrip = QSizeGrip(self)
        self.sizegrip.setStyleSheet("QSizeGrip { background-color: transparent; width: 20px; height: 20px; }")

        # Gestor de Fondo
        self.bg_manager = BackgroundManager(self, self.profile_manager, self.config_manager)
        self.bg_manager.change_background(self.current_background)

    def update_dock_buttons(self):
        # 1. Limpiar botones anteriores
        while self.emotions_layout.count():
            item = self.emotions_layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()

        # 2. Inicializar lista de botones extra
        self.extra_emotion_btns = []

        # 3. Datos del modelo
        current_model_key = self.config_manager.get("ai_model", "spanish")
        supported_states = set(SUPPORTED_MODELS[current_model_key]["avatar_states"])

        # 4. Lista MAESTRA de emociones
        master_emotions = [
            ("neutral", "😐", "Neutral"),
            ("happy", "😄", "Feliz"),
            ("sad", "😢", "Triste"),
            ("angry", "😠", "Enojado"),
            ("fear", "😨", "Miedo"),
            ("disgust", "🤢", "Asco"), 
            ("surprise", "😲", "Sorpresa")   
            
        ]

        base_style = """
            QPushButton { 
                background-color: rgba(255,255,255,200); 
                border-radius: 18px; 
                border: none;
                font-size: 16px;
            } 
            QPushButton:hover { background-color: rgba(255,255,255,255); }
        """
        
        disabled_style = """
            QPushButton { 
                background-color: rgba(60,60,60,150); 
                border-radius: 18px; 
                border: none;
                font-size: 16px;
                color: rgba(255,255,255,50);
            } 
        """

        # 5. Botón Modo IA
        self.btn_ai = QPushButton("🤖")
        self.btn_ai.setFixedSize(36, 36)
        self.btn_ai.setToolTip("Modo Automático")
        self.btn_ai.setStyleSheet(base_style)
        self.btn_ai.clicked.connect(lambda: self.handle_hotkey("ai_mode"))
        self.emotions_layout.addWidget(self.btn_ai)

        # 6. Generar botones
        for state, icon, name in master_emotions:
            btn = QPushButton(icon)
            btn.setFixedSize(36, 36)
            
            # Usamos lambda con state=state
            btn.clicked.connect(lambda _, s=state: self.handle_hotkey(s))
            
            if state in supported_states:
                # Soportado -> Visible en barra principal
                btn.setEnabled(True)
                btn.setToolTip(name)
                btn.setStyleSheet(base_style)
                self.emotions_layout.addWidget(btn)
            else:
                # No soportado -> Oculto (Colapsado) y deshabilitado
                btn.setEnabled(False)
                btn.setToolTip(f"{name} (No disponible en {current_model_key})")
                btn.setStyleSheet(disabled_style)
                btn.setVisible(False) # Oculto por defecto
                self.emotions_layout.addWidget(btn)
                self.extra_emotion_btns.append(btn)
        
        # 7. Actualizar visibilidad del botón de expansión
        if hasattr(self, 'expand_btn'):
            self.expand_btn.setVisible(len(self.extra_emotion_btns) > 0)
            # Resetear estado del botón (flecha cerrada)
            self.expand_btn.setText("›")
            self.expand_btn.setToolTip("Ver emociones no disponibles")

    # --- LÓGICA DE FLIP ---
    def toggle_flip(self):
        self.is_flipped = not self.is_flipped
        self.update_avatar()

    # --- NUEVO: ABRIR AJUSTES ---
    def open_settings_window(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def toggle_emotions_menu(self):
        # Verificar estado actual basado en el primer botón extra
        if not self.extra_emotion_btns: return
        
        # Si están ocultos, los mostramos
        should_show = not self.extra_emotion_btns[0].isVisible()
        
        for btn in self.extra_emotion_btns:
            btn.setVisible(should_show)
            
        # Animación de resize suave
        current_width = self.width()
        target_width = current_width
        
        # Cambiar el icono de la flecha y definir ancho objetivo
        if should_show:
            self.expand_btn.setText("‹") # Flecha izquierda
            self.expand_btn.setToolTip("Menos emociones")
            if current_width < 600: 
                target_width = 600
        else:
            self.expand_btn.setText("›") # Flecha derecha
            self.expand_btn.setToolTip("Ver más emociones")
            if current_width > 500:
                target_width = 500
        
        if target_width != current_width:
            self.animation = QPropertyAnimation(self, b"size")
            self.animation.setDuration(300)
            self.animation.setStartValue(QSize(current_width, self.height()))
            self.animation.setEndValue(QSize(target_width, self.height()))
            self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.animation.start()

    # --- LÓGICA DE ANIMACIÓN ---
    def animate_bounce(self):
        if self.bounce_enabled and self.is_speaking:
            self.bounce_phase += self.bounce_speed
            offset = int(abs(np.sin(self.bounce_phase)) * self.bounce_amplitude)
            self.avatar_label.setContentsMargins(0, 0, 0, offset)
        elif self.bounce_phase != 0:
            self.bounce_phase = 0
            self.avatar_label.setContentsMargins(0, 0, 0, 0)

    def animate_ai_pulse(self):
        if not self.ai_mode or not hasattr(self, 'btn_ai'):
            self.ai_pulse_timer.stop()
            return

        # Animación de respiración (alpha de 0 a 100)
        self.ai_pulse_alpha += 5 * self.ai_pulse_direction
        
        if self.ai_pulse_alpha >= 100:
            self.ai_pulse_alpha = 100
            self.ai_pulse_direction = -1
        elif self.ai_pulse_alpha <= 0:
            self.ai_pulse_alpha = 0
            self.ai_pulse_direction = 1
            
        # Color azul/morado tipo Gemini
        glow_color = f"rgba(0, 200, 255, {self.ai_pulse_alpha})"
        border_color = f"rgba(255, 255, 255, {50 + self.ai_pulse_alpha})"
        
        style = f"""
            QPushButton {{ 
                background-color: rgba(255,255,255,200); 
                border-radius: 18px; 
                border: 2px solid {glow_color};
                background-color: {border_color};
                font-size: 16px;
            }} 
            QPushButton:hover {{ background-color: rgba(255,255,255,255); }}
        """
        self.btn_ai.setStyleSheet(style)

    def update_avatar(self):
        try:
            state = "open" if self.is_speaking else "closed"
            
            # Intentar obtener la ruta de la imagen
            path = None
            if hasattr(self, 'profile_manager'):
                path = self.profile_manager.get_image_path(self.current_emotion, state)
            
            pix = None
            if path and isinstance(path, str):
                pix = QPixmap(path)
            
            # --- PROTECCIÓN FINAL: GENERACIÓN EN MEMORIA ---
            # Si no hay imagen válida, generamos el aviso visual
            if not pix or pix.isNull():
                pix = QPixmap(200, 200)
                pix.fill(QColor("transparent"))
                painter = QPainter(pix)
                
                # Círculo rojo semitransparente de error
                painter.setBrush(QBrush(QColor(255, 50, 50, 150)))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(10, 10, 180, 180)
                
                # Signo de interrogación
                painter.setPen(QPen(QColor("white")))
                font = QFont("Arial", 40, QFont.Weight.Bold)
                painter.setFont(font)
                painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "?")
                painter.end()
            # -----------------------------------------------

            # Aplicar espejo si es necesario
            if self.is_flipped:
                pix = pix.transformed(QTransform().scale(-1, 1))

            # Mostrar en la etiqueta de forma segura
            w = self.avatar_label.width()
            h = self.avatar_label.height()
            if w > 0 and h > 0:
                self.avatar_label.setPixmap(pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                
        except Exception as e:
            print(f"⚠️ Error controlado en update_avatar: {e}")
            # No hacemos nada más, así la app sigue viva
   
    # --- SEÑALES ---
    def handle_audio(self, chunk):
        if not self.is_muted:
            # Enviar audio al hilo de emociones si está activo y NO es None
            if self.ai_mode and self.emotion_thread is not None:
                 self.emotion_thread.add_audio(chunk)

            try:
                rms = np.sqrt(np.mean(chunk**2))
                level = int(rms * 500) 
                level = min(100, max(0, level))
                
                self.volume_bar.setValue(level)
                
                new_color = "#00E64D" # Verde
                if level > 80: new_color = "#FF3333" # Rojo
                elif level > 60: new_color = "#FF8800" # Naranja
                elif level > 40: new_color = "#FFFF00" # Amarillo
                
                if new_color != self.last_color_hex:
                    self.volume_bar.set_color_hex(new_color)
                    self.last_color_hex = new_color

            except Exception: pass
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
            self.current_emotion = "neutral"
            self.update_avatar()
            self.ai_pulse_timer.start(50)
            print("🤖 Modo IA Activado")
        else:
            # Lógica dinámica para emociones
            
            # 1. Normalizar alias (Legacy hotkeys -> Estado avatar)
            alias_map = {
                "happiness": "happy",
                "sadness": "sad",
                "anger": "angry", 
                "neutral": "neutral",
                "fear": "fear",
                "disgust": "disgust",
                "surprise": "surprise"
            }
            target_state = alias_map.get(action, action)

            # 2. Verificar soporte en modelo actual
            current_model_key = self.config_manager.get("ai_model", "spanish")
            supported_states = SUPPORTED_MODELS[current_model_key]["avatar_states"]

            final_state = None
            
            # Permitir Override Manual: Si el usuario usa un hotkey, forzamos el estado aunque el modelo no lo soporte
            if target_state:
                final_state = target_state
                if target_state not in supported_states:
                     print(f"⚠️ Emoción '{target_state}' no soportada por '{current_model_key}', pero forzada por usuario.")

            # 4. Aplicar cambio
            if final_state:
                self.ai_mode = False # Desactivar IA al usar manual
                self.ai_pulse_timer.stop()
                if hasattr(self, 'btn_ai'):
                    self.btn_ai.setStyleSheet("""
                        QPushButton { 
                            background-color: rgba(255,255,255,200); 
                            border-radius: 18px; 
                            border: none;
                            font-size: 16px;
                        } 
                        QPushButton:hover { background-color: rgba(255,255,255,255); }
                    """)
                self.current_emotion = final_state
                self.update_avatar()
                print(f"🛑 Modo Manual: {final_state}")
            else:
                print(f"❌ Acción desconocida o no soportada: {action}")

    # --- SETTERS ---
    def set_microphone(self, index):
        print(f"🎤 Cambiando micrófono a ID: {index}")
        self.audio_thread.change_device(index)
        self.config_manager.set("microphone_index", index)

    def set_mic_sensitivity(self, value):
        self.mic_sensitivity = value
        self.audio_thread.set_sensitivity(value)
        self.config_manager.set("mic_sensitivity", value)

    def check_initial_model(self):
        """Verifica si el modelo configurado existe al arrancar"""
        current_model_key = self.config_manager.get("ai_model", "spanish")
        model_config = SUPPORTED_MODELS.get(current_model_key, SUPPORTED_MODELS["spanish"])
        
        # Si el modelo no está en caché, forzamos la descarga con ventana visual
        if not is_model_cached(model_config["id"]):
            print("🚀 Primera ejecución detectada: Descargando modelo...")
            self.start_model_download(current_model_key, model_config["name"], model_config["id"])
        else:
            # Si ya existe, iniciamos la IA normalmente
            self.start_emotion_system(current_model_key)

    def start_emotion_system(self, model_key):
        """Inicia el hilo de emociones una vez que estamos seguros que el modelo existe"""
        if self.emotion_thread is not None:
            self.emotion_thread.stop()
            
        self.emotion_thread = EmotionThread()
        # Configurar modelo antes de iniciar
        self.emotion_thread.set_model(model_key)
        self.emotion_thread.emotion_signal.connect(self.update_emotion)
        self.emotion_thread.start()
        print(f"✅ Sistema de emociones iniciado con: {model_key}")
        self.config_manager.set("ai_model", model_key)
        self.update_dock_buttons()
        # Iniciar animación visual si corresponde
        if self.ai_mode:
            self.ai_pulse_timer.start(50)

    def change_ai_model(self, model_key):
        """Método público llamado desde settings_window"""
        model_config = SUPPORTED_MODELS.get(model_key)
        if not model_config: return

        if is_model_cached(model_config["id"]):
            self.start_emotion_system(model_key)
        else:
            self.start_model_download(model_key, model_config["name"], model_config["id"])

    def start_model_download(self, model_key, model_name, model_id):
        # Crear y mostrar ventana de diálogo
        self.download_dialog = DownloadDialog(model_name, self)
        
        # Crear hilo de descarga
        self.downloader = ModelDownloaderThread(model_id)
        
        # Conectar señales
        self.downloader.finished_signal.connect(lambda success, msg: self.on_download_finished(success, msg, model_key))
        
        # Iniciar
        self.downloader.start()
        self.download_dialog.exec() # Esto bloquea la UI principal hasta que se cierre el diálogo

    def on_download_finished(self, success, msg, model_key):
        if hasattr(self, 'download_dialog'):
            self.download_dialog.close()
        
        if success:
            # Mensaje de éxito opcional (quizás no quieras mostrarlo en el primer arranque para ser más fluido)
            # QMessageBox.information(self, "Descarga Completada", "Modelo listo.")
            
            # Guardamos config
            self.config_manager.set("ai_model", model_key)
            
            # --- CAMBIO: INICIAR EL SISTEMA ---
            self.start_emotion_system(model_key)
            # ----------------------------------
        else:
            QMessageBox.critical(self, "Error Fatal", f"No se pudo descargar el modelo de IA.\nLa aplicación no detectará emociones.\nError: {msg}")

    def set_audio_threshold(self, value):
        self.audio_threshold = value
        self.audio_thread.set_threshold(value)
        self.config_manager.set("audio_threshold", value)

    def set_muted(self, muted):
        self.is_muted = muted
        self.mute_btn.setChecked(muted)
        # Actualizamos el icono o color si es necesario
        self.config_manager.set("is_muted", muted)
        if muted:
            self.is_speaking = False
            self.update_avatar()

    def set_bounce_enabled(self, enabled):
        self.bounce_enabled = enabled
        self.config_manager.set("bounce_enabled", enabled)
        if not enabled:
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
        if hasattr(self, 'tutorial') and self.tutorial and self.tutorial.isVisible():
             self.tutorial.setGeometry(rect)
        super().resizeEvent(event)

    def contextMenuEvent(self, event):
        # Mantenemos el clic derecho como acceso alternativo
        self.bg_manager.show_context_menu(event.pos())

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(100, lambda: self.resize(self.width() + 1, self.height()))
        QTimer.singleShot(200, lambda: self.resize(self.width() - 1, self.height()))

        QTimer.singleShot(200, lambda: self.resize(self.width() - 1, self.height()))

    def closeEvent(self, event):
        if self.will_quit:
             self.stop_threads()
             event.accept()
        elif self.tray_icon.isVisible():
            if not self.tray_message_shown:
                QMessageBox.information(self, "PNGTuber", 
                                        "La aplicación seguirá ejecutándose en la bandeja del sistema.\nPara salir completamente, usa el menú del icono o 'Quit' en el menú de la aplicación.")
                self.tray_message_shown = True
            
            self.hide()
            event.ignore()
        else:
            self.stop_threads()
            event.accept()

    def stop_threads(self):
        self.hotkey_manager.stop_listening()
        self.audio_thread.stop()
        if self.emotion_thread:
            self.emotion_thread.stop()
        if self.update_checker: # Si existe
             self.update_checker.terminate()
    
    def quit_application(self):
        self.will_quit = True
        self.stop_threads()
        QApplication.quit()
    
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

    def init_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        # Icono por defecto (usamos un emoji o lo que sea, idealmente debería ser un .ico/.png)
        # Como no tenemos un icono fijo, usaremos un pixmap generado o el avatar actual si es posible
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QBrush(QColor("#00E64D"))) # Verde PNGTuber
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 32, 32)
        painter.setPen(QPen(QColor("white")))
        font = QFont("Arial", 20, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "P")
        painter.end()
        
        self.tray_icon.setIcon(QIcon(pixmap))
        
        # Menú Contextual
        tray_menu = QMenu()
        
        show_action = QAction("Mostrar / Ocultar", self)
        show_action.triggered.connect(self.toggle_window_visibility)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        mute_action = QAction("Silenciar Micrófono", self)
        mute_action.setCheckable(True)
        mute_action.setChecked(self.is_muted)
        mute_action.triggered.connect(lambda c: self.set_muted(c))
        # Sincronizar estado visual del menú con el botón
        self.mute_btn.clicked.connect(lambda: mute_action.setChecked(self.is_muted))
        tray_menu.addAction(mute_action)

        ai_action = QAction("Modo IA activado", self)
        ai_action.setCheckable(True)
        ai_action.setChecked(self.ai_mode)
        ai_action.triggered.connect(self.toggle_ai_mode_tray)
        # Sincronizar
        # Nota: Sincronizar bi-direccionalmente es complejo sin señales dedicadas, 
        # pero para este caso simple lo dejamos así.
        tray_menu.addAction(ai_action)

        tray_menu.addSeparator()
        
        quit_action = QAction("Salir (Quit)", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def toggle_window_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.activateWindow()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_window_visibility()

    def toggle_ai_mode_tray(self, checked):
        if checked:
            self.handle_hotkey("ai_mode")
        else:
             # Modo manual 'neutral' al desactivar
             self.handle_hotkey("neutral")

    # --- SISTEMA DE ACTUALIZACIONES ---
    def on_update_found(self, url, version):
        """Se llama cuando el hilo detecta una versión nueva"""
        self.pending_update_url = url
        # Actualizamos el texto del botón y lo mostramos
        self.update_btn.setText(f"⬇️  Actualización v{version} Disponible")
        self.update_btn.setVisible(True)
        print(f"Update detected: {version}")
        
        # Notificación en Tray
        if self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "Actualización Disponible",
                f"La versión {version} está lista para descargar.",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )

    def confirm_update(self):
        """Se llama al hacer clic en el botón de la barra superior"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Actualización Disponible")
        msg.setText("¡Nueva versión disponible!")
        msg.setInformativeText("¿Quieres ir a la página de descarga ahora?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            if hasattr(self, 'pending_update_url'):
                QDesktopServices.openUrl(QUrl(self.pending_update_url))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Importante para que no se cierre al cerrar la ventana si el tray está activo
    app.setQuitOnLastWindowClosed(False) 
    window = PNGTuberApp()
    window.show()
    sys.exit(app.exec())
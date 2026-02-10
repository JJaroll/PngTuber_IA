import os
import sys
import platform
import numpy as np
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QSlider, QCheckBox, QTabWidget, 
                             QWidget, QPushButton, QGroupBox, QFormLayout, 
                             QRadioButton, QButtonGroup, QScrollArea, QGridLayout, QFrame,
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QMenu, QInputDialog, QMessageBox, QColorDialog)
from PyQt6.QtGui import QAction, QFont, QDesktopServices
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QUrl
from PyQt6.QtGui import QPixmap, QIcon, QColor, QPainter, QPainterPath

from ui_components import PillProgressBar
from hotkey_gui import HotkeyRecorderDialog

# --- WIDGET PERSONALIZADO: TARJETA DE AVATAR (Sin cambios) ---
class AvatarCard(QFrame):
    clicked = pyqtSignal(str) 
    rename_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self, name, image_path, is_active, parent=None):
        super().__init__(parent)
        self.name = name
        self.setFixedSize(140, 180) 
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        border_color = "#00E64D" if is_active else "#444"
        bg_color = "#3a3a3a" if is_active else "#333"
        border_width = "2px" if is_active else "1px"
        
        self.setStyleSheet(f"""
            AvatarCard {{
                background-color: {bg_color};
                border: {border_width} solid {border_color};
                border-radius: 15px;
            }}
            AvatarCard:hover {{
                background-color: #444;
                border: 2px solid #666;
            }}
            QLabel {{ border: none; background: transparent; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.img_lbl = QLabel()
        self.img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        pix = QPixmap(image_path)
        if not pix.isNull():
            pix = pix.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.img_lbl.setPixmap(pix)
        else:
            self.img_lbl.setText("❓")
            self.img_lbl.setStyleSheet("font-size: 40px;")
            
        layout.addWidget(self.img_lbl)

        self.name_lbl = QLabel(name)
        self.name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_lbl.setStyleSheet("font-weight: bold; color: white; font-size: 13px;")
        layout.addWidget(self.name_lbl)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.name)
        super().mousePressEvent(event)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #333; color: white; border: 1px solid #555; }
            QMenu::item { padding: 5px 20px; }
            QMenu::item:selected { background-color: #007ACC; }
        """)
        
        rename_action = QAction("✏️ Cambiar Nombre", self)
        rename_action.triggered.connect(lambda: self.rename_requested.emit(self.name))
        menu.addAction(rename_action)

        if self.name != "Default":
            menu.addSeparator()
            delete_action = QAction("🗑️ Eliminar Skin", self)
            delete_action.triggered.connect(lambda: self.delete_requested.emit(self.name))
            menu.addAction(delete_action)
        
        menu.exec(self.mapToGlobal(pos))


# --- VENTANA PRINCIPAL DE AJUSTES ---
class SettingsDialog(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.bg_manager = main_window.bg_manager
        
        self.setWindowTitle("Configuración - PNGTuber IA")
        self.resize(700, 600)
        
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: white; }
            QTabWidget::pane { border: 1px solid #333; background: #252525; border-radius: 8px; }
            QTabBar::tab { background: #333; color: #aaa; padding: 10px 15px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 4px; font-weight: bold;}
            QTabBar::tab:selected { background: #252525; color: white; border-bottom: 2px solid #007ACC; }
            QLabel { color: #ddd; font-size: 13px; }
            QGroupBox { border: 1px solid #444; border-radius: 8px; margin-top: 20px; font-weight: bold; color: #eee; padding-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QPushButton { background-color: #3a3a3a; color: white; border-radius: 6px; padding: 8px; font-weight: bold; border: 1px solid #555; }
            QPushButton:hover { background-color: #4a4a4a; border-color: #777; }
            QSlider::groove:horizontal { border: 1px solid #444; height: 6px; background: #222; border-radius: 3px; }
            QSlider::handle:horizontal { background: #007ACC; width: 16px; margin: -5px 0; border-radius: 8px; }
            QComboBox { background: #333; color: white; border: 1px solid #444; padding: 6px; border-radius: 4px; }
            QScrollArea { border: none; background: transparent; }
            QTableWidget { background-color: #2b2b2b; border: 1px solid #444; border-radius: 6px; gridline-color: #383838; }
            QHeaderView::section { background-color: #333; color: #ccc; padding: 5px; border: none; font-weight: bold; }
            QTableWidget::item { padding: 5px; }
            QLineEdit { background-color: #333; color: white; border: 1px solid #555; padding: 4px; }
        """)

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # --- AÑADIR PESTAÑAS ---
        self.tabs.addTab(self.create_audio_tab(), "🎙️ Audio")
        self.tabs.addTab(self.create_visual_tab(), "🎨 Apariencia")
        self.tabs.addTab(self.create_avatar_tab(), "👕 Avatar")
        self.tabs.addTab(self.create_hotkeys_tab(), "⌨️ Atajos")
        self.tabs.addTab(self.create_system_tab(), "💻 Sistema")
        self.tabs.addTab(self.create_about_tab(), "ℹ️ Sobre")

        close_btn = QPushButton("Cerrar")
        close_btn.setStyleSheet("background-color: #007ACC; border: none;")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        self.last_color_hex = "#00E64D"

    def showEvent(self, event):
        self.main_window.audio_thread.audio_data_signal.connect(self.update_audio_bar)
        super().showEvent(event)

    def closeEvent(self, event):
        try:
            self.main_window.audio_thread.audio_data_signal.disconnect(self.update_audio_bar)
        except: pass
        super().closeEvent(event)

    def update_audio_bar(self, chunk):
        try:
            rms = np.sqrt(np.mean(chunk**2))
            level = int(rms * 500) 
            level = min(100, max(0, level))
            
            if hasattr(self, 'audio_test_bar'):
                self.audio_test_bar.setValue(level)
                new_color = "#00E64D"
                if level > 80: new_color = "#FF3333"
                elif level > 60: new_color = "#FF8800"
                elif level > 40: new_color = "#FFFF00"
                
                if new_color != self.last_color_hex:
                    self.audio_test_bar.set_color_hex(new_color)
                    self.last_color_hex = new_color
        except: pass

    # ==========================================
    # 🆕 PESTAÑA: AUDIO (CORREGIDA ALINEACIÓN)
    # ==========================================
    def create_audio_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.mic_combo = QComboBox()
        devices = self.main_window.audio_thread.list_devices()
        current_idx = self.main_window.audio_thread.device_index
        idx_map = {}
        for i, (dev_idx, name) in enumerate(devices):
            self.mic_combo.addItem(f"{name[:35]}...", dev_idx)
            idx_map[dev_idx] = i 
        if current_idx in idx_map:
            self.mic_combo.setCurrentIndex(idx_map[current_idx])
        self.mic_combo.currentIndexChanged.connect(self.on_mic_changed)
        layout.addRow("Dispositivo:", self.mic_combo)

        self.sens_slider = QSlider(Qt.Orientation.Horizontal)
        self.sens_slider.setRange(1, 50) 
        self.sens_slider.setValue(int(self.main_window.mic_sensitivity * 10))
        self.sens_label = QLabel(f"{self.main_window.mic_sensitivity:.1f}")
        self.sens_slider.valueChanged.connect(lambda v: self.on_sensitivity(v))
        sens_layout = QHBoxLayout()
        sens_layout.addWidget(self.sens_slider)
        sens_layout.addWidget(self.sens_label)
        layout.addRow("Sensibilidad:", sens_layout)

        self.thres_slider = QSlider(Qt.Orientation.Horizontal)
        self.thres_slider.setRange(1, 100) 
        self.thres_slider.setValue(int(self.main_window.audio_threshold * 1000))
        self.thres_label = QLabel(f"{self.main_window.audio_threshold:.3f}")
        self.thres_slider.valueChanged.connect(lambda v: self.on_threshold(v))
        thres_layout = QHBoxLayout()
        thres_layout.addWidget(self.thres_slider)
        thres_layout.addWidget(self.thres_label)
        layout.addRow("Umbral:", thres_layout)
        
        layout.addRow(QLabel(" "))
        
        # --- CORRECCIÓN ---
        lbl_test = QLabel("Prueba de Audio:")
        # 1. ELIMINAMOS 'margin-top: 10px'
        lbl_test.setStyleSheet("font-weight: bold;") 
        
        self.audio_test_bar = PillProgressBar()
        
        # 2. USAMOS UN CONTENEDOR PARA CENTRAR VERTICALMENTE
        bar_container = QWidget()
        bar_layout = QHBoxLayout(bar_container)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter) # Esto hace la magia
        bar_layout.addWidget(self.audio_test_bar)
        
        layout.addRow(lbl_test, bar_container)
        
        return tab

    # ==========================================
    # 🆕 PESTAÑA: DETALLES DEL SISTEMA
    # ==========================================
    def create_system_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # 1. Información de Ubicación
        path_group = QGroupBox("Ubicación del Proyecto")
        path_layout = QVBoxLayout()
        current_path = os.getcwd()
        lbl_path = QLabel(f"{current_path}")
        lbl_path.setWordWrap(True)
        lbl_path.setStyleSheet("color: #aaa; font-family: monospace;")
        path_layout.addWidget(lbl_path)
        
        btn_open_folder = QPushButton("Abrir Carpeta")
        btn_open_folder.setFixedSize(120, 30)
        btn_open_folder.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(current_path)))
        path_layout.addWidget(btn_open_folder)
        path_group.setLayout(path_layout)
        layout.addWidget(path_group)

        # 2. Peso de la Aplicación
        size_group = QGroupBox("Almacenamiento")
        size_layout = QFormLayout()
        
        # Calcular peso (excluyendo venv y .git para ser realistas)
        total_size = 0
        file_count = 0
        exclude_dirs = {'venv', '.git', '__pycache__', '.idea', '.vscode'}
        
        for dirpath, dirnames, filenames in os.walk(current_path):
            dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
                    file_count += 1
        
        size_str = f"{total_size / (1024*1024):.2f} MB"
        
        size_layout.addRow("Peso Total (aprox):", QLabel(size_str))
        size_layout.addRow("Archivos:", QLabel(str(file_count)))
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)

        # 3. Detalles Técnicos
        tech_group = QGroupBox("Entorno de Ejecución")
        tech_layout = QFormLayout()
        
        tech_layout.addRow("Sistema Operativo:", QLabel(f"{platform.system()} {platform.release()}"))
        tech_layout.addRow("Arquitectura:", QLabel(platform.machine()))
        tech_layout.addRow("Versión de Python:", QLabel(platform.python_version()))
        
        tech_group.setLayout(tech_layout)
        layout.addWidget(tech_group)

        layout.addStretch()
        return tab

    # ==========================================
    # 🆕 PESTAÑA: ABOUT (SOBRE)
    # ==========================================
    def create_about_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(15)

        # Logo / Emoji Grande
        lbl_icon = QLabel("🎙️")
        lbl_icon.setStyleSheet("font-size: 64px;")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_icon)

        # Título
        lbl_title = QLabel("AI PNGTuber")
        lbl_title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        # Versión
        lbl_ver = QLabel("Versión 1.1.0")
        lbl_ver.setStyleSheet("color: #888; font-size: 14px;")
        lbl_ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_ver)

        # Descripción
        desc_text = (
            "Un avatar virtual inteligente que reacciona a tu voz y emociones "
            "en tiempo real utilizando Inteligencia Artificial."
        )
        lbl_desc = QLabel(desc_text)
        lbl_desc.setWordWrap(True)
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setStyleSheet("color: #ccc; margin: 10px 0;")
        layout.addWidget(lbl_desc)

        # Línea separadora
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #444;")
        layout.addWidget(line)

        # Créditos
        lbl_credits = QLabel("Desarrollado por <b>JJaroll</b>")
        lbl_credits.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_credits)

        # Tecnologías
        lbl_tech = QLabel("Powered by Python, PyQt6 & PyTorch")
        lbl_tech.setStyleSheet("color: #666; font-size: 11px;")
        lbl_tech.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_tech)

        # Licencia
        lbl_license = QLabel("Distribuido bajo Licencia MIT")
        lbl_license.setStyleSheet("color: #555; font-size: 11px; font-style: italic;")
        lbl_license.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_license)

        layout.addSpacing(20)

        # Botón GitHub
        btn_github = QPushButton("  Ver en GitHub")
        # Usamos un estilo un poco más llamativo para el CTA
        btn_github.setStyleSheet("""
            QPushButton {
                background-color: #24292e;
                color: white;
                border: 1px solid #444;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2f363d; }
        """)
        btn_github.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/JJaroll/PngTuber_IA")))
        
        # Botón Reportar Bug
        btn_bug = QPushButton("🐛 Reportar un Problema")
        btn_bug.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #aaa;
                border: none;
                text-decoration: underline;
            }
            QPushButton:hover { color: #fff; }
        """)
        btn_bug.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_bug.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/JJaroll/PngTuber_IA/issues")))

        layout.addWidget(btn_github)
        layout.addWidget(btn_bug)

        layout.addStretch()
        return tab

    # ==========================================
    # PESTAÑAS ANTERIORES (CONSERVADAS)
    # ==========================================
    def create_visual_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # --- GRUPO FONDO ---
        bg_group = QGroupBox("Color de Fondo")
        bg_layout = QVBoxLayout()
        
        self.bg_radios = QButtonGroup(self)
        
        opts = [
            ("Transparente", "transparent"),
            ("Verde (Chroma)", "#07FD01"),
            ("Azul (Chroma)", "#0000FE"),
            ("Semitransparente (Oscuro)", "rgba(0, 0, 0, 100)")
        ]
        
        grid_opts = QGridLayout()
        row = 0
        col = 0
        
        for name, val in opts:
            rb = QRadioButton(name)
            self.bg_radios.addButton(rb)
            
            if self.main_window.current_background == val: 
                rb.setChecked(True)
                
            rb.toggled.connect(lambda checked, v=val: self.bg_manager.change_background(v) if checked else None)
            grid_opts.addWidget(rb, row, col)
            
            col += 1
            if col > 1:
                col = 0
                row += 1
        
        bg_layout.addLayout(grid_opts)

        # Opción Personalizada
        custom_layout = QHBoxLayout()
        self.rb_custom = QRadioButton("Seleccionar Color:")
        self.bg_radios.addButton(self.rb_custom)
        
        current_bg = self.main_window.current_background
        is_standard = any(val == current_bg for _, val in opts)
        if not is_standard:
            self.rb_custom.setChecked(True)

        self.btn_pick_color = QPushButton("Elegir Color")
        self.btn_pick_color.setFixedSize(100, 35)
        self.btn_pick_color.setStyleSheet("background-color: #444; border: 1px solid #666;")
        self.btn_pick_color.clicked.connect(self.open_color_picker)
        
        self.rb_custom.toggled.connect(lambda checked: self.btn_pick_color.setEnabled(True))

        custom_layout.addWidget(self.rb_custom)
        custom_layout.addWidget(self.btn_pick_color)
        custom_layout.addStretch()
        
        bg_layout.addLayout(custom_layout)
        bg_group.setLayout(bg_layout)
        layout.addWidget(bg_group)

        # --- RESTO ---
        self.shadow_cb = QCheckBox("Activar Sombra Suave")
        self.shadow_cb.setChecked(self.main_window.shadow_enabled)
        self.shadow_cb.toggled.connect(self.main_window.set_shadow_enabled)
        layout.addWidget(self.shadow_cb)

        bounce_group = QGroupBox("Animación de Rebote")
        bounce_layout = QFormLayout()
        self.bounce_cb = QCheckBox("Activar Rebote")
        self.bounce_cb.setChecked(self.main_window.bounce_enabled)
        self.bounce_cb.toggled.connect(self.main_window.set_bounce_enabled)
        bounce_layout.addRow(self.bounce_cb)
        self.amp_slider = QSlider(Qt.Orientation.Horizontal)
        self.amp_slider.setRange(0, 50)
        self.amp_slider.setValue(self.main_window.bounce_amplitude)
        self.amp_slider.valueChanged.connect(self.main_window.set_bounce_amplitude)
        bounce_layout.addRow("Fuerza:", self.amp_slider)
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 20)
        self.speed_slider.setValue(int(self.main_window.bounce_speed * 10))
        self.speed_slider.valueChanged.connect(lambda v: self.main_window.set_bounce_speed(v/10))
        bounce_layout.addRow("Velocidad:", self.speed_slider)
        bounce_group.setLayout(bounce_layout)
        layout.addWidget(bounce_group)
        
        layout.addStretch()
        return tab

    def open_color_picker(self):
        color = QColorDialog.getColor(initial=QColor(self.main_window.current_background), parent=self, title="Seleccionar Color de Fondo")
        if color.isValid():
            rgba = f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"
            self.bg_manager.change_background(rgba)
            self.rb_custom.setChecked(True)

    def create_avatar_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("Gestión de Avatares")
        lbl.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(lbl)
        
        hint = QLabel("💡 Tip: Haz clic derecho en un avatar para cambiarle el nombre o eliminarlo.")
        hint.setStyleSheet("color: #888; font-size: 11px; margin-bottom: 5px;")
        layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: transparent;")
        
        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background-color: transparent;")
        self.avatar_grid = QGridLayout(self.grid_container)
        self.avatar_grid.setSpacing(15)
        self.avatar_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        scroll.setWidget(self.grid_container)
        layout.addWidget(scroll)

        layout.addSpacing(10)

        self.btn_create = QPushButton("+  Crear Nuevo Skin")
        self.btn_create.setMinimumHeight(45)
        self.btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_create_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px dashed #666;
                border-radius: 10px;
                font-size: 14px;
                color: #aaa;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                border: 1px dashed white;
            }
        """
        self.btn_create.setStyleSheet(self.btn_create_style)
        self.btn_create.clicked.connect(self.open_creator_refresh)
        layout.addWidget(self.btn_create)

        h_layout = QHBoxLayout()
        btn_import = QPushButton("📥 Importar")
        btn_import.clicked.connect(self.import_refresh)
        btn_export = QPushButton("📤 Exportar")
        btn_export.clicked.connect(self.bg_manager.export_current_skin)
        
        h_layout.addWidget(btn_import)
        h_layout.addWidget(btn_export)
        layout.addLayout(h_layout)

        self.refresh_avatar_grid()
        return tab

    def refresh_avatar_grid(self):
        for i in reversed(range(self.avatar_grid.count())): 
            self.avatar_grid.itemAt(i).widget().setParent(None)

        self.main_window.profile_manager.scan_profiles()
        profiles = self.main_window.profile_manager.profiles
        current_profile = self.main_window.profile_manager.current_profile
        root_folder = self.main_window.profile_manager.root_folder

        count = len(profiles)
        limit = 12
        if count >= limit:
            self.btn_create.setEnabled(False)
            self.btn_create.setText(f"⚠️ Límite de Skins Alcanzado ({count}/{limit})")
            self.btn_create.setStyleSheet("""
                QPushButton {
                    background-color: rgba(50, 0, 0, 0.3);
                    border: 1px solid #500;
                    border-radius: 10px;
                    font-size: 14px;
                    color: #777;
                }
            """)
            self.btn_create.setToolTip("Has alcanzado el máximo de 12 skins. Elimina carpetas en 'avatars/' para crear más.")
        else:
            self.btn_create.setEnabled(True)
            self.btn_create.setText(f"+  Crear Nuevo Skin ({count}/{limit})")
            self.btn_create.setStyleSheet(self.btn_create_style)
            self.btn_create.setToolTip("")

        col_count = 3
        row = 0
        col = 0

        for profile in profiles:
            image_path = os.path.join(root_folder, profile, "neutral_open.PNG")
            if not os.path.exists(image_path):
                image_path = os.path.join(root_folder, profile, "neutral_closed.PNG")
            
            is_active = (profile == current_profile)
            
            card = AvatarCard(profile, image_path, is_active)
            card.clicked.connect(self.on_avatar_selected)
            card.rename_requested.connect(self.rename_avatar)
            card.delete_requested.connect(self.delete_avatar)
            
            self.avatar_grid.addWidget(card, row, col)
            
            col += 1
            if col >= col_count:
                col = 0
                row += 1

    def on_avatar_selected(self, profile_name):
        self.bg_manager.change_profile(profile_name)
        self.refresh_avatar_grid()
    
    def rename_avatar(self, old_name):
        new_name, ok = QInputDialog.getText(self, "Renombrar Skin", 
                                          f"Nuevo nombre para '{old_name}':",
                                          text=old_name)
        
        if ok and new_name:
            new_name = new_name.strip()
            if not new_name: return
            if new_name == old_name: return

            success, msg = self.main_window.profile_manager.rename_profile(old_name, new_name)
            
            if success:
                if self.main_window.profile_manager.current_profile == new_name:
                     self.main_window.config_manager.set("current_profile", new_name)
                
                self.refresh_avatar_grid()
                QMessageBox.information(self, "Éxito", f"Renombrado a '{new_name}'")
            else:
                QMessageBox.warning(self, "Error", msg)

    def delete_avatar(self, profile_name):
        reply = QMessageBox.question(self, "Eliminar Skin", 
            f"¿Estás seguro de que deseas eliminar permanentemente el skin '{profile_name}'?\n\nEsta acción NO se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = self.main_window.profile_manager.delete_profile(profile_name)
            
            if success:
                if self.main_window.config_manager.get("current_profile") == profile_name:
                     self.main_window.config_manager.set("current_profile", "Default")
                
                self.refresh_avatar_grid()
                QMessageBox.information(self, "Eliminado", f"El skin '{profile_name}' ha sido eliminado.")
            else:
                QMessageBox.warning(self, "Error", msg)

    def open_creator_refresh(self):
        self.bg_manager.open_creator()
        self.refresh_avatar_grid()

    def import_refresh(self):
        self.bg_manager.import_skin_dialog()
        self.refresh_avatar_grid()

    def create_audio_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.mic_combo = QComboBox()
        devices = self.main_window.audio_thread.list_devices()
        current_idx = self.main_window.audio_thread.device_index
        idx_map = {}
        for i, (dev_idx, name) in enumerate(devices):
            self.mic_combo.addItem(f"{name[:35]}...", dev_idx)
            idx_map[dev_idx] = i 
        if current_idx in idx_map:
            self.mic_combo.setCurrentIndex(idx_map[current_idx])
        self.mic_combo.currentIndexChanged.connect(self.on_mic_changed)
        layout.addRow("Dispositivo:", self.mic_combo)

        self.sens_slider = QSlider(Qt.Orientation.Horizontal)
        self.sens_slider.setRange(1, 50) 
        self.sens_slider.setValue(int(self.main_window.mic_sensitivity * 10))
        self.sens_label = QLabel(f"{self.main_window.mic_sensitivity:.1f}")
        self.sens_slider.valueChanged.connect(lambda v: self.on_sensitivity(v))
        sens_layout = QHBoxLayout()
        sens_layout.addWidget(self.sens_slider)
        sens_layout.addWidget(self.sens_label)
        layout.addRow("Sensibilidad:", sens_layout)

        self.thres_slider = QSlider(Qt.Orientation.Horizontal)
        self.thres_slider.setRange(1, 100) 
        self.thres_slider.setValue(int(self.main_window.audio_threshold * 1000))
        self.thres_label = QLabel(f"{self.main_window.audio_threshold:.3f}")
        self.thres_slider.valueChanged.connect(lambda v: self.on_threshold(v))
        thres_layout = QHBoxLayout()
        thres_layout.addWidget(self.thres_slider)
        thres_layout.addWidget(self.thres_label)
        layout.addRow("Umbral:", thres_layout)
        
        layout.addRow(QLabel(" "))
        lbl_test = QLabel("Prueba de Audio:")
        lbl_test.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.audio_test_bar = PillProgressBar()
        layout.addRow(lbl_test, self.audio_test_bar)
        return tab

    def create_hotkeys_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)

        lbl = QLabel("Configura las teclas para activar emociones rápidamente.")
        lbl.setStyleSheet("color: #aaa; margin-bottom: 10px;")
        layout.addWidget(lbl)

        self.hotkey_table = QTableWidget()
        self.hotkey_table.setColumnCount(3)
        self.hotkey_table.setHorizontalHeaderLabels(["Acción", "Tecla Actual", ""])
        
        self.hotkey_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.hotkey_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.hotkey_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed) 
        self.hotkey_table.setColumnWidth(2, 130) 
        
        self.hotkey_table.verticalHeader().setDefaultSectionSize(45) 
        self.hotkey_table.verticalHeader().setVisible(False)
        self.hotkey_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.hotkey_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        layout.addWidget(self.hotkey_table)

        self.refresh_hotkey_list()
        return tab

    def refresh_hotkey_list(self):
        self.hotkey_table.setRowCount(0)
        hotkeys = self.main_window.config_manager.get("hotkeys", {})
        
        friendly_names = {
            "mute_toggle": "🔇 Silenciar / Activar Micrófono",
            "ai_mode": "🤖 Activar Modo Automático (IA)",
            "neutral": "😐 Emoción: Neutral",
            "disgust": "🤢 Emoción: Asco",
            "fear": "😨 Emoción: Miedo",
            "happiness": "😄 Emoción: Felicidad",
            "sadness": "😢 Emoción: Tristeza",
            "anger": "😡 Emoción: Enojo"
        }
        
        order = ["mute_toggle", "ai_mode", "neutral", "happiness", "sadness", "anger", "fear", "disgust"]
        
        row = 0
        for action in order:
            if action in hotkeys:
                self.add_hotkey_row(row, action, friendly_names.get(action, action), hotkeys[action])
                row += 1
                
        for action, key in hotkeys.items():
            if action not in order:
                self.add_hotkey_row(row, action, friendly_names.get(action, action), key)
                row += 1

    def add_hotkey_row(self, row, action, name, key_str):
        self.hotkey_table.insertRow(row)
        
        item_name = QTableWidgetItem(name)
        item_name.setFlags(Qt.ItemFlag.ItemIsEnabled) 
        self.hotkey_table.setItem(row, 0, item_name)
        
        display_key = str(key_str).upper() if key_str else "---"
        item_key = QTableWidgetItem(display_key)
        item_key.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_key.setFlags(Qt.ItemFlag.ItemIsEnabled)
        
        if key_str:
            item_key.setForeground(QColor("#00E64D")) 
            item_key.setFont(self.get_bold_font())
        else:
            item_key.setForeground(QColor("#777"))
            
        self.hotkey_table.setItem(row, 1, item_key)

        btn = QPushButton("✏️ Cambiar")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(100, 30)
        btn.setStyleSheet("""
            QPushButton { 
                background-color: #3a3a3a; 
                border: 1px solid #555; 
                border-radius: 4px; 
                font-size: 12px;
                color: #ddd;
            }
            QPushButton:hover { 
                background-color: #4a4a4a; 
                border-color: #777; 
                color: white;
            }
        """)
        btn.clicked.connect(lambda _, a=action: self.record_key(a))
        
        container = QWidget()
        l = QHBoxLayout(container)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(btn)
        self.hotkey_table.setCellWidget(row, 2, container)

    def record_key(self, action):
        dialog = HotkeyRecorderDialog(self)
        if dialog.exec():
            new_key = dialog.key_result
            if new_key:
                self.main_window.hotkey_manager.update_hotkey(action, new_key)
                self.refresh_hotkey_list()

    def get_bold_font(self):
        f = self.font()
        f.setBold(True)
        return f

    def on_mic_changed(self, index):
        dev_index = self.mic_combo.currentData()
        self.main_window.set_microphone(dev_index)

    def on_sensitivity(self, val):
        real_val = val / 10.0
        self.sens_label.setText(f"{real_val:.1f}")
        self.main_window.set_mic_sensitivity(real_val)

    def on_threshold(self, val):
        real_val = val / 1000.0
        self.thres_label.setText(f"{real_val:.3f}")
        self.main_window.set_audio_threshold(real_val)
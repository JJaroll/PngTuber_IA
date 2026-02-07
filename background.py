import os
import zipfile
import json
import shutil
from PyQt6.QtWidgets import QMenu, QWidget, QVBoxLayout, QLabel, QSlider, QWidgetAction, QFileDialog, QMessageBox
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
from profile_creator import ProfileCreatorDialog

class BackgroundManager:
    def __init__(self, main_window, profile_manager, config_manager): 
        self.main_window = main_window
        self.profile_manager = profile_manager
        self.config_manager = config_manager  # <--- Guardarlo
        self.central_widget = main_window.central_widget

    def show_context_menu(self, position):
        menu = QMenu(self.main_window)
        
        # --- SUBMENÚ: Audio ---
        # 1. Mute
        mute_action = QAction("🔇 Silenciar / Mute", self.main_window)
        mute_action.setCheckable(True)
        mute_action.setChecked(self.main_window.is_muted)
        mute_action.triggered.connect(lambda checked: self.main_window.set_muted(checked))
        menu.addAction(mute_action)

        # 2. Micrófono
        mic_menu = menu.addMenu("🎤 Micrófono")
        
        # Obtener lista de dispositivos desde el hilo de audio
        devices = self.main_window.audio_thread.list_devices()
        current_idx = self.main_window.audio_thread.device_index
        
        for idx, name in devices:
            # Truncar nombres muy largos
            display_name = (name[:30] + '..') if len(name) > 30 else name
            a = QAction(display_name, self.main_window)
            a.setCheckable(True)
            if idx == current_idx:
                a.setChecked(True)
            elif current_idx is None and idx ==  self.main_window.audio_thread.p.get_default_input_device_info()['index']:
                 # Si no seleccionamos nada explícitamente, marcar el default (aproximado)
                 a.setChecked(True)

            a.triggered.connect(lambda _, i=idx: self.main_window.set_microphone(i))
            mic_menu.addAction(a)

        menu.addSeparator()

        # --- SUBMENÚ: Fondo ---
        bg_menu = menu.addMenu("🎨 Fondo / Background")
        actions = [("Transparente", "transparent"), ("Azul (Blue Screen)", "#0000FE"), ("Verde (Green Screen)", "#07FD01")]
        
        for name, color in actions:
            a = QAction(name, self.main_window)
            if color == self.main_window.current_background:
                a.setCheckable(True)
                a.setChecked(True)
            a.triggered.connect(lambda _, c=color: self.change_background(c))
            bg_menu.addAction(a)

        bg_menu.addSeparator()

        # Toggle Sombra
        shadow_action = QAction("Sombra / Shadow", self.main_window)
        shadow_action.setCheckable(True)
        shadow_action.setChecked(self.main_window.shadow_enabled)
        shadow_action.triggered.connect(lambda checked: self.main_window.set_shadow_enabled(checked))
        bg_menu.addAction(shadow_action)

        menu.addSeparator()

        # --- SUBMENÚ: Skins ---
        skin_menu = menu.addMenu("👕 Skins / Avatares")
        
        # Opción 1: Crear Nuevo
        new_skin_action = QAction("➕ Crear Nuevo Skin...", self.main_window)
        new_skin_action.triggered.connect(self.open_creator)
        skin_menu.addAction(new_skin_action)

        # Opción 2: Importar .ptuber
        import_action = QAction("📥 Importar Skin (.ptuber)...", self.main_window)
        import_action.triggered.connect(self.import_profile)
        skin_menu.addAction(import_action)

        # Opción 3: Exportar actual
        export_action = QAction("📤 Exportar Skin Actual...", self.main_window)
        export_action.triggered.connect(self.export_current_profile)
        skin_menu.addAction(export_action)

        skin_menu.addSeparator()

        # Opción 2: Listar Existentes
        self.profile_manager.scan_profiles()
        for profile in self.profile_manager.profiles:
            action = QAction(profile, self.main_window)
            # Marcar el actual con un check
            if profile == self.profile_manager.current_profile:
                action.setCheckable(True)
                action.setChecked(True)
            
            action.triggered.connect(lambda _, p=profile: self.change_profile(p))
            skin_menu.addAction(action)

        menu.addSeparator()

        # --- SUBMENÚ: Rebote ---
        bounce_menu = menu.addMenu("🎾 Rebote / Bounce")

        # Activar/Desactivar
        bounce_toggle = QAction("Activar Rebote", self.main_window)
        bounce_toggle.setCheckable(True)
        bounce_toggle.setChecked(self.main_window.bounce_enabled)
        bounce_toggle.triggered.connect(lambda checked: self.main_window.set_bounce_enabled(checked))
        bounce_menu.addAction(bounce_toggle)
        bounce_menu.addSeparator()

        # Amplitud (0 a 50)
        self.create_slider_action(
            bounce_menu, "Amplitud Rebote", 0, 50, 
            self.main_window.bounce_amplitude, 
            self.main_window.set_bounce_amplitude
        )
        
        # Velocidad (0.1 a 2.0 -> slider 1 a 20)
        self.create_slider_action(
            bounce_menu, "Velocidad Rebote", 1, 20, 
            self.main_window.bounce_speed, 
            self.main_window.set_bounce_speed,
            resolution=10 # Factor division
        )

        menu.exec(self.main_window.mapToGlobal(position))

    def change_background(self, color):
        self.main_window.current_background = color
        if color == "transparent":
            self.central_widget.setStyleSheet("background-color: transparent;")
        else:
            self.central_widget.setStyleSheet(f"background-color: {color}; border-radius: 20px; border: 1px solid rgba(0,0,0,50);")
        self.config_manager.set("background_color", color)

    def change_profile(self, profile_name):
        self.profile_manager.set_profile(profile_name)
        self.main_window.update_avatar()
        self.config_manager.set("current_profile", name)

    def open_creator(self):
        dialog = ProfileCreatorDialog(self.main_window)
        if dialog.exec():
            # Si se creó uno nuevo, recargamos la lista
            self.profile_manager.scan_profiles()

    def import_profile(self):
        path, _ = QFileDialog.getOpenFileName(
            self.main_window, "Importar Skin (.ptuber)", 
            "", "PNGTuber Profile (*.ptuber)"
        )
        
        if not path:
            return

        try:
            with zipfile.ZipFile(path, 'r') as zip_ref:
                # Verificar metadata
                if "meta.json" not in zip_ref.namelist():
                    # Intento de fallback o error
                    # Podríamos usar el nombre del archivo
                    skin_name = os.path.splitext(os.path.basename(path))[0]
                else:
                    with zip_ref.open("meta.json") as f:
                        meta = json.load(f)
                        skin_name = meta.get("name", "UnknownSkin")

                # Asegurar nombre único
                target_dir = os.path.join(self.profile_manager.root_folder, skin_name)
                counter = 1
                base_name = skin_name
                while os.path.exists(target_dir):
                    skin_name = f"{base_name}_{counter}"
                    target_dir = os.path.join(self.profile_manager.root_folder, skin_name)
                    counter += 1

                # Extraer
                os.makedirs(target_dir)
                zip_ref.extractall(target_dir)

                QMessageBox.information(self.main_window, "Importado", f"Skin '{skin_name}' importado correctamente.")
                self.profile_manager.scan_profiles()
                
                # Opcional: Cambiar al nuevo perfil automáticamente
                self.change_profile(skin_name)

        except Exception as e:
            QMessageBox.critical(self.main_window, "Error de Importación", f"No se pudo importar el archivo:\n{e}")

    def export_current_profile(self):
        current = self.profile_manager.current_profile
        if not current or current == "Default":
            # Opcional: Permitir exportar Default si se quisiera, pero suele ser protegido
            pass

        source_dir = os.path.join(self.profile_manager.root_folder, current)
        
        # Pedir ubicación
        save_path, _ = QFileDialog.getSaveFileName(
            self.main_window, "Exportar Skin (.ptuber)", 
            f"{current}.ptuber", 
            "PNGTuber Profile (*.ptuber)"
        )

        if not save_path:
            return

        try:
            # Crear metadata básica
            meta = {
                "name": current,
                "version": "1.0",
                "author": "Usuario"
            }
            meta_path = os.path.join(source_dir, "meta.json")
            with open(meta_path, "w") as f:
                json.dump(meta, f, indent=4)

            # Crear ZIP
            with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(meta_path, "meta.json")
                for filename in os.listdir(source_dir):
                    if filename.endswith(".PNG") or filename.endswith(".png"):
                        zipf.write(os.path.join(source_dir, filename), filename)
            
            os.remove(meta_path)
            QMessageBox.information(self.main_window, "Exportado", f"Skin exportado a:\n{save_path}")

        except Exception as e:
            QMessageBox.critical(self.main_window, "Error de Exportación", f"Falló al exportar:\n{e}")

    def create_slider_action(self, menu, label_text, min_val, max_val, current_val, callback, resolution=1):
        # Widget contenedor
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 5, 10, 5)

        # Etiqueta con valor dinámico
        label = QLabel(f"{label_text}: {current_val}")
        label.setStyleSheet("color: black;")
        layout.addWidget(label)

        # Slider
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(int(current_val * resolution) if resolution > 1 else int(current_val))
        
        def on_change(val):
            real_val = val / resolution if resolution > 1 else val
            label.setText(f"{label_text}: {real_val:.1f}" if resolution > 1 else f"{label_text}: {real_val}")
            callback(real_val)

        slider.valueChanged.connect(on_change)
        layout.addWidget(slider)

        # QWidgetAction permite insertar widgets en menús
        action = QWidgetAction(menu)
        action.setDefaultWidget(container)
        menu.addAction(action)

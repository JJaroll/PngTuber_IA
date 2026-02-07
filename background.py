import os
import zipfile
import json
import shutil
from PyQt6.QtWidgets import QMenu, QWidget, QVBoxLayout, QLabel, QSlider, QWidgetAction, QFileDialog, QMessageBox
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
from profile_creator import ProfileCreatorDialog
from hotkey_gui import HotkeyConfigDialog

class BackgroundManager:
    def __init__(self, main_window, profile_manager, config_manager): 
        self.main_window = main_window
        self.profile_manager = profile_manager
        self.config_manager = config_manager
        self.central_widget = main_window.central_widget

    def show_context_menu(self, position):
        menu = QMenu(self.main_window)
        
        # --- SUBMENÚ: Audio ---
        mute_action = QAction("🔇 Silenciar / Mute", self.main_window)
        mute_action.setCheckable(True)
        mute_action.setChecked(self.main_window.is_muted)
        mute_action.triggered.connect(lambda checked: self.main_window.set_muted(checked))
        menu.addAction(mute_action)

        mic_menu = menu.addMenu("🎤 Micrófono")
        devices = self.main_window.audio_thread.list_devices()
        current_idx = self.main_window.audio_thread.device_index
        
        for idx, name in devices:
            display_name = (name[:30] + '..') if len(name) > 30 else name
            a = QAction(display_name, self.main_window)
            a.setCheckable(True)
            if idx == current_idx:
                a.setChecked(True)
            elif current_idx is None and idx ==  self.main_window.audio_thread.p.get_default_input_device_info()['index']:
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

        shadow_action = QAction("Sombra / Shadow", self.main_window)
        shadow_action.setCheckable(True)
        shadow_action.setChecked(self.main_window.shadow_enabled)
        shadow_action.triggered.connect(lambda checked: self.main_window.set_shadow_enabled(checked))
        bg_menu.addAction(shadow_action)

        menu.addSeparator()

        # --- SUBMENÚ: Skins ---
        skin_menu = menu.addMenu("👕 Skins / Avatares")
        
        new_skin_action = QAction("➕ Crear Nuevo Skin...", self.main_window)
        new_skin_action.triggered.connect(self.open_creator)
        skin_menu.addAction(new_skin_action)

        import_act = QAction("📥 Importar Skin (.ptuber)...", self.main_window)
        import_act.triggered.connect(self.import_skin_dialog)
        skin_menu.addAction(import_act)

        export_act = QAction(f"📤 Exportar '{self.profile_manager.current_profile}'...", self.main_window)
        export_act.triggered.connect(self.export_current_skin)
        skin_menu.addAction(export_act)

        skin_menu.addSeparator()

        self.profile_manager.scan_profiles()
        for profile in self.profile_manager.profiles:
            action = QAction(profile, self.main_window)
            if profile == self.profile_manager.current_profile:
                action.setCheckable(True)
                action.setChecked(True)
            action.triggered.connect(lambda _, p=profile: self.change_profile(p))
            skin_menu.addAction(action)

        menu.addSeparator()

        # --- SUBMENÚ: Rebote ---
        bounce_menu = menu.addMenu("🎾 Rebote / Bounce")
        bounce_toggle = QAction("Activar Rebote", self.main_window)
        bounce_toggle.setCheckable(True)
        bounce_toggle.setChecked(self.main_window.bounce_enabled)
        bounce_toggle.triggered.connect(lambda checked: self.main_window.set_bounce_enabled(checked))
        bounce_menu.addAction(bounce_toggle)
        bounce_menu.addSeparator()

        self.create_slider_action(bounce_menu, "Amplitud Rebote", 0, 50, self.main_window.bounce_amplitude, self.main_window.set_bounce_amplitude)
        self.create_slider_action(bounce_menu, "Velocidad Rebote", 1, 20, self.main_window.bounce_speed, self.main_window.set_bounce_speed, resolution=10)

        menu.addSeparator()

        # Configuración Hotkeys
        hotkey_action = QAction("⌨️ Configurar Hotkeys...", self.main_window)
        hotkey_action.triggered.connect(self.open_hotkey_config)
        menu.addAction(hotkey_action)

        menu.exec(self.main_window.mapToGlobal(position))

    # --- LÓGICA CORREGIDA ---
    def change_background(self, color):
        self.main_window.current_background = color
        
        # NOTA: Ya no tocamos self.main_window.setAttribute(WA_TranslucentBackground)
        # Asumimos que la ventana SIEMPRE es translúcida (definido en main.py)
        
        if color == "transparent":
            # Pintamos el widget "invisible"
            self.central_widget.setStyleSheet("background: transparent;")
        else:
            # Pintamos el widget del color deseado (encima de lo transparente)
            self.central_widget.setStyleSheet(f"background-color: {color}; border-radius: 20px; border: 1px solid rgba(0,0,0,50);")
            
        self.config_manager.set("background_color", color)

    def change_profile(self, profile_name):
        self.profile_manager.set_profile(profile_name)
        self.main_window.update_avatar()
        self.config_manager.set("current_profile", profile_name)

    def open_creator(self):
        dialog = ProfileCreatorDialog(self.main_window)
        if dialog.exec():
            self.profile_manager.scan_profiles()

    def open_hotkey_config(self):
        dialog = HotkeyConfigDialog(self.main_window)
        dialog.exec()


    def import_skin_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self.main_window, "Importar Skin (.ptuber)", "", "PNGTuber Profile (*.ptuber)")
        if path:
            success, res = self.profile_manager.import_skin_package(path)
            if success:
                self.change_profile(res)
                QMessageBox.information(self.main_window, "Éxito", f"Skin '{res}' importado correctamente.")
            else:
                QMessageBox.critical(self.main_window, "Error", f"No se pudo importar: {res}")

    def export_current_skin(self):
        current_name = self.profile_manager.current_profile
        path, _ = QFileDialog.getSaveFileName(self.main_window, "Exportar Skin (.ptuber)", f"{current_name}.ptuber", "PNGTuber Profile (*.ptuber)")
        if path:
            success, msg = self.profile_manager.export_skin_package(current_name, path)
            if success:
                QMessageBox.information(self.main_window, "Éxito", f"Skin guardado en:\n{path}")
            else:
                QMessageBox.critical(self.main_window, "Error", f"Error al exportar: {msg}")

    def create_slider_action(self, menu, label_text, min_val, max_val, current_val, callback, resolution=1):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 5, 10, 5)
        label = QLabel(f"{label_text}: {current_val}")
        label.setStyleSheet("color: black;")
        layout.addWidget(label)
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
        action = QWidgetAction(menu)
        action.setDefaultWidget(container)
        menu.addAction(action)
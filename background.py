from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction
from profile_creator import ProfileCreatorDialog

class BackgroundManager:
    def __init__(self, main_window, profile_manager):
        self.main_window = main_window
        self.central_widget = main_window.central_widget
        self.profile_manager = profile_manager

    def show_context_menu(self, position):
        menu = QMenu(self.main_window)
        
        # --- SUBMENÚ: Fondo ---
        bg_menu = menu.addMenu("🎨 Fondo / Background")
        actions = [("Transparente", "transparent"), ("Azul (Blue Screen)", "#0000FE"), ("Verde (Green Screen)", "#07FD01")]
        
        for name, color in actions:
            a = QAction(name, self.main_window)
            a.triggered.connect(lambda _, c=color: self.change_background(c))
            bg_menu.addAction(a)

        menu.addSeparator()

        # --- SUBMENÚ: Skins ---
        skin_menu = menu.addMenu("👕 Skins / Avatares")
        
        # Opción 1: Crear Nuevo
        new_skin_action = QAction("➕ Crear Nuevo Skin...", self.main_window)
        new_skin_action.triggered.connect(self.open_creator)
        skin_menu.addAction(new_skin_action)
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

        menu.exec(self.main_window.mapToGlobal(position))

    def change_background(self, color):
        style = "background-color: transparent;" if color == "transparent" else f"background-color: {color};"
        self.central_widget.setStyleSheet(style)

    def change_profile(self, profile_name):
        self.profile_manager.set_profile(profile_name)
        self.main_window.update_avatar()

    def open_creator(self):
        dialog = ProfileCreatorDialog(self.main_window)
        if dialog.exec():
            # Si se creó uno nuevo, recargamos la lista
            self.profile_manager.scan_profiles()

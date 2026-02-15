"""
(AI)terEgo
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

import os
import zipfile
import shutil
from PyQt6.QtGui import QImage, QColor, QPainter, QBrush
from PyQt6.QtCore import Qt
from core_systems import SUPPORTED_MODELS

class AvatarProfileManager:
    def __init__(self, root_folder="avatars"):
        self.root_folder = root_folder
        self.current_profile = "Default"
        self.profiles = []
        self.scan_profiles()

    def scan_profiles(self):
        """Escanea perfiles y repara el Default si está roto o vacío"""
        if not os.path.exists(self.root_folder):
            os.makedirs(self.root_folder)
        
        self.profiles = [d for d in os.listdir(self.root_folder) 
                         if os.path.isdir(os.path.join(self.root_folder, d))]
        self.profiles.sort()

        default_path = os.path.join(self.root_folder, "Default")
        
        # Verificar si falta algún archivo en el perfil Default
        missing_files = False
        all_possible_states = set()
        for model in SUPPORTED_MODELS.values():
            all_possible_states.update(model["avatar_states"])
            
        if os.path.exists(default_path):
            current_files = set(os.listdir(default_path))
            for state in all_possible_states:
                if f"{state}_open.PNG" not in current_files or f"{state}_closed.PNG" not in current_files:
                    missing_files = True
                    break
        else:
            missing_files = True

        # Crea o actualiza si faltan archivos
        if missing_files:
            self.create_default_skin(default_path)
            if "Default" not in self.profiles:
                self.profiles.append("Default")
                self.profiles.sort()

        if self.current_profile not in self.profiles:
            if self.profiles:
                self.current_profile = self.profiles[0]
            else:
                self.current_profile = "Default" 

    def create_default_skin(self, target_dir):
        """Genera avatares de emergencia basados en TODOS los modelos posibles"""
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        print(f"🛠️ Reparando skin en: {target_dir}")
        
        # Colores para estados conocidos
        colors = {
            "neutral": "#00E64D", # Verde
            "happy": "#FFD700",   # Amarillo
            "sad": "#4169E1",     # Azul
            "angry": "#FF4500",   # Rojo
            "surprise": "#FF00FF", # Magenta
            "disgust": "#808000", # Oliva
            "fear": "#4B0082"     # Indigo
        }
        
        # Recopilamos todos los estados posibles de todos los modelos
        all_possible_states = set()
        for model in SUPPORTED_MODELS.values():
            all_possible_states.update(model["avatar_states"])
            
        size = 250
        for state in all_possible_states:
            color_hex = colors.get(state, "#CCCCCC") # Gris si no tiene color definido
            
            img = QImage(size, size, QImage.Format.Format_ARGB32)
            img.fill(QColor(0, 0, 0, 0))
            painter = QPainter(img)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            painter.setBrush(QBrush(QColor(color_hex)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(10, 10, size-20, size-20)
            painter.end()
            
            img.save(os.path.join(target_dir, f"{state}_closed.PNG"))
            img.save(os.path.join(target_dir, f"{state}_open.PNG"))

    def set_profile(self, profile_name):
        if profile_name in self.profiles:
            self.current_profile = profile_name
            print(f"👕 Perfil cambiado a: {profile_name}")

    def get_image_path(self, emotion, state):
        """Busca la mejor imagen disponible. Si falta una, usa un reemplazo."""
        
        # Función auxiliar para verificar si es archivo real
        def is_valid_file(path):
            return os.path.exists(path) and os.path.isfile(path)

        # 1. Intento exacto (Ej: happy_open.PNG)
        filename = f"{emotion}_{state}.PNG"
        full_path = os.path.join(self.root_folder, self.current_profile, filename)
        if is_valid_file(full_path): return full_path
            
        # 2. Intento mismo emoción, estado opuesto (Ej: happy_closed.PNG)
        opp_state = "closed" if state == "open" else "open"
        filename = f"{emotion}_{opp_state}.PNG"
        full_path = os.path.join(self.root_folder, self.current_profile, filename)
        if is_valid_file(full_path): return full_path

        # 3. Intento neutral (Ej: neutral_open.PNG)
        filename = f"neutral_{state}.PNG"
        full_path = os.path.join(self.root_folder, self.current_profile, filename)
        if is_valid_file(full_path): return full_path

        # 4. Intento neutral base (Ej: neutral_closed.PNG)
        filename = "neutral_closed.PNG"
        full_path = os.path.join(self.root_folder, self.current_profile, filename)
        if is_valid_file(full_path): return full_path
            
        # 5. Desesperación: Devolver cualquier png real que encuentre
        skin_dir = os.path.join(self.root_folder, self.current_profile)
        if os.path.exists(skin_dir):
            for f in os.listdir(skin_dir):
                if f.lower().endswith(".png"):
                    candidate = os.path.join(skin_dir, f)
                    if os.path.isfile(candidate): 
                        return candidate
        
        # 6. Nada encontrado
        return None

    def export_skin_package(self, profile_name, target_file_path):
        skin_folder = os.path.join(self.root_folder, profile_name)
        if not target_file_path.endswith(".ptuber"):
            target_file_path += ".ptuber"

        try:
            with zipfile.ZipFile(target_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(skin_folder):
                    for file in files:
                        if file.lower().endswith(".png"):
                            file_path = os.path.join(root, file)
                            zipf.write(file_path, arcname=file)
            return True, "Skin exportado exitosamente."
        except Exception as e:
            return False, str(e)

    def import_skin_package(self, source_file_path):
        self.scan_profiles()
        # Excluir 'Default' del conteo
        user_skins = [p for p in self.profiles if p != "Default"]
        if len(user_skins) >= 12:
            return False, "Límite de 12 skins alcanzado (sin contar Default)."

        try:
            skin_name = os.path.splitext(os.path.basename(source_file_path))[0]
            target_dir = os.path.join(self.root_folder, skin_name)
            
            counter = 1
            original_name = skin_name
            while os.path.exists(target_dir):
                skin_name = f"{original_name}_{counter}"
                target_dir = os.path.join(self.root_folder, skin_name)
                counter += 1

            os.makedirs(target_dir)
            with zipfile.ZipFile(source_file_path, 'r') as zipf:
                zipf.extractall(target_dir)
            
            self.scan_profiles()
            return True, skin_name
        except Exception as e:
            return False, str(e)

    def rename_profile(self, old_name, new_name):
        if old_name == "Default": return False, "No se puede renombrar Default."
        new_name = "".join(c for c in new_name if c.isalnum() or c in (' ', '_', '-')).strip()
        if not new_name: return False, "Nombre inválido."

        old_path = os.path.join(self.root_folder, old_name)
        new_path = os.path.join(self.root_folder, new_name)
        
        if not os.path.exists(old_path): return False, "Perfil no existe."
        if os.path.exists(new_path): return False, "Nombre ya existe."
            
        try:
            os.rename(old_path, new_path)
            if self.current_profile == old_name: self.current_profile = new_name
            self.scan_profiles()
            return True, new_name
        except Exception as e: return False, str(e)

    def delete_profile(self, profile_name):
        if profile_name == "Default": return False, "No se puede eliminar Default."
        target_dir = os.path.join(self.root_folder, profile_name)
        if not os.path.exists(target_dir): return False, "Perfil no existe."
            
        try:
            shutil.rmtree(target_dir)
            if self.current_profile == profile_name: self.set_profile("Default")
            self.scan_profiles()
            return True, "Eliminado."
        except Exception as e: return False, str(e)
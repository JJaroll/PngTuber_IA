import os
import zipfile
import shutil
from PyQt6.QtGui import QImage, QColor, QPainter, QBrush
from PyQt6.QtCore import Qt

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
        
        # Si no hay perfiles, o si existe Default pero está vacío
        if not self.profiles or ("Default" in self.profiles and not os.listdir(default_path)):
            self.create_default_skin(default_path)
            if "Default" not in self.profiles:
                self.profiles.append("Default")
                self.profiles.sort()

        if self.current_profile not in self.profiles:
            if self.profiles:
                self.current_profile = self.profiles[0]
            else:
                self.current_profile = "Default" # Fallback extremo

    def create_default_skin(self, target_dir):
        """Genera avatares de emergencia (Círculos) si no hay imágenes"""
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        print(f"🛠️ Reparando skin en: {target_dir}")
        
        emotions = {
            "neutral": "#00E64D", # Verde
            "happy": "#FFD700",   # Amarillo
            "sad": "#4169E1",     # Azul
            "angry": "#FF4500"    # Rojo
        }
        
        size = 250
        for emo, color_hex in emotions.items():
            img = QImage(size, size, QImage.Format.Format_ARGB32)
            img.fill(QColor(0, 0, 0, 0))
            painter = QPainter(img)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QBrush(QColor(color_hex)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(10, 10, size-20, size-20)
            painter.end()
            
            img.save(os.path.join(target_dir, f"{emo}_closed.PNG"))
            img.save(os.path.join(target_dir, f"{emo}_open.PNG"))

    def set_profile(self, profile_name):
        if profile_name in self.profiles:
            self.current_profile = profile_name
            print(f"👕 Perfil cambiado a: {profile_name}")

    def get_image_path(self, emotion, state):
        """Busca la mejor imagen disponible. Si falta una, usa un reemplazo."""
        # 1. Intento exacto (Ej: happy_open.PNG)
        filename = f"{emotion}_{state}.PNG"
        full_path = os.path.join(self.root_folder, self.current_profile, filename)
        if os.path.exists(full_path): return full_path
            
        # 2. Intento mismo emoción, estado opuesto (Ej: happy_closed.PNG)
        opp_state = "closed" if state == "open" else "open"
        filename = f"{emotion}_{opp_state}.PNG"
        full_path = os.path.join(self.root_folder, self.current_profile, filename)
        if os.path.exists(full_path): return full_path

        # 3. Intento neutral (Ej: neutral_open.PNG)
        filename = f"neutral_{state}.PNG"
        full_path = os.path.join(self.root_folder, self.current_profile, filename)
        if os.path.exists(full_path): return full_path

        # 4. Intento neutral base (Ej: neutral_closed.PNG)
        filename = "neutral_closed.PNG"
        full_path = os.path.join(self.root_folder, self.current_profile, filename)
        if os.path.exists(full_path): return full_path
            
        # 5. Desesperación: Devolver CUALQUIER png que encuentre en la carpeta
        skin_dir = os.path.join(self.root_folder, self.current_profile)
        if os.path.exists(skin_dir):
            for f in os.listdir(skin_dir):
                if f.lower().endswith(".png"):
                    return os.path.join(skin_dir, f)
        
        # 6. Si la carpeta está vacía, retornamos None para que main.py genere un error visual
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
        if len(self.profiles) >= 12:
            return False, "Límite de 12 skins alcanzado."

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
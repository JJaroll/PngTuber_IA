import os
import zipfile
import shutil

class AvatarProfileManager:
    def __init__(self, root_folder="avatars"):
        self.root_folder = root_folder
        self.current_profile = "Default"
        self.profiles = []
        self.scan_profiles()

    def scan_profiles(self):
        """Busca subcarpetas dentro de 'avatars' para identificar skins disponibles"""
        if not os.path.exists(self.root_folder):
            os.makedirs(self.root_folder)
            default_path = os.path.join(self.root_folder, "Default")
            if not os.path.exists(default_path):
                os.makedirs(default_path)
        
        self.profiles = [d for d in os.listdir(self.root_folder) 
                         if os.path.isdir(os.path.join(self.root_folder, d))]
        
        self.profiles.sort()

        if not self.profiles:
            self.profiles = ["Default"]
        
        if self.current_profile not in self.profiles:
            self.current_profile = self.profiles[0]

    def set_profile(self, profile_name):
        if profile_name in self.profiles:
            self.current_profile = profile_name
            print(f"👕 Perfil cambiado a: {profile_name}")

    def get_image_path(self, emotion, state):
        filename = f"{emotion}_{state}.PNG"
        return os.path.join(self.root_folder, self.current_profile, filename)

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
            return False, "Límite de 12 skins alcanzado. Borra alguno manualmente para importar uno nuevo."

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
        if old_name == "Default":
            return False, "No se puede renombrar el perfil por defecto (Default)."
        
        new_name = "".join(c for c in new_name if c.isalnum() or c in (' ', '_', '-')).strip()
        if not new_name:
            return False, "Nombre inválido."

        old_path = os.path.join(self.root_folder, old_name)
        new_path = os.path.join(self.root_folder, new_name)
        
        if not os.path.exists(old_path):
            return False, "El perfil original no existe."
        
        if os.path.exists(new_path):
            return False, "Ya existe un perfil con ese nombre."
            
        try:
            os.rename(old_path, new_path)
            if self.current_profile == old_name:
                self.current_profile = new_name
            self.scan_profiles()
            return True, new_name
        except Exception as e:
            return False, str(e)

    # --- NUEVO MÉTODO: ELIMINAR ---
    def delete_profile(self, profile_name):
        if profile_name == "Default":
            return False, "No se puede eliminar el perfil por defecto (Default)."
        
        target_dir = os.path.join(self.root_folder, profile_name)
        if not os.path.exists(target_dir):
            return False, "El perfil no existe."
            
        try:
            shutil.rmtree(target_dir) # Borrado recursivo de la carpeta
            
            # Si borramos el actual, volvemos a Default
            if self.current_profile == profile_name:
                self.set_profile("Default")
                
            self.scan_profiles()
            return True, "Perfil eliminado."
        except Exception as e:
            return False, str(e)
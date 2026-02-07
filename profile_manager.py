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
            # Crear perfil Default si no existe para evitar errores
            default_path = os.path.join(self.root_folder, "Default")
            if not os.path.exists(default_path):
                os.makedirs(default_path)
        
        # Listar solo directorios (cada directorio es un skin)
        self.profiles = [d for d in os.listdir(self.root_folder) 
                         if os.path.isdir(os.path.join(self.root_folder, d))]
        
        self.profiles.sort()

        if not self.profiles:
            self.profiles = ["Default"]
        
        # Si el perfil actual fue borrado, volver al primero disponible
        if self.current_profile not in self.profiles:
            self.current_profile = self.profiles[0]

    def set_profile(self, profile_name):
        """Cambia el perfil activo"""
        if profile_name in self.profiles:
            self.current_profile = profile_name
            print(f"👕 Perfil cambiado a: {profile_name}")

    def get_image_path(self, emotion, state):
        """Devuelve la ruta exacta de la imagen según el perfil activo"""
        # Estructura esperada: avatars/NombrePerfil/emocion_estado.PNG
        filename = f"{emotion}_{state}.PNG"
        return os.path.join(self.root_folder, self.current_profile, filename)

# --- CÓDIGO FALTANTE PARA EXPORTAR/IMPORTAR ---

    def export_skin_package(self, profile_name, target_file_path):
        """Empaqueta la carpeta del perfil en un archivo .ptuber (ZIP)"""
        skin_folder = os.path.join(self.root_folder, profile_name)
        
        # Aseguramos que la extensión sea correcta
        if not target_file_path.endswith(".ptuber"):
            target_file_path += ".ptuber"

        try:
            with zipfile.ZipFile(target_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(skin_folder):
                    for file in files:
                        # Solo guardamos PNGs para evitar archivos basura
                        if file.lower().endswith(".png"):
                            file_path = os.path.join(root, file)
                            # Guardamos el archivo plano en el zip (sin carpetas extrañas)
                            zipf.write(file_path, arcname=file)
            return True, "Skin exportado exitosamente."
        except Exception as e:
            return False, str(e)

    def import_skin_package(self, source_file_path):
        """Desempaqueta un archivo .ptuber en la carpeta avatars"""
        try:
            # El nombre de la carpeta será el nombre del archivo
            skin_name = os.path.splitext(os.path.basename(source_file_path))[0]
            target_dir = os.path.join(self.root_folder, skin_name)

            # Evitar sobreescribir si ya existe (añadir _1, _2...)
            counter = 1
            original_name = skin_name
            while os.path.exists(target_dir):
                skin_name = f"{original_name}_{counter}"
                target_dir = os.path.join(self.root_folder, skin_name)
                counter += 1

            os.makedirs(target_dir)

            with zipfile.ZipFile(source_file_path, 'r') as zipf:
                zipf.extractall(target_dir)
            
            self.scan_profiles() # Actualizar lista de perfiles
            return True, skin_name
        except Exception as e:
            return False, str(e)
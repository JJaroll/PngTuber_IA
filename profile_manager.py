import os

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

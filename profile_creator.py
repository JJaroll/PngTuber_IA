import os
import shutil
import zipfile
import json
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFileDialog, QMessageBox, QGridLayout, QScrollArea, QWidget)
from PyQt6.QtCore import Qt

class ProfileCreatorDialog(QDialog):
    def __init__(self, parent=None, avatars_dir="avatars"):
        super().__init__(parent)
        self.setWindowTitle("Crear Nuevo Skin de Avatar")
        self.resize(500, 600)
        self.avatars_dir = avatars_dir
        self.selected_files = {} 

        self.layout = QVBoxLayout(self)

        # Sección 1: Nombre
        self.layout.addWidget(QLabel("Nombre del Nuevo Skin (Ej: Traje_Gala):"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Escribe el nombre aquí...")
        self.layout.addWidget(self.name_input)

        self.layout.addSpacing(10)
        self.layout.addWidget(QLabel("Asigna las imágenes correspondientes:"))

        # Sección 2: Grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.grid = QGridLayout(content)
        
        self.slots = [
            ("Neutral - Cerrada", "neutral_closed"),
            ("Neutral - Abierta", "neutral_open"),
            ("Feliz - Cerrada", "happy_closed"),
            ("Feliz - Abierta", "happy_open"),
            ("Enojado - Cerrada", "angry_closed"),
            ("Enojado - Abierta", "angry_open"),
            ("Triste - Cerrada", "sad_closed"),
            ("Triste - Abierta", "sad_open"),
        ]

        self.labels = {}
        for i, (text, key) in enumerate(self.slots):
            self.grid.addWidget(QLabel(text), i, 0)
            lbl_status = QLabel("❌ Sin imagen")
            lbl_status.setStyleSheet("color: gray; font-style: italic;")
            self.labels[key] = lbl_status
            self.grid.addWidget(lbl_status, i, 1)
            btn = QPushButton("📂 Seleccionar")
            btn.clicked.connect(lambda _, k=key: self.select_image(k))
            self.grid.addWidget(btn, i, 2)

        scroll.setWidget(content)
        self.layout.addWidget(scroll)

        # Sección 3: Botones
        btns = QHBoxLayout()
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("💾 Guardar y Crear")
        save_btn.setStyleSheet("background-color: #28C840; color: white; font-weight: bold; padding: 6px;")
        save_btn.clicked.connect(self.save_profile)
        
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        self.layout.addLayout(btns)

    def select_image(self, key):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar PNG", "", "Imágenes PNG (*.png *.PNG)")
        if path:
            self.selected_files[key] = path
            filename = os.path.basename(path)
            self.labels[key].setText(f"✅ {filename}")
            self.labels[key].setStyleSheet("color: green; font-weight: bold;")

    def save_profile(self):
        # --- NUEVO: Verificación de límite ---
        current_skins = [d for d in os.listdir(self.avatars_dir) if os.path.isdir(os.path.join(self.avatars_dir, d))]
        if len(current_skins) >= 12:
            QMessageBox.warning(self, "Límite Alcanzado", "Has alcanzado el límite de 12 skins. Borra alguno manualmente antes de crear uno nuevo.")
            return
        # -------------------------------------

        name = self.name_input.text().strip()
        if not name:
            return QMessageBox.warning(self, "Error", "Por favor escribe un nombre para el skin.")
        
        target_dir = os.path.join(self.avatars_dir, name)
        if os.path.exists(target_dir):
            return QMessageBox.warning(self, "Error", "Ya existe un skin con ese nombre.")

        if "neutral_closed" not in self.selected_files or "neutral_open" not in self.selected_files:
            return QMessageBox.warning(self, "Incompleto", "Debes cargar al menos las imágenes 'Neutral' (Abierta y Cerrada).")

        try:
            os.makedirs(target_dir)
            for _, key in self.slots:
                if key in self.selected_files:
                    src = self.selected_files[key]
                    dst = os.path.join(target_dir, f"{key}.PNG")
                    shutil.copy2(src, dst)
            
            QMessageBox.information(self, "Éxito", f"Skin '{name}' creado correctamente.")
            
            reply = QMessageBox.question(
                self, "Exportar Skin", 
                "¿Deseas guardar un archivo .ptuber para compartir este skin?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.export_ptuber(name, target_dir)

            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error Fatal", f"No se pudo crear el perfil:\n{e}")

    def export_ptuber(self, name, source_dir):
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Skin Compacto", f"{name}.ptuber", "PNGTuber Profile (*.ptuber)"
        )
        if not save_path: return

        try:
            meta = { "name": name, "version": "1.0", "author": "Usuario" }
            meta_path = os.path.join(source_dir, "meta.json")
            with open(meta_path, "w") as f:
                json.dump(meta, f, indent=4)

            with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(meta_path, "meta.json")
                for filename in os.listdir(source_dir):
                    if filename.endswith(".PNG") or filename.endswith(".png"):
                        zipf.write(os.path.join(source_dir, filename), filename)
            
            os.remove(meta_path)
            QMessageBox.information(self, "Exportado", f"Archivo guardado en:\n{save_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error Exportación", f"Falló al crear el archivo .ptuber:\n{e}")
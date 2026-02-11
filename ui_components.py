from PyQt6.QtWidgets import QWidget, QDialog, QVBoxLayout, QLabel
from PyQt6.QtGui import QPainter, QBrush, QColor
from PyQt6.QtCore import Qt, QRect

class PillProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(12)  # Altura fija
        self.setMinimumWidth(100) # Ancho mínimo
        
        self._value = 0
        self._color = QColor("#00E64D")
        self._bg_color = QColor("#1e1e1e")

    def setValue(self, val):
        self._value = min(100, max(0, val))
        self.update()

    def set_color_hex(self, hex_code):
        self._color = QColor(hex_code)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        
        # 1. Fondo
        painter.setBrush(QBrush(self._bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        radius = rect.height() / 2
        painter.drawRoundedRect(rect, radius, radius)

        # 2. Relleno
        if self._value > 0:
            width = int(rect.width() * (self._value / 100))
            if width < rect.height() and width > 0:
                width = rect.height()
            
            if width > rect.width():
                width = rect.width()

            progress_rect = QRect(0, 0, width, rect.height())
            painter.setBrush(QBrush(self._color))
            painter.drawRoundedRect(progress_rect, radius, radius)

# --- CLASE DE DESCARGA ---
class DownloadDialog(QDialog):
    def __init__(self, model_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Descargando Modelo IA")
        self.setFixedSize(400, 150)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        self.setModal(True) 

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Icono y Título
        lbl_title = QLabel(f"Descargando: {model_name}")
        lbl_title.setStyleSheet("font-weight: bold; font-size: 14px; color: white;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        lbl_info = QLabel("Esto puede tardar unos minutos dependiendo de tu internet (aprox. 300MB - 1GB). Por favor espera.")
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("color: #aaa; font-size: 11px;")
        lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_info)

        # Barra de progreso indeterminada
        self.progress = PillProgressBar()
        # PillProgressBar ya no soporta setRange(0,0) explícitamente para animación indeterminada en la versión actual,
        # pero podemos simularlo o simplemente mostrarla vacía/llena.
        # Por ahora la mostramos al 50% fija o implementamos un timer aquí si queremos animación.
        self.progress.setValue(50) 
        layout.addWidget(self.progress)
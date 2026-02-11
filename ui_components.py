"""
PNGTuber IA
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

from PyQt6.QtWidgets import QWidget, QDialog, QVBoxLayout, QLabel
from PyQt6.QtGui import QPainter, QBrush, QColor, QPen, QFont
from PyQt6.QtCore import Qt, QRect, QPoint

class PillProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(12)  
        self.setMinimumWidth(100) 
        
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

class TutorialOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setGeometry(parent.rect())
        self.setVisible(False)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 150))
        
        pen = QPen(Qt.GlobalColor.white)
        pen.setWidth(2)
        painter.setPen(pen)
        
        font_title = QFont("Arial", 16, QFont.Weight.Bold)
        painter.setFont(font_title)
        
        rect = self.rect()
        center = rect.center()
        
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Flip: Ctrl+F\nClick derecho: Menú")
        
        start_arrow = QPoint(center.x(), rect.bottom() - 60)
        end_arrow = QPoint(center.x(), rect.bottom() - 20)
        painter.drawLine(start_arrow, end_arrow)
        
        painter.setFont(QFont("Arial", 12))
        painter.drawText(start_arrow.x() - 60, start_arrow.y() - 5, "Controles")
        
        painter.setFont(QFont("Arial", 10, QFont.Weight.Normal))
        painter.drawText(rect.adjusted(0, 0, 0, -50), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, "Haz clic para comenzar")

    def mousePressEvent(self, event):
        if self.parent_window:
            self.parent_window.mark_tutorial_completed()
        self.close()
        self.deleteLater()

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
        self.progress.setValue(50) 
        layout.addWidget(self.progress)
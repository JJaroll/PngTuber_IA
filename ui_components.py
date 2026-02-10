from PyQt6.QtWidgets import QWidget
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
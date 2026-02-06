from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen

class MacWindowControls(QWidget):
    close_signal = pyqtSignal()
    minimize_signal = pyqtSignal()
    maximize_signal = pyqtSignal() # Not used but good practice
    #comentario para que git lo suba

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 20)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 0, 0, 0)
        self.layout.setSpacing(8)

        # Crear botones
        self.btn_close = self._create_button("#FF5F56", "#E0443E", "x")
        self.btn_min = self._create_button("#FFBD2E", "#DEA123", "-")
        self.btn_max = self._create_button("#27C93F", "#1AAB29", "+")
        
        # Conectar señales
        self.btn_close.clicked.connect(self.close_signal.emit)
        self.btn_min.clicked.connect(self.minimize_signal.emit)
        self.btn_max.clicked.connect(self.maximize_signal.emit)

        self.layout.addWidget(self.btn_close)
        self.layout.addWidget(self.btn_min)
        self.layout.addWidget(self.btn_max)
        
        # Simular hover effect en grupo: cuando entras al widget, muestran iconos
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

    def _create_button(self, color, hover_color, symbol):
        btn = MacCircleButton(color, hover_color, symbol)
        return btn
        
    def enterEvent(self, event):
        self.btn_close.set_hover(True)
        self.btn_min.set_hover(True)
        self.btn_max.set_hover(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.btn_close.set_hover(False)
        self.btn_min.set_hover(False)
        self.btn_max.set_hover(False)
        super().leaveEvent(event)

class MacCircleButton(QPushButton):
    def __init__(self, color_hex, border_hex, symbol):
        super().__init__()
        self.setFixedSize(12, 12)
        self.base_color = QColor(color_hex)
        self.border_color = QColor(border_hex)
        self.symbol = symbol
        self.is_hovered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_hover(self, hovered):
        self.is_hovered = hovered
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Dibujar círculo
        painter.setBrush(QBrush(self.base_color))
        painter.setPen(QPen(self.border_color, 1))
        painter.drawEllipse(0, 0, 11, 11)

        # Dibujar símbolo si está en hover
        if self.is_hovered:
            painter.setPen(QColor(0, 0, 0, 150)) # Negro semitransparente
            font = painter.font()
            font.setBold(True)
            font.setPixelSize(10)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.symbol)

        painter.end()

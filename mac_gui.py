from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QRect
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QFont

class MacCircleButton(QPushButton):
    def __init__(self, color_hex, border_hex, symbol, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12) # Tamaño estándar macOS
        self.base_color = QColor(color_hex)
        self.border_color = QColor(border_hex)
        self.symbol = symbol
        
        # Cursor de flecha normal para mayor realismo
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Dibujar Círculo
        painter.setBrush(QBrush(self.base_color))
        painter.setPen(QPen(self.border_color, 1))
        painter.drawEllipse(0, 0, 11, 11)

        # 2. Dibujar Símbolo (Solo si el mouse está sobre el widget contenedor padre)
        # Esto replica el efecto de macOS donde los símbolos aparecen en todos los botones a la vez
        parent = self.parent()
        if parent and parent.underMouse(): 
            painter.setPen(QColor(0, 0, 0, 160)) # Negro al 65% de opacidad
            
            # Fuente Arial Bold pequeña para los iconos
            font = QFont("Arial", 8, QFont.Weight.Bold)
            painter.setFont(font)
            
            # Ajuste fino de posición para centrar cada símbolo visualmente
            if self.symbol == "✕": # Cerrar
                painter.drawText(QRect(0, 0, 12, 11), Qt.AlignmentFlag.AlignCenter, self.symbol)
            elif self.symbol == "−": # Minimizar
                # Ajuste vertical para el signo menos
                painter.drawText(QRect(0, -1, 12, 11), Qt.AlignmentFlag.AlignCenter, self.symbol)
            elif self.symbol == "+": # Maximizar
                 painter.drawText(QRect(0, 0, 12, 12), Qt.AlignmentFlag.AlignCenter, self.symbol)

        painter.end()

class MacWindowControls(QWidget):
    close_signal = pyqtSignal()
    minimize_signal = pyqtSignal()
    maximize_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(54, 16) # Tamaño ajustado al layout nativo
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8) # Espacio entre botones

        # Colores exactos de macOS Big Sur+
        # Pasamos self como parent para que los botones puedan detectar el hover del padre
        self.btn_close = MacCircleButton("#FF5F57", "#E0443E", "✕", self)
        self.btn_min = MacCircleButton("#FEBC2E", "#D89E24", "−", self)
        self.btn_max = MacCircleButton("#28C840", "#1AAB29", "+", self)

        # Conectar señales
        self.btn_close.clicked.connect(self.close_signal.emit)
        self.btn_min.clicked.connect(self.minimize_signal.emit)
        self.btn_max.clicked.connect(self.maximize_signal.emit)

        self.layout.addWidget(self.btn_close)
        self.layout.addWidget(self.btn_min)
        self.layout.addWidget(self.btn_max)

        # Habilitar tracking del mouse para que los botones hijos detecten el hover
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

    # Forzar repintado al entrar/salir para mostrar/ocultar símbolos
    def enterEvent(self, event):
        self.btn_close.update()
        self.btn_min.update()
        self.btn_max.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.btn_close.update()
        self.btn_min.update()
        self.btn_max.update()
        super().leaveEvent(event)

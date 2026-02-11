from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal

class MacWindowControls(QWidget):
    # Señales para que la ventana principal sepa qué hacer
    close_signal = pyqtSignal()
    minimize_signal = pyqtSignal()
    maximize_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuración del contenedor para que se ajuste al contenido
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        layout = QHBoxLayout(self)
        # Márgenes nativos aproximados de macOS (Top, Left, Bottom, Right)
        # Se ajustan para que queden en la esquina superior izquierda
        layout.setContentsMargins(8, 8, 8, 8) 
        layout.setSpacing(8) # Espacio entre los botones

        # --- Estilo Base Común ---
        # Define el tamaño, la forma redonda, y oculta el texto por defecto
        base_style = """
            QPushButton {
                border: none;
                border-radius: 6px; /* Mitad de 12px para hacerlo circular */
                min-width: 12px;
                max-width: 12px;
                min-height: 12px;
                max-height: 12px;
                font-weight: bold;
                font-family: "Arial"; /* Fuente limpia para los símbolos */
                font-size: 10px;
                padding-bottom: 1px; /* Pequeño ajuste vertical para centrar símbolos */
                color: transparent; /* Texto invisible en estado normal */
            }
            QPushButton:hover {
                /* Al pasar el mouse, el símbolo se vuelve visible (gris oscuro) */
                color: rgba(0, 0, 0, 160); 
            }
            QPushButton:pressed {
                 /* Oscurecer ligeramente al hacer click */
                 background-color: rgba(0, 0, 0, 30);
            }
        """

        # --- Botón Cerrar (Rojo) ---
        # Símbolo: '×' (Multiplication Sign - Unicode U+00D7)
        self.btn_close = QPushButton("×")
        self.btn_close.setToolTip("Cerrar")
        # Combinamos el estilo base con el color específico
        self.btn_close.setStyleSheet(base_style + """
            QPushButton { background-color: #FF5F57; border: 1px solid #E0443E; }
            QPushButton:pressed { background-color: #BF4C46; }
        """)
        self.btn_close.clicked.connect(self.close_signal.emit)
        layout.addWidget(self.btn_close)

        # --- Botón Minimizar (Amarillo) ---
        # Símbolo: '−' (Minus Sign - Unicode U+2212)
        self.btn_minimize = QPushButton("−")
        self.btn_minimize.setToolTip("Minimizar")
        self.btn_minimize.setStyleSheet(base_style + """
            QPushButton { background-color: #FFBD2E; border: 1px solid #DEA123; }
            QPushButton:pressed { background-color: #BF9327; }
        """)
        self.btn_minimize.clicked.connect(self.minimize_signal.emit)
        layout.addWidget(self.btn_minimize)

        # --- Botón Maximizar/Zoom (Verde) ---
        # Símbolo: '+' (Plus Sign) - En Mac a veces son flechas, pero + es estándar para zoom
        self.btn_maximize = QPushButton("+")
        self.btn_maximize.setToolTip("Zoom / Pantalla Completa")
        self.btn_maximize.setStyleSheet(base_style + """
            QPushButton { background-color: #28C940; border: 1px solid #1AAB29; }
            QPushButton:pressed { background-color: #1F9A31; }
        """)
        self.btn_maximize.clicked.connect(self.maximize_signal.emit)
        layout.addWidget(self.btn_maximize)

# Pequeña prueba individual para verificar cómo se ve
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    win = QWidget()
    win.setStyleSheet("background-color: #333;") # Fondo oscuro para probar
    l = QHBoxLayout(win)
    controls = MacWindowControls()
    l.addWidget(controls)
    l.addStretch()
    win.show()
    sys.exit(app.exec())
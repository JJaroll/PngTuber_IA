from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction

class BackgroundManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.central_widget = main_window.central_widget

    def show_context_menu(self, position):
        menu = QMenu(self.main_window)
        
        action_transparent = QAction("Transparente", self.main_window)
        action_blue = QAction("Azul (Blue Screen)", self.main_window)
        action_green = QAction("Verde (Green Screen)", self.main_window)

        action_transparent.triggered.connect(lambda: self.change_background("transparent"))
        action_blue.triggered.connect(lambda: self.change_background("#0000FE"))
        action_green.triggered.connect(lambda: self.change_background("#07FD01"))

        menu.addAction(action_transparent)
        menu.addAction(action_blue)
        menu.addAction(action_green)

        menu.exec(self.main_window.mapToGlobal(position))

    def change_background(self, color):
        if color == "transparent":
            self.central_widget.setStyleSheet("background-color: transparent;")
        else:
            self.central_widget.setStyleSheet(f"background-color: {color};")

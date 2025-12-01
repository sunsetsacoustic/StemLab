from PyQt6.QtWidgets import QSplashScreen, QProgressBar, QVBoxLayout, QLabel, QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QPen
from .style import COLORS

class SplashScreen(QSplashScreen):
    def __init__(self):
        # Determine resource path
        import sys
        import os
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
            
        splash_path = os.path.join(base_path, "resources", "splash.png")
        
        if os.path.exists(splash_path):
            pixmap = QPixmap(splash_path)
            # Resize if too big, but keep aspect ratio? Or just use as is. 
            # The user image looks like a banner. Let's scale it to a reasonable width if needed.
            # pixmap = pixmap.scaled(600, 400, Qt.AspectRatioMode.KeepAspectRatio) 
        else:
            # Fallback if image missing
            pixmap = QPixmap(600, 400)
            pixmap.fill(QColor(COLORS['background']))
            painter = QPainter(pixmap)
            painter.setPen(QColor(COLORS['text']))
            painter.drawText(0, 0, 600, 400, Qt.AlignmentFlag.AlignCenter, "StemLab")
            painter.end()

        # Initialize with the pixmap
        super().__init__(pixmap)
        
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        
        # Add Progress Bar (Overlay widget)
        # QSplashScreen doesn't support layouts easily, so we just draw or use a child widget
        # But child widgets on splash screens can be tricky.
        # Let's just use the showMessage method for text.

    def show_message(self, message):
        self.showMessage(message, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, QColor(COLORS['secondary']))

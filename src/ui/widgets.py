from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
    QProgressBar, QPushButton, QFrame, QStyle
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QDrag, QAction
from .style import COLORS
import os

class DragDropWidget(QFrame):
    files_dropped = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet(f"""
            QFrame {{
                border: 2px dashed {COLORS['text_dim']};
                border-radius: 15px;
                background-color: rgba(26, 26, 46, 0.3);
            }}
            QFrame:hover {{
                border-color: {COLORS['secondary']};
                background-color: rgba(0, 229, 255, 0.1);
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.label = QLabel("DRAG & DROP AUDIO FILES HERE\nor Click 'Add Files'")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 16px; font-weight: bold;")
        layout.addWidget(self.label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
            self.setStyleSheet(f"""
                QFrame {{
                    border: 2px dashed {COLORS['primary']};
                    border-radius: 15px;
                    background-color: rgba(214, 0, 255, 0.1);
                }}
            """)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet(f"""
            QFrame {{
                border: 2px dashed {COLORS['text_dim']};
                border-radius: 15px;
                background-color: rgba(26, 26, 46, 0.3);
            }}
        """)

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet(f"""
            QFrame {{
                border: 2px dashed {COLORS['text_dim']};
                border-radius: 15px;
                background-color: rgba(26, 26, 46, 0.3);
            }}
        """)
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        valid_files = [f for f in files if f.lower().endswith(('.mp3', '.wav', '.flac', '.m4a'))]
        if valid_files:
            self.files_dropped.emit(valid_files)

class DragButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__("DRAG", parent)
        self.setFixedSize(50, 30)
        self.setToolTip("Drag Stems to DAW")
        self.setStyleSheet(f"font-weight: bold; color: {COLORS['accent']}; border: 1px solid {COLORS['accent']}; border-radius: 4px;")
        self.files = []

    def set_files(self, files):
        self.files = files

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton and self.files:
            drag = QDrag(self)
            mime = QMimeData()
            urls = [QUrl.fromLocalFile(f) for f in self.files if os.path.exists(f)]
            mime.setUrls(urls)
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.CopyAction)
        super().mouseMoveEvent(e)

class QueueItemWidget(QWidget):
    cancel_requested = pyqtSignal()
    open_folder_requested = pyqtSignal()
    resplit_requested = pyqtSignal()

    def __init__(self, filename, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.name_label = QLabel(filename)
        self.name_label.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold;")
        layout.addWidget(self.name_label, stretch=2)
        
        self.status_label = QLabel("Pending")
        self.status_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        layout.addWidget(self.status_label, stretch=1)
        
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {COLORS['secondary']};
                border-radius: 4px;
                background-color: {COLORS['background']};
                height: 10px;
            }}
            QProgressBar::chunk {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLORS['primary']}, stop:1 {COLORS['secondary']});
                border-radius: 2px;
            }}
        """)
        layout.addWidget(self.progress, stretch=3)
        
        self.cancel_btn = QPushButton()
        self.cancel_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton))
        self.cancel_btn.setFixedSize(30, 30)
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {COLORS['danger']};
                border-radius: 15px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger']};
            }}
        """)
        self.cancel_btn.clicked.connect(self.cancel_requested.emit)
        layout.addWidget(self.cancel_btn)
        
        self.open_btn = QPushButton()
        self.open_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.open_btn.setFixedSize(30, 30)
        self.open_btn.setToolTip("Open Output Folder")
        self.open_btn.hide()
        self.open_btn.clicked.connect(self.open_output_folder)
        layout.addWidget(self.open_btn)
        
        self.drag_btn = DragButton()
        self.drag_btn.hide()
        layout.addWidget(self.drag_btn)

    def update_progress(self, filename, value, status=None, output_files=None):
        self.progress.setValue(value)
        if status:
            self.status_label.setText(status)
            if "Error" in status:
                self.status_label.setStyleSheet(f"color: {COLORS['danger']};")
            elif "Done" in status:
                self.status_label.setStyleSheet(f"color: {COLORS['success']};")
                self.open_btn.show()
                self.drag_btn.show()
                self.cancel_btn.hide()
                if output_files:
                    self.drag_btn.set_files(output_files)
            elif "Pending" in status:
                self.open_btn.hide()
                self.drag_btn.hide()
                self.cancel_btn.show()
                
    def contextMenuEvent(self, event):
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        menu = QMenu(self)
        
        open_action = QAction("Open Output Folder", self)
        open_action.triggered.connect(self.open_output_folder)
        menu.addAction(open_action)
        
        menu.addSeparator()
        
        resplit_action = QAction("Re-split", self)
        resplit_action.triggered.connect(self.resplit_requested.emit)
        menu.addAction(resplit_action)
        
        remove_action = QAction("Remove", self)
        remove_action.triggered.connect(self.cancel_requested.emit)
        menu.addAction(remove_action)
        
        menu.exec(event.globalPos())

    def open_output_folder(self):
        self.open_folder_requested.emit()

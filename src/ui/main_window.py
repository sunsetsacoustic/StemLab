import os
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QListWidget, QListWidgetItem, QFileDialog,
    QGroupBox, QRadioButton, QCheckBox, QSlider, QLabel,
    QDialog, QTextEdit, QStyle
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from .style import STYLESHEET, COLORS, apply_theme
from .widgets import DragDropWidget, QueueItemWidget
from src.core.splitter import SplitterWorker
from src.core.gpu_utils import get_gpu_info

# Log Window
class LogWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Process Logs")
        self.resize(600, 400)
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet(f"background-color: {COLORS['background']}; color: {COLORS['text']}; font-family: Consolas, monospace;")
        layout.addWidget(self.text_edit)

class LogEmitter(QObject):
    text_written = pyqtSignal(str)

class StreamRedirector:
    def __init__(self, emitter):
        self.emitter = emitter
    def write(self, text):
        self.emitter.text_written.emit(text)
    def flush(self):
        pass

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StemLab v1.0")
        self.resize(1000, 700)
        
        # Setup Logging
        self.log_emitter = LogEmitter()
        self.log_emitter.text_written.connect(self.append_log)
        sys.stdout = StreamRedirector(self.log_emitter)
        sys.stderr = StreamRedirector(self.log_emitter)
        
        self.log_window = LogWindow(self)
        
        # Central Widget
        central = QWidget()
        self.setCentralWidget(central)
        self.main_layout = QHBoxLayout(central)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        apply_theme(self)
        self.setup_ui()
        
        # Initial State
        self.slider_quality.setValue(1)

    def setup_ui(self):
        # Left Panel (Controls)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setFixedWidth(300)
        
        # Logo / Title
        title = QLabel("STEM\nLAB")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size: 36px; font-weight: 900; color: {COLORS['text']}; margin-top: 10px;")
        left_layout.addWidget(title)

        tagline = QLabel("Professional-grade AI stem separation.\nLocal. Unlimited. One-time payment.")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setWordWrap(True)
        tagline.setStyleSheet(f"font-size: 11px; color: {COLORS['text_dim']}; margin-bottom: 20px; font-style: italic;")
        left_layout.addWidget(tagline)
        
        # GPU Indicator
        self.gpu_label = QLabel("Checking GPU...")
        self.gpu_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gpu_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px; margin-bottom: 10px;")
        left_layout.addWidget(self.gpu_label)
        
        # Update GPU info
        is_gpu, device_name = get_gpu_info()
        if is_gpu:
            self.gpu_label.setText(f"{device_name} • Ready")
            self.gpu_label.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px; margin-bottom: 10px; font-weight: bold;")
        else:
            self.gpu_label.setText("CPU Mode (Slower)")
            self.gpu_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px; margin-bottom: 10px;")

        # Stem Options
        stem_group = QGroupBox("STEM OPTIONS")
        stem_layout = QVBoxLayout()
        
        self.radio_2stem = QRadioButton("2-Stem (Vocals / Instrumental)")
        self.radio_4stem = QRadioButton("4-Stem (Classic)")
        self.radio_6stem = QRadioButton("6-Stem (Full Band)")
        self.radio_vocals = QRadioButton("Vocals Only (Ultra Clean)")
        self.radio_inst = QRadioButton("Instrumental / Karaoke")
        
        # Set default
        self.radio_2stem.setChecked(True)
        
        stem_layout.addWidget(self.radio_2stem)
        stem_layout.addWidget(self.radio_4stem)
        stem_layout.addWidget(self.radio_6stem)
        stem_layout.addWidget(self.radio_vocals)
        stem_layout.addWidget(self.radio_inst)
        
        # Advanced Toggle
        self.chk_dereverb = QCheckBox("De-Reverb + De-Echo (Experimental)")
        self.chk_dereverb.setStyleSheet(f"color: {COLORS['secondary']}; margin-top: 5px;")
        stem_layout.addWidget(self.chk_dereverb)
        
        stem_group.setLayout(stem_layout)
        left_layout.addWidget(stem_group)
        
        # Speed/Quality
        quality_group = QGroupBox("QUALITY MODE")
        quality_layout = QVBoxLayout()
        
        self.slider_quality = QSlider(Qt.Orientation.Horizontal)
        self.slider_quality.setRange(0, 2)
        self.slider_quality.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_quality.setTickInterval(1)
        self.slider_quality.valueChanged.connect(self.update_quality_label)
        
        self.label_quality = QLabel("Balanced (GPU Auto)")
        self.label_quality.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_quality.setStyleSheet(f"color: {COLORS['secondary']}; font-weight: bold;")
        
        quality_layout.addWidget(self.label_quality)
        quality_layout.addWidget(self.slider_quality)
        quality_group.setLayout(quality_layout)
        left_layout.addWidget(quality_group)
        
        # Output Options
        out_group = QGroupBox("OUTPUT")
        out_layout = QVBoxLayout()
        self.chk_mp3 = QCheckBox("Export as MP3 320kbps")
        self.chk_zip = QCheckBox("Export as ZIP")
        self.chk_keep = QCheckBox("Keep Original")
        self.chk_keep.setChecked(True)
        self.chk_auto_open = QCheckBox("Auto-open Folder")
        self.chk_auto_open.setChecked(True)
        
        out_layout.addWidget(self.chk_mp3)
        out_layout.addWidget(self.chk_zip)
        out_layout.addWidget(self.chk_keep)
        out_layout.addWidget(self.chk_auto_open)
        out_group.setLayout(out_layout)
        left_layout.addWidget(out_group)
        
        left_layout.addStretch()
        
        # Process Button
        self.btn_process = QPushButton("START PROCESSING")
        self.btn_process.setFixedHeight(50)
        self.btn_process.setStyleSheet(f"font-size: 16px; background-color: {COLORS['primary']}; color: white;")
        self.btn_process.clicked.connect(self.start_processing)
        left_layout.addWidget(self.btn_process)
        
        # Logs Button
        self.logs_btn = QPushButton("Show Logs")
        self.logs_btn.setStyleSheet(f"color: {COLORS['text_dim']}; background: transparent; border: none; text-decoration: underline;")
        self.logs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logs_btn.clicked.connect(self.log_window.show)
        left_layout.addWidget(self.logs_btn)
        
        self.main_layout.addWidget(left_panel)
        
        # Right Panel (Queue)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Drag Drop Area
        self.drag_drop = DragDropWidget()
        self.drag_drop.setFixedHeight(150)
        self.drag_drop.files_dropped.connect(self.add_files_to_queue)
        right_layout.addWidget(self.drag_drop)
        
        # Queue List
        self.queue_list = QListWidget()
        right_layout.addWidget(self.queue_list)
        
        # Bottom Controls
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add Files")
        self.btn_add.clicked.connect(self.open_file_dialog)
        self.btn_clear = QPushButton("Clear Queue")
        self.btn_clear.clicked.connect(self.queue_list.clear)
        
        btn_layout.addWidget(self.btn_add)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_clear)
        right_layout.addLayout(btn_layout)
        
        self.main_layout.addWidget(right_panel)

    def append_log(self, text):
        self.log_window.text_edit.moveCursor(self.log_window.text_edit.textCursor().MoveOperation.End)
        self.log_window.text_edit.insertPlainText(text)
        self.log_window.text_edit.moveCursor(self.log_window.text_edit.textCursor().MoveOperation.End)

    def update_quality_label(self, value):
        labels = ["Fast (CPU)", "Balanced (GPU Auto)", "Best (Ensemble)"]
        self.label_quality.setText(labels[value])

    def open_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Audio Files", "", "Audio Files (*.mp3 *.wav *.flac *.m4a)"
        )
        if files:
            self.add_files_to_queue(files)

    def add_files_to_queue(self, files):
        for f in files:
            item = QListWidgetItem(self.queue_list)
            item.setData(Qt.ItemDataRole.UserRole, f) # Store full path
            widget = QueueItemWidget(os.path.basename(f))
            item.setSizeHint(widget.sizeHint())
            self.queue_list.addItem(item)
            self.queue_list.setItemWidget(item, widget)
            
            # Connect cancel signal
            widget.cancel_requested.connect(lambda i=item: self.remove_queue_item(i))
            # Connect open folder signal
            widget.open_folder_requested.connect(lambda i=item: self.open_item_folder(i))
            # Connect resplit signal
            widget.resplit_requested.connect(lambda i=item: self.resplit_item(i))

    def resplit_item(self, item):
        widget = self.queue_list.itemWidget(item)
        widget.update_progress(None, 0, "Pending")
        widget.status_label.setStyleSheet(f"color: {COLORS['text_dim']};")
        self.start_processing()

    def remove_queue_item(self, item):
        # Check if this item is currently being processed
        if hasattr(self, 'worker') and self.worker.isRunning():
            widget = self.queue_list.itemWidget(item)
            # Simple check: if status is not Pending/Done/Error, it's likely processing
            status = widget.status_label.text()
            if "Pending" not in status and "Done" not in status and "Error" not in status and "Cancelled" not in status:
                from src.utils.logger import logger
                logger.info("Terminating active process...")
                
                # Terminate worker (kills subprocess)
                self.worker.terminate()
                self.worker.wait()
                widget.update_progress(None, 0, "Cancelled")
                
                # Cleanup partially created files
                file_path = item.data(Qt.ItemDataRole.UserRole)
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                output_dir = os.path.join(os.path.dirname(file_path), f"{base_name} - Stems")
                
                if os.path.exists(output_dir):
                    import shutil
                    try:
                        shutil.rmtree(output_dir)
                        logger.info(f"Cleaned up output directory: {output_dir}")
                    except Exception as e:
                        logger.error(f"Failed to clean up output directory: {e}")
        
        row = self.queue_list.row(item)
        self.queue_list.takeItem(row)

    def open_item_folder(self, item):
        import subprocess
        file_path = item.data(Qt.ItemDataRole.UserRole)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_dir = os.path.join(os.path.dirname(file_path), f"{base_name} - Stems")
        
        if os.path.exists(output_dir):
            os.startfile(output_dir)
        else:
            # Fallback to parent dir if stems folder doesn't exist yet
            os.startfile(os.path.dirname(file_path))

    def start_processing(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            return

        # Find first pending item
        for i in range(self.queue_list.count()):
            item = self.queue_list.item(i)
            widget = self.queue_list.itemWidget(item)
            
            if widget.status_label.text() == "Pending":
                self.process_item(item)
                return

    def process_item(self, item):
        widget = self.queue_list.itemWidget(item)
        file_path = item.data(Qt.ItemDataRole.UserRole)
        
        # Determine Stem Mode
        stem_count = 4
        mode = "standard" # standard, vocals_only, instrumental, remix_pack
        
        if self.radio_6stem.isChecked():
            stem_count = 6
        elif self.radio_2stem.isChecked():
            stem_count = 2
        elif self.radio_vocals.isChecked():
            stem_count = 2
            mode = "vocals_only"
        elif self.radio_inst.isChecked():
            stem_count = 2
            mode = "instrumental"

        options = {
            "stem_count": stem_count,
            "mode": mode,
            "quality": self.slider_quality.value(),
            "export_zip": self.chk_zip.isChecked(),
            "keep_original": self.chk_keep.isChecked(),
            "export_mp3": self.chk_mp3.isChecked(),
            "dereverb": self.chk_dereverb.isChecked()
        }
        
        self.worker = SplitterWorker(file_path, options)
        self.worker.progress_updated.connect(widget.update_progress)
        self.worker.finished.connect(lambda _: self.on_worker_finished(item))
        self.worker.error_occurred.connect(lambda f, e: self.on_worker_error(item, e))
        self.worker.start()

    def on_worker_finished(self, item):
        import winsound
        import glob
        
        file_path = item.data(Qt.ItemDataRole.UserRole)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_dir = os.path.join(os.path.dirname(file_path), f"{base_name} - Stems")
        
        # Collect generated files for drag-and-drop
        output_files = []
        if os.path.exists(output_dir):
            output_files = glob.glob(os.path.join(output_dir, "*.wav"))
            output_files += glob.glob(os.path.join(output_dir, "*.mp3"))

        widget = self.queue_list.itemWidget(item)
        widget.update_progress(None, 100, "Done", output_files=output_files)
        
        # Play success sound
        try:
            winsound.MessageBeep(winsound.MB_OK)
        except:
            pass
            
        # Auto-open folder if enabled
        if self.chk_auto_open.isChecked():
            self.open_item_folder(item)
            
        # Process next
        self.start_processing()

    def on_worker_error(self, item, error):
        widget = self.queue_list.itemWidget(item)
        widget.status_label.setText(f"Error: {error}")
        widget.status_label.setStyleSheet(f"color: {COLORS['danger']};")
        # Process next
        self.start_processing()

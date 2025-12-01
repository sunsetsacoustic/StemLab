
COLORS = {
    "background": "#0E0E0E",
    "surface": "#1A1A1A",
    "primary": "#00D4FF",  # Bright Cyan
    "secondary": "#FF6B6B", # Soft Coral
    "text": "#FFFFFF",
    "text_dim": "#B0B0B0",
    "danger": "#FF4444",
    "success": "#00D4FF",
    "accent": "#FF6B6B"
}

STYLESHEET = f"""
QMainWindow {{
    background-color: {COLORS['background']};
}}

QWidget {{
    color: {COLORS['text']};
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
}}

/* Buttons */
QPushButton {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['primary']};
    border-radius: 8px;
    padding: 8px 16px;
    color: {COLORS['primary']};
    font-weight: bold;
}}

QPushButton:hover {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLORS['primary']}, stop:1 {COLORS['secondary']});
    color: {COLORS['background']};
    border: 1px solid {COLORS['primary']};
}}

QPushButton:pressed {{
    background-color: {COLORS['primary']};
    border-color: {COLORS['secondary']};
}}

QPushButton:disabled {{
    border-color: {COLORS['text_dim']};
    color: {COLORS['text_dim']};
    background-color: transparent;
}}

/* Group Box */
QGroupBox {{
    border: 1px solid #333333;
    border-radius: 8px;
    margin-top: 20px;
    background-color: rgba(255, 255, 255, 0.03);
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 10px;
    color: {COLORS['primary']};
    font-weight: bold;
    background-color: {COLORS['background']};
}}

/* Sliders */
QSlider::groove:horizontal {{
    border: 1px solid #333333;
    height: 6px;
    background: #222222;
    margin: 2px 0;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: {COLORS['primary']};
    border: 1px solid {COLORS['primary']};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}

/* Progress Bar */
QProgressBar {{
    border: none;
    background-color: #222222;
    border-radius: 4px;
    text-align: center;
    color: white;
}}

QProgressBar::chunk {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLORS['primary']}, stop:1 {COLORS['secondary']});
    border-radius: 4px;
}}

/* List Widget */
QListWidget {{
    background-color: {COLORS['surface']};
    border: 1px solid #333333;
    border-radius: 8px;
    padding: 5px;
}}

QListWidget::item {{
    padding: 8px;
    border-radius: 4px;
    margin-bottom: 2px;
}}

QListWidget::item:selected {{
    background-color: rgba(0, 212, 255, 0.1);
    border: 1px solid {COLORS['primary']};
}}
"""

def apply_theme(app_or_window):
    app_or_window.setStyleSheet(STYLESHEET)

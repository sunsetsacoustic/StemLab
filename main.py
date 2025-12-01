import sys
import os

# Fix for 'NoneType' object has no attribute 'write' in noconsole mode
class StreamRedirector:
    def write(self, text):
        pass
    def flush(self):
        pass

if sys.stdout is None:
    sys.stdout = StreamRedirector()
if sys.stderr is None:
    sys.stderr = StreamRedirector()

from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.ui.splash import SplashScreen
import time

def run_worker(args):
    # args is a list of arguments passed after --worker
    # Expected: input_file stem_count quality export_zip keep_original
    try:
        import json
        # We'll pass a single JSON string for simplicity
        config = json.loads(args[0])
        
        from src.core.splitter import separate_audio
        separate_audio(
            config['input_file'],
            config['output_dir'],
            config['stem_count'],
            config['quality'],
            config['export_zip'],
            config['keep_original'],
            export_mp3=config.get('export_mp3', False),
            mode=config.get('mode', 'standard'),
            dereverb=config.get('dereverb', False),
            invert=config.get('invert', False)
        )
    except Exception as e:
        print(f"WORKER ERROR: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    if "--worker" in sys.argv:
        # Worker mode
        idx = sys.argv.index("--worker")
        run_worker(sys.argv[idx+1:])
        return

    app = QApplication(sys.argv)
    app.setApplicationName("StemLab")
    
    splash = SplashScreen()
    splash.show()
    splash.show_message("Initializing Core Systems...")
    app.processEvents()
    
    # Simulate loading (or actually load things if we had heavy imports)
    time.sleep(1) 
    splash.show_message("Loading AI Models...")
    app.processEvents()
    time.sleep(1)
    splash.show_message("Starting UI...")
    app.processEvents()
    time.sleep(0.5)
    
    window = MainWindow()
    window.show()
    splash.finish(window)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

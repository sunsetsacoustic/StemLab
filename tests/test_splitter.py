import sys
import os
import time
from PyQt6.QtCore import QCoreApplication
from src.core.splitter import SplitterWorker

# Mock App
app = QCoreApplication(sys.argv)

def test_worker():
    print("Testing SplitterWorker...")
    
    file_path = "test_audio.mp3"
    options = {"stem_count": 4, "quality": 1}
    
    worker = SplitterWorker(file_path, options)
    
    def on_progress(filename, progress, status):
        print(f"Progress: {progress}% - {status}")
        
    def on_finished(filename):
        print(f"Finished: {filename}")
        app.quit()
        
    worker.progress_updated.connect(on_progress)
    worker.finished.connect(on_finished)
    
    worker.start()
    
    # Run event loop
    app.exec()

if __name__ == "__main__":
    test_worker()

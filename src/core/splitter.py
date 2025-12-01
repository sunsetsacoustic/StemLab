import os
import shutil
import sys
import subprocess
import json


from PyQt6.QtCore import QThread, pyqtSignal
from src.utils.logger import logger
import demucs.separate
import torch
import torchaudio
import soundfile as sf
try:
    from src.core.advanced_audio import AdvancedAudioProcessor
except ImportError:
    AdvancedAudioProcessor = None
    logger.warning("AdvancedAudioProcessor not available (audio-separator missing?)")

# Monkeypatch torchaudio to use soundfile directly (Fix for Python 3.14 / torchaudio 2.9.1)
def custom_load(filepath, *args, **kwargs):
    wav, sr = sf.read(filepath)
    wav = torch.tensor(wav).float()
    if wav.ndim == 1:
        wav = wav.unsqueeze(0)
    else:
        wav = wav.t()
    return wav, sr

def custom_save(filepath, src, sample_rate, **kwargs):
    src = src.detach().cpu().t().numpy()
    sf.write(filepath, src, sample_rate)

torchaudio.load = custom_load
torchaudio.save = custom_save

def separate_audio(input_file, output_dir, stem_count, quality, export_zip, keep_original, **kwargs):
    filename = os.path.basename(input_file)
    base_name = os.path.splitext(filename)[0]
    os.makedirs(output_dir, exist_ok=True)

    # Determine Model and Args
    model = "htdemucs"
    shifts = 1
    overlap = 0.25
    
    if stem_count == 6:
        model = "htdemucs_6s"
    
    if quality == 0: # Fast
        shifts = 0
        overlap = 0.1
    elif quality == 2: # Best
        if stem_count == 4:
            model = "htdemucs_ft" # Fine-tuned 4-stem
        shifts = 2
        overlap = 0.25

    # Construct Demucs Args
    args = [
        "-n", model,
        "--shifts", str(shifts),
        "--overlap", str(overlap),
        "-o", output_dir,
        "--filename", "{track}/{stem}.{ext}",
        input_file
    ]
    
    if stem_count == 2:
        args.append("--two-stems=vocals")
        
    if kwargs.get("export_mp3", False):
        args.append("--mp3")
        args.append("--mp3-bitrate")
        args.append("320")
    
    if not torch.cuda.is_available():
        args.append("-d")
        args.append("cpu")

    # Run Demucs
    demucs.separate.main(args)
    
    # Organize Files
    # Organize Files
    demucs_output_root = os.path.join(output_dir, model, base_name)
    
    mode = kwargs.get("mode", "standard")
    ext = "mp3" if kwargs.get("export_mp3", False) else "wav"
    
    if os.path.exists(demucs_output_root):
        for stem in os.listdir(demucs_output_root):
            src = os.path.join(demucs_output_root, stem)
            
            # Filter based on mode
            should_keep = True
            if mode == "vocals_only" and "vocals" not in stem:
                should_keep = False
            elif mode == "instrumental" and "no_vocals" not in stem:
                should_keep = False
            
            if should_keep:
                dst = os.path.join(output_dir, stem)
                shutil.move(src, dst)
        
        # Clean up empty folders
        shutil.rmtree(os.path.join(output_dir, model))
    
    # Copy Original if requested
    if keep_original:
        shutil.copy(input_file, os.path.join(output_dir, f"original.{ext}"))
        
    # De-Reverb Logic (Placeholder/Basic Implementation)
    if kwargs.get("dereverb", False):
        logger.info("De-Reverb requested (Experimental)")

    # Advanced Pipeline (Vocals Only)
    if mode == "vocals_only" and AdvancedAudioProcessor:
        try:
            logger.info("Starting Advanced Audio Pipeline (Ensemble/MDX)...")
            processor = AdvancedAudioProcessor(output_dir)
            
            # Demucs output might be mp3 or wav depending on flag
            demucs_vocals = os.path.join(output_dir, f"vocals.{ext}")
            
            # If MP3, we might need to convert back to WAV for processing, or ensure processor handles it
            # For simplicity, let's assume processor handles input formats supported by soundfile/ffmpeg
            
            if os.path.exists(demucs_vocals):
                final_vocals = processor.process_vocals_ultra_clean(input_file, demucs_vocals)
                
                # Rename/Move result
                if final_vocals and os.path.exists(final_vocals):
                    target_name = f"vocals_ultra_clean.wav" # Processor outputs WAV
                    shutil.move(final_vocals, os.path.join(output_dir, target_name))
                    
                    # Convert to MP3 if requested
                    if kwargs.get("export_mp3", False):
                        mp3_target = f"vocals_ultra_clean.mp3"
                        # Use pydub or ffmpeg to convert. 
                        # Since we have ffmpeg in path (checked by debug script), we can use subprocess
                        subprocess.run(f'ffmpeg -y -i "{os.path.join(output_dir, target_name)}" -b:a 320k "{os.path.join(output_dir, mp3_target)}"', shell=True)
                        os.remove(os.path.join(output_dir, target_name)) # Remove WAV
                        target_name = mp3_target
                        
                    logger.info(f"Created Ultra Clean Vocals: {target_name}")
                    
                    # Create Instrumental Inversion if needed
                    if kwargs.get("invert", False):
                        inst_path = os.path.join(output_dir, f"instrumental_inverted.wav")
                        processor.invert_audio(input_file, os.path.join(output_dir, target_name), inst_path)
                        
                        if kwargs.get("export_mp3", False):
                             mp3_inst = f"instrumental_inverted.mp3"
                             subprocess.run(f'ffmpeg -y -i "{inst_path}" -b:a 320k "{os.path.join(output_dir, mp3_inst)}"', shell=True)
                             os.remove(inst_path)
                             inst_path = mp3_inst
                             
                        logger.info(f"Created Inverted Instrumental: {inst_path}")

        except Exception as e:
            logger.error(f"Advanced Pipeline Failed: {e}")
            # Fallback to standard Demucs output is already there, so just log error.

    # Zip if requested
    if export_zip:
        shutil.make_archive(output_dir, 'zip', output_dir)

class SplitterWorker(QThread):
    progress_updated = pyqtSignal(str, int, str) # filename, progress, status
    finished = pyqtSignal(str) # filename
    error_occurred = pyqtSignal(str, str) # filename, error message

    def __init__(self, file_path, options):
        super().__init__()
        self.file_path = file_path
        self.options = options
        self.process = None
        self.is_cancelled = False

    def run(self):
        filename = os.path.basename(self.file_path)
        logger.info(f"Starting processing for {filename} with options: {self.options}")
        
        try:
            base_name = os.path.splitext(filename)[0]
            output_dir = os.path.join(os.path.dirname(self.file_path), f"{base_name} - Stems")
            
            config = {
                "input_file": self.file_path,
                "output_dir": output_dir,
                "stem_count": self.options["stem_count"],
                "quality": self.options["quality"],
                "export_zip": self.options["export_zip"],
                "keep_original": self.options["keep_original"],
                "export_mp3": self.options.get("export_mp3", False),
                "mode": self.options.get("mode", "standard"),
                "dereverb": self.options.get("dereverb", False)
            }
            
            config_json = json.dumps(config)
            
            # Run subprocess
            # Use -u for unbuffered output to capture real-time logs
            cmd = [sys.executable, "-u", "main.py", "--worker", config_json]
            if getattr(sys, 'frozen', False):
                cmd = [sys.executable, "--worker", config_json]
            
            self.progress_updated.emit(filename, 10, "Starting Worker...")
            
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # Force unbuffered output
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            
            self.process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                text=False, # Read bytes to handle \r
                startupinfo=startupinfo,
                bufsize=0, # Unbuffered
                env=env
            )
            
            self.progress_updated.emit(filename, 20, "Separating...")
            
            # Read output in real-time
            buffer = b""
            while True:
                if self.is_cancelled:
                    break
                
                # Read one byte at a time to handle \r and \n
                chunk = self.process.stdout.read(1)
                if not chunk and self.process.poll() is not None:
                    break
                
                if chunk:
                    buffer += chunk
                    
                    # Check for newline or carriage return
                    if chunk in (b'\n', b'\r'):
                        try:
                            line = buffer.decode('utf-8', errors='replace').strip()
                        except:
                            line = ""
                        
                        buffer = b""
                        
                        if line:
                            # Parse Progress (e.g. " 15%|...")
                            if "%" in line and "|" in line:
                                try:
                                    # Extract percentage
                                    parts = line.split('%')[0].split()
                                    if parts:
                                        pct = int(parts[-1])
                                        # Map 0-100% of separation to 20-90% of total progress
                                        total_progress = 20 + int(pct * 0.7)
                                        self.progress_updated.emit(filename, total_progress, f"Separating: {pct}%")
                                except:
                                    pass
                            
                            # User Friendly Logging
                            # Only log significant messages or errors
                            is_progress_bar = "%" in line and "|" in line
                            if not is_progress_bar:
                                logger.info(f"[Worker] {line}")
                                if "Separating" in line:
                                    self.progress_updated.emit(filename, 20, "Separating...")
                                elif "Loading" in line:
                                    self.progress_updated.emit(filename, 10, "Loading Models...")
            
            if self.is_cancelled:
                return

            return_code = self.process.poll()
            if return_code != 0:
                raise Exception(f"Worker failed with code {return_code}")
            
            self.progress_updated.emit(filename, 100, "Done")
            self.finished.emit(filename)
            
        except Exception as e:
            if not self.is_cancelled:
                logger.error(f"Error processing {filename}: {e}")
                self.error_occurred.emit(filename, str(e))

    def terminate(self):
        self.is_cancelled = True
        if self.process:
            try:
                self.process.kill()
            except:
                pass
        # Do NOT call super().terminate() - let the thread exit naturally

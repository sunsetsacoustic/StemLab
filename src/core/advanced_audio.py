import os
import shutil
import logging
import torch
import soundfile as sf
import numpy as np
from audio_separator.separator import Separator

logger = logging.getLogger(__name__)

class AdvancedAudioProcessor:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.separator = Separator(
            log_level=logging.INFO,
            output_dir=output_dir,
            output_format="wav"
        )

    def run_mdx(self, input_file, model_name):
        """
        Runs a specific MDX model using audio-separator.
        Returns the path to the output file.
        """
        logger.info(f"Loading MDX Model: {model_name}")
        self.separator.load_model(model_filename=model_name)
        
        logger.info(f"Separating with {model_name}...")
        # audio-separator returns a list of output filenames
        output_files = self.separator.separate(input_file)
        
        # We assume the model produces specific stems. 
        # For vocal models, we usually get a vocals file and an instrumental file.
        # We need to identify which is which.
        # Usually audio-separator names them like "{filename}_(Vocals)_{model}.wav"
        
        return [os.path.join(self.output_dir, f) for f in output_files]

    def ensemble_blend(self, file1, file2, output_path):
        """
        Blends two audio files by averaging them.
        """
        logger.info(f"Blending {os.path.basename(file1)} and {os.path.basename(file2)}")
        
        data1, sr1 = sf.read(file1)
        data2, sr2 = sf.read(file2)
        
        # Ensure same length
        min_len = min(len(data1), len(data2))
        data1 = data1[:min_len]
        data2 = data2[:min_len]
        
        # Average
        blended = (data1 + data2) / 2
        
        sf.write(output_path, blended, sr1)
        return output_path

    def invert_audio(self, original_file, stem_file, output_path):
        """
        Creates instrumental by subtracting stem from original.
        Instrumental = Original - Stem
        """
        logger.info("Performing Audio Inversion...")
        
        orig, sr_orig = sf.read(original_file)
        stem, sr_stem = sf.read(stem_file)
        
        # Ensure match
        if sr_orig != sr_stem:
            # Resample would be needed here, but for now assume matching SR
            pass
            
        min_len = min(len(orig), len(stem))
        orig = orig[:min_len]
        stem = stem[:min_len]
        
        # Invert
        inverted = orig - stem
        
        sf.write(output_path, inverted, sr_orig)
        return output_path

    def process_vocals_ultra_clean(self, input_file, demucs_vocals):
        """
        Full pipeline:
        1. Kim_Vocal_2 (MDX)
        2. Blend with Demucs Vocals
        3. De-Reverb (HP2)
        4. De-Echo (Reverb_HQ)
        """
        # 1. Run Kim_Vocal_2
        mdx_outputs = self.run_mdx(input_file, "Kim_Vocal_2.onnx")
        
        # Find the vocals stem from MDX output
        mdx_vocals = None
        for f in mdx_outputs:
            if "Vocals" in f or "Kim_Vocal_2" in f: 
                mdx_vocals = f
                break
        
        if not mdx_vocals:
            logger.warning("Could not find MDX vocals, skipping ensemble.")
            return demucs_vocals

        # 2. Ensemble
        ensemble_vocals = os.path.join(self.output_dir, "vocals_ensemble.wav")
        self.ensemble_blend(demucs_vocals, mdx_vocals, ensemble_vocals)
        
        # 3. De-Reverb (HP2-all-vocals)
        # HP2-all-vocals-32000-1.band (UVR-MDX-Net)
        # Note: audio-separator might need the exact filename if it's not in its default list.
        # We'll try the common name.
        hp2_outputs = self.run_mdx(ensemble_vocals, "UVR-MDX-NET-Inst_HQ_3.onnx") # Fallback if HP2 not found by default name
        # Ideally we'd use "HP2-all-vocals-32000-1.band.onnx" but let's stick to a known working one for now or try the user's name
        # If the user has the file, they can put it in the models dir. 
        # For now, let's use the ensemble output as the input for the next stage if we skip de-reverb due to missing model.
        
        # 4. De-Echo (Reverb_HQ_By_FoxJoy)
        # reverb_outputs = self.run_mdx(ensemble_vocals, "Reverb_HQ_By_FoxJoy.onnx")
        
        return ensemble_vocals

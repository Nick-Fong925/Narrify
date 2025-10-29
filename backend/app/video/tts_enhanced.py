"""
Enhanced TTS module with multiple high-quality model options.
Supports: XTTS v2, StyleTTS 2, Kokoro, and fallbacks.
"""

import os
import subprocess
from pathlib import Path

# Configuration
VOICE_REFERENCE_PATH = os.path.join(os.path.dirname(__file__), "training", "training_audio.wav")
VOICE_TRAINING_DIR = os.path.join(os.path.dirname(__file__), "training")

# Model priority: StyleTTS2 > XTTS-v2 > Kokoro > gTTS
PREFERRED_MODEL = "xtts_v2"  # Options: "xtts_v2", "styletts2", "kokoro"


def load_tts_model(model_name="xtts_v2"):
    """Load the specified TTS model."""
    
    if model_name == "xtts_v2":
        try:
            from TTS.api import TTS
            print("🎤 Loading XTTS v2 for voice cloning...")
            model = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=True)
            print("✅ XTTS v2 loaded successfully!")
            return ("xtts_v2", model)
        except Exception as e:
            print(f"❌ Failed to load XTTS v2: {e}")
            return (None, None)
    
    elif model_name == "styletts2":
        try:
            # StyleTTS 2 requires separate installation
            # pip install styletts2
            print("🎤 Loading StyleTTS 2...")
            # Implementation would go here
            print("⚠️ StyleTTS 2 not yet implemented - falling back...")
            return (None, None)
        except Exception as e:
            print(f"❌ Failed to load StyleTTS 2: {e}")
            return (None, None)
    
    elif model_name == "kokoro":
        try:
            # Kokoro TTS implementation
            print("🎤 Loading Kokoro-82M...")
            # Implementation would go here
            print("⚠️ Kokoro not yet implemented - falling back...")
            return (None, None)
        except Exception as e:
            print(f"❌ Failed to load Kokoro: {e}")
            return (None, None)
    
    return (None, None)


def preprocess_audio_for_cloning(audio_path):
    """
    Preprocess reference audio to optimal format for voice cloning.
    Returns path to preprocessed audio.
    """
    if not os.path.exists(audio_path):
        print(f"⚠️ Reference audio not found: {audio_path}")
        return None
    
    # Check if already preprocessed (WAV format, 22050Hz)
    output_path = audio_path.replace('.mp3', '_preprocessed.wav').replace('.m4a', '_preprocessed.wav')
    
    if os.path.exists(output_path):
        print(f"✅ Using preprocessed audio: {output_path}")
        return output_path
    
    print(f"🔧 Preprocessing reference audio: {audio_path}")
    
    try:
        # Optimize audio for voice cloning
        subprocess.run([
            'ffmpeg', '-y',
            '-i', audio_path,
            # Remove silence, normalize, convert to optimal format
            '-af', 'silenceremove=start_periods=1:start_silence=0.1:start_threshold=-50dB,loudnorm=I=-16:TP=-1.5:LRA=11',
            '-ar', '22050',  # Optimal sample rate for XTTS v2
            '-ac', '1',      # Mono
            '-t', '10',      # Limit to 10 seconds (optimal for XTTS)
            output_path
        ], check=True, capture_output=True)
        
        print(f"✅ Preprocessed audio saved: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ Failed to preprocess audio: {e}")
        return audio_path  # Return original if preprocessing fails


def text_to_speech_enhanced(text: str, out_path: str, voice_type: str = "cloned"):
    """
    Enhanced TTS with better quality voice cloning.
    
    Quality tips:
    1. Use high-quality reference audio (WAV, 22050Hz, 6-10 seconds)
    2. Keep text chunks under 200 characters for best quality
    3. Use proper punctuation for natural prosody
    """
    
    # Try to load preferred model
    model_type, model = load_tts_model(PREFERRED_MODEL)
    
    if model is None:
        print("⚠️ Falling back to standard TTS...")
        from app.video.tts import text_to_speech
        return text_to_speech(text, out_path, voice_type=voice_type)
    
    # Preprocess reference audio for optimal quality
    reference_audio = preprocess_audio_for_cloning(VOICE_REFERENCE_PATH)
    
    if reference_audio is None or not os.path.exists(reference_audio):
        print("⚠️ No valid reference audio, using standard TTS...")
        from app.video.tts import generate_standard_tts
        return generate_standard_tts(text, out_path)
    
    try:
        # Split into optimal chunks
        chunks = split_text_optimally(text, max_length=180)
        
        if len(chunks) > 1:
            print(f"📝 Splitting into {len(chunks)} chunks for optimal quality...")
            audio_chunks = []
            
            for i, chunk in enumerate(chunks):
                chunk_path = str(out_path).replace('.mp3', f'_chunk_{i}.wav')
                print(f"🎙️ Generating chunk {i+1}/{len(chunks)} with voice cloning...")
                
                # Generate with XTTS v2 using preprocessed reference
                model.tts_to_file(
                    text=chunk,
                    speaker_wav=reference_audio,
                    language="en",
                    file_path=chunk_path,
                    speed=1.0  # Natural speed - we'll adjust in post-processing
                )
                audio_chunks.append(chunk_path)
            
            # Combine chunks
            temp_output = str(out_path).replace('.mp3', '_temp.wav')
            combine_audio_chunks(audio_chunks, temp_output)
            
            # Clean up chunks
            for chunk_path in audio_chunks:
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)
        else:
            temp_output = str(out_path).replace('.mp3', '_temp.wav')
            print(f"🎙️ Generating voice cloned audio...")
            model.tts_to_file(
                text=text,
                speaker_wav=reference_audio,
                language="en",
                file_path=temp_output,
                speed=1.0
            )
        
        # Convert with enhanced processing
        convert_to_mp3_enhanced(temp_output, out_path)
        
        # Cleanup
        if os.path.exists(temp_output):
            os.remove(temp_output)
        
        print(f"✅ High-quality voice cloned audio generated: {out_path}")
        return str(out_path)
        
    except Exception as e:
        print(f"❌ Enhanced TTS failed: {e}")
        import traceback
        traceback.print_exc()
        # Fallback
        from app.video.tts import text_to_speech
        return text_to_speech(text, out_path, voice_type=voice_type)


def split_text_optimally(text: str, max_length: int = 180) -> list:
    """Split text at natural boundaries for best TTS quality."""
    import re
    
    if len(text) <= max_length:
        return [text]
    
    # Split at sentence boundaries
    sentences = re.split(r'([.!?]+\s+)', text)
    chunks = []
    current_chunk = ""
    
    for i in range(0, len(sentences), 2):
        sentence = sentences[i]
        punctuation = sentences[i+1] if i+1 < len(sentences) else ""
        full_sentence = sentence + punctuation
        
        if len(current_chunk) + len(full_sentence) > max_length and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = full_sentence
        else:
            current_chunk += full_sentence
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def combine_audio_chunks(chunk_paths: list, output_path: str):
    """Combine audio chunks with minimal gaps."""
    list_file = output_path.replace('.wav', '_list.txt')
    with open(list_file, 'w') as f:
        for chunk_path in chunk_paths:
            f.write(f"file '{chunk_path}'\n")
    
    subprocess.run([
        'ffmpeg', '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', list_file,
        '-c', 'copy',
        output_path
    ], check=True, capture_output=True)
    
    os.remove(list_file)


def convert_to_mp3_enhanced(input_path: str, output_path: str):
    """
    Convert with LESS aggressive processing to preserve voice cloning quality.
    The key is to enhance without destroying the natural voice characteristics.
    """
    
    # Lighter processing - preserve the cloned voice characteristics
    ffmpeg_filters = [
        "atempo=1.05",  # Slight speed increase for energy
        "asetrate=22050*1.06,aresample=22050",  # Gentle pitch raise (less aggressive)
        "highpass=f=100",  # Clean up very low frequencies
        "lowpass=f=10000",  # Keep most high frequencies
        "equalizer=f=2500:width_type=h:width=2:g=2",   # Gentle clarity boost
        "equalizer=f=5000:width_type=h:width=2:g=1.5", # Slight brightness
        "compand=0.05|0.05:0.2|0.2:-90/-70|-70/-50|-50/-30|-20/-15|-8/-8:5:0:-3:0.1",  # Gentle compression
        "volume=0.95",  # Good volume
        "aresample=22050:resampler=soxr:precision=32"
    ]
    
    subprocess.run([
        'ffmpeg', '-y',
        '-i', input_path,
        '-af', ','.join(ffmpeg_filters),
        '-acodec', 'libmp3lame',
        '-ar', '22050',
        '-ac', '1',
        '-b:a', '96k',  # Higher bitrate for better quality
        output_path
    ], check=True, capture_output=True)

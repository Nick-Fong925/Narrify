import os
import subprocess
from pathlib import Path
import requests
import json
import gc
import torch
from TTS.api import TTS

# Voice cloning configuration
VOICE_REFERENCE_PATH = os.path.join(os.path.dirname(__file__), "training", "training_audio.mp3")
VOICE_TRAINING_DIR = os.path.join(os.path.dirname(__file__), "training")

def prepare_enhanced_reference_audio():
    """Prepare enhanced reference audio by combining multiple samples if available."""
    training_files = []
    
    # Check for multiple training files
    if os.path.exists(VOICE_TRAINING_DIR):
        for file in os.listdir(VOICE_TRAINING_DIR):
            if file.endswith(('.mp3', '.wav', '.m4a')) and file != 'combined_reference.mp3':
                training_files.append(os.path.join(VOICE_TRAINING_DIR, file))
    
    # If multiple files exist, combine them for better voice cloning
    if len(training_files) > 1:
        combined_path = os.path.join(VOICE_TRAINING_DIR, "combined_reference.mp3")
        print(f"🎯 Combining {len(training_files)} training files for enhanced voice cloning...")
        
        # Create input list for ffmpeg
        input_list = []
        filter_parts = []
        
        for i, file in enumerate(training_files):
            input_list.extend(['-i', file])
            filter_parts.append(f'[{i}:0]')
        
        # Combine with crossfade for smoother transitions
        if len(training_files) == 2:
            filter_complex = f"{filter_parts[0]}{filter_parts[1]}concat=n=2:v=0:a=1[out]"
        else:
            filter_complex = f"{''.join(filter_parts)}concat=n={len(training_files)}:v=0:a=1[out]"
        
        ffmpeg_cmd = [
            'ffmpeg', '-y'
        ] + input_list + [
            '-filter_complex', filter_complex,
            '-map', '[out]',
            '-acodec', 'libmp3lame',
            '-ar', '22050',
            '-ac', '1',
            '-b:a', '128k',
            combined_path
        ]
        
        try:
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Enhanced reference audio created: {combined_path}")
                return combined_path
        except Exception as e:
            print(f"⚠️ Failed to combine training files: {e}")
    
    # Return original reference if combination failed or only one file
    return VOICE_REFERENCE_PATH if os.path.exists(VOICE_REFERENCE_PATH) else None

# Initialize XTTS v2 for voice cloning
try:
    print("🎤 Loading XTTS v2 for voice cloning...")
    tts_model = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=True)
    print("✅ XTTS v2 loaded successfully for voice cloning!")
    
    # Prepare enhanced reference audio
    enhanced_reference = prepare_enhanced_reference_audio()
    if enhanced_reference:
        VOICE_REFERENCE_PATH = enhanced_reference
        print(f"🎯 Using enhanced reference audio: {VOICE_REFERENCE_PATH}")
    
    VOICE_CLONING_AVAILABLE = True
except Exception as e:
    print(f"❌ Failed to load XTTS v2: {e}")
    print("🔄 Falling back to VITS model...")
    VOICE_CLONING_AVAILABLE = False
    try:
        tts_model = TTS(model_name="tts_models/en/ljspeech/vits", progress_bar=True)
        print("✅ Coqui TTS (VITS) loaded successfully!")
    except Exception as e2:
        print(f"❌ Failed to load Coqui TTS VITS: {e2}")
        print("🔄 Trying neural_hmm as fallback...")
        try:
            tts_model = TTS(model_name="tts_models/en/ljspeech/neural_hmm", progress_bar=True)
            print("✅ Coqui TTS (neural_hmm) loaded successfully!")
        except Exception as e3:
            print(f"❌ Failed to load any Coqui TTS model: {e3}")
            print("🔄 Will fall back to gTTS for audio generation")
            tts_model = None


def text_to_speech(text: str, out_path: str, lang: str = "en", slow: bool = False, voice_type: str = "male"):
    """
    Generate an mp3 audio file from text using XTTS v2 voice cloning or fallback TTS.
    
    Args:
        text: Text to convert to speech (original text)
        out_path: Path where to save the audio file
        lang: Language (kept for compatibility)
        slow: Slow speech (kept for compatibility)
        voice_type: Voice type preference (kept for compatibility)
    
    Returns:
        str: Path to the generated audio file
    """
    try:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        
        # Preprocess text for TTS (expand contractions, handle Reddit patterns)
        from app.utils.text_cleaning import prepare_text_for_tts
        clean_text = prepare_text_for_tts(text)
        
        # Generate speech using XTTS v2 voice cloning or fallback
        if tts_model is None:
            raise Exception("No TTS model loaded")
        
        # Check if voice cloning is available and reference audio exists
        if VOICE_CLONING_AVAILABLE and os.path.exists(VOICE_REFERENCE_PATH):
            return generate_voice_cloned_speech(clean_text, out_path)
        else:
            print("🔄 Voice cloning not available, using standard TTS...")
            return generate_standard_tts(clean_text, out_path)
        
    except Exception as e:
        print(f"❌ Error in TTS generation: {e}")
        import traceback
        traceback.print_exc()
        # Fail hard instead of falling back to gTTS
        raise Exception(f"TTS generation failed: {e}")


def cleanup_tts_memory():
    """Free up memory after TTS generation by forcing garbage collection"""
    try:
        # Clear CUDA cache if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        # Force garbage collection to free up RAM
        gc.collect()
        
        print("🗑️ TTS memory cleaned up")
    except Exception as e:
        print(f"⚠️ Warning: Could not cleanup TTS memory: {e}")


def generate_voice_cloned_speech(text: str, out_path: str) -> str:
    """Generate speech using XTTS v2 voice cloning with reference audio."""
    try:
        print(f"🎭 Generating voice cloned speech using: {VOICE_REFERENCE_PATH}")
        print(f"   Voice cloning available: {VOICE_CLONING_AVAILABLE}")
        print(f"   TTS model: {tts_model.model_name if tts_model else 'None'}")
        
        # Split long text into smaller chunks for better quality and timing control
        # Shorter chunks = better prosody, more natural speech, higher quality
        # Sweet spot for XTTS v2: 80-100 characters per chunk
        max_chunk_length = 90  # Reduced from 120 for even better quality
        if len(text) > max_chunk_length:
            print(f"🔄 Text is long ({len(text)} chars), splitting into chunks...")
            chunks = split_text_into_chunks(text, max_chunk_length)
            audio_chunks = []
            
            for i, chunk in enumerate(chunks):
                chunk_path = str(out_path).replace('.mp3', f'_chunk_{i}.wav')
                print(f"🎙️ Generating cloned voice chunk {i+1}/{len(chunks)}...")
                
                # Use XTTS v2 voice cloning with careful timing
                tts_model.tts_to_file(
                    text=chunk,
                    speaker_wav=VOICE_REFERENCE_PATH,
                    language="en",
                    file_path=chunk_path
                )
                audio_chunks.append(chunk_path)
            
            # Combine chunks with minimal gaps for timing accuracy
            temp_output = str(out_path).replace('.mp3', '_temp.wav')
            combine_audio_chunks_precise(audio_chunks, temp_output)
            
            # Clean up chunk files
            for chunk_path in audio_chunks:
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)
        else:
            # Create temporary path for XTTS output
            temp_output = str(out_path).replace('.mp3', '_temp.wav')
            
            print(f"� Generating cloned voice...")
            tts_model.tts_to_file(
                text=text,
                speaker_wav=VOICE_REFERENCE_PATH,
                language="en", 
                file_path=temp_output
            )
        
        # Convert WAV to MP3 with enhanced voice processing for cloned voice
        print(f"🔧 Converting cloned voice to MP3 with processing...")
        convert_to_mp3_with_processing(temp_output, out_path, voice_type="cloned")
        
        # Clean up temporary file
        if os.path.exists(temp_output):
            os.remove(temp_output)
        
        print(f"✅ Voice cloned audio generated: {out_path}")
        return str(out_path)
        
    except Exception as e:
        print(f"❌ Voice cloning failed: {e}")
        import traceback
        traceback.print_exc()
        # Don't fall back to gTTS - fail hard so we know there's a problem
        raise Exception(f"Voice cloning failed and gTTS fallback is disabled: {e}")


def generate_standard_tts(text: str, out_path: str) -> str:
    """Generate speech using standard TTS models (VITS, etc.)."""
    try:
        # Check if model requires speaker parameter
        model_name = tts_model.model_name if hasattr(tts_model, 'model_name') else ""
        requires_speaker = 'multi' in model_name.lower() or tts_model.is_multi_speaker
        
        # Get available speakers if needed
        speaker = None
        if requires_speaker:
            speakers = tts_model.speakers if hasattr(tts_model, 'speakers') else []
            if speakers:
                # Use first speaker or a default one
                speaker = speakers[0] if len(speakers) > 0 else None
                print(f"🎤 Using speaker: {speaker}")
        
        # Split long text into smaller chunks to avoid decoder issues and improve quality
        max_chunk_length = 110  # Reduced from 150 for better quality
        if len(text) > max_chunk_length:
            print(f"🔄 Text is long ({len(text)} chars), splitting into chunks...")
            chunks = split_text_into_chunks(text, max_chunk_length)
            audio_chunks = []
            
            for i, chunk in enumerate(chunks):
                chunk_path = str(out_path).replace('.mp3', f'_chunk_{i}.wav')
                print(f"🎙️ Generating chunk {i+1}/{len(chunks)}...")
                if requires_speaker and speaker:
                    tts_model.tts_to_file(text=chunk, file_path=chunk_path, speaker=speaker)
                else:
                    tts_model.tts_to_file(text=chunk, file_path=chunk_path)
                audio_chunks.append(chunk_path)
            
            # Combine chunks
            temp_output = str(out_path).replace('.mp3', '_temp.wav')
            combine_audio_chunks(audio_chunks, temp_output)
            
            # Clean up chunk files
            for chunk_path in audio_chunks:
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)
        else:
            # Create temporary path for TTS output
            temp_output = str(out_path).replace('.mp3', '_temp.wav')
            
            print(f"🎙️ Generating speech with standard TTS...")
            if requires_speaker and speaker:
                tts_model.tts_to_file(text=text, file_path=temp_output, speaker=speaker)
            else:
                tts_model.tts_to_file(text=text, file_path=temp_output)
        
        # Convert WAV to MP3 with processing
        convert_to_mp3_with_processing(temp_output, out_path, voice_type="standard")
        
        # Clean up temporary file
        if os.path.exists(temp_output):
            os.remove(temp_output)
        
        print(f"✅ Standard TTS audio generated: {out_path}")
        return str(out_path)
        
    except Exception as e:
        print(f"❌ Standard TTS failed: {e}")
        raise


def convert_to_mp3_with_processing(input_path: str, output_path: str, voice_type: str = "standard"):
    """Convert WAV to MP3 with appropriate audio processing based on voice type."""
    from app.video.subtitle_config import AUDIO_ENHANCEMENT_LEVEL, AUDIO_BITRATE
    
    # Base filters for cleanup and quality
    base_filters = [
        "highpass=f=75",  # Remove deep rumble
        "lowpass=f=12000",  # Remove harsh high frequencies
        # Denoise filter to reduce background noise and scratchiness
        "afftdn=nf=-20:tn=1",  # Adaptive noise reduction
    ]
    
    # Enhancement filters based on level
    if AUDIO_ENHANCEMENT_LEVEL == "extreme":
        clarity_filters = [
            "atempo=1.04",  # Slight speed for energy
            # Multi-band EQ for clarity with depth
            "equalizer=f=80:width_type=h:width=1:g=-3",      # Reduce rumble
            "equalizer=f=150:width_type=h:width=2:g=3",      # Add warmth/body
            "equalizer=f=400:width_type=h:width=2:g=2",      # Vocal foundation
            "equalizer=f=1000:width_type=h:width=2:g=3",     # Vocal presence
            "equalizer=f=2500:width_type=h:width=1500:g=4",  # Clarity boost
            "equalizer=f=4000:width_type=h:width=2000:g=3",  # Consonant definition
            "equalizer=f=6000:width_type=h:width=2000:g=2",  # Brightness
            # Aggressive compression for loudness and consistency
            "acompressor=threshold=-24dB:ratio=6:attack=3:release=150:makeup=12dB",
            # Bass enhancement for depth and warmth
            "bass=g=4:f=100:w=0.6",
            # Harmonic exciter for presence (gentle to avoid harshness)
            "aexciter=level_in=1:level_out=1:amount=1.8:drive=2.5:blend=0:freq=3000:ceil=10000:listen=0",
            # Final limiter to prevent clipping while maximizing volume
            "alimiter=limit=0.98:attack=5:release=50",
            # Strong volume boost
            "volume=2.0",
        ]
    elif AUDIO_ENHANCEMENT_LEVEL == "high":
        clarity_filters = [
            "atempo=1.02",  # Minimal speed adjustment
            # Balanced EQ with depth and warmth
            "equalizer=f=100:width_type=h:width=2:g=-2",     # Reduce mud
            "equalizer=f=200:width_type=h:width=2:g=2.5",    # Add warmth
            "equalizer=f=800:width_type=h:width=2:g=2",      # Body
            "equalizer=f=1500:width_type=h:width=2:g=3",     # Vocal presence
            "equalizer=f=3000:width_type=h:width=2000:g=3",  # Clarity
            "equalizer=f=5000:width_type=h:width=2000:g=2",  # Brightness
            # Strong compression for loudness and consistency
            "acompressor=threshold=-22dB:ratio=5:attack=3:release=150:makeup=10dB",
            # Bass boost for depth and fullness
            "bass=g=3:f=100:w=0.6",
            # Gentle harmonic exciter for presence without harshness
            "aexciter=level_in=1:level_out=1:amount=1.5:drive=2:blend=0:freq=3000:ceil=10000:listen=0",
            # Limiter to prevent clipping
            "alimiter=limit=0.98:attack=5:release=50",
            # Volume boost
            "volume=1.8",
        ]
    elif AUDIO_ENHANCEMENT_LEVEL == "medium":
        clarity_filters = [
            # Natural, cleaner processing
            "equalizer=f=150:width_type=h:width=2:g=2",      # Warmth
            "equalizer=f=1500:width_type=h:width=2:g=2",     # Vocal presence
            "equalizer=f=3000:width_type=h:width=2:g=2",     # Clarity
            "equalizer=f=5000:width_type=h:width=2:g=1.5",   # Brightness
            # Moderate compression for volume
            "acompressor=threshold=-24dB:ratio=4:attack=5:release=200:makeup=8dB",
            # Subtle bass for depth
            "bass=g=2:f=100:w=0.5",
            # Limiter
            "alimiter=limit=0.98:attack=5:release=50",
            "volume=1.5",
        ]
    elif AUDIO_ENHANCEMENT_LEVEL == "low":
        clarity_filters = [
            # Minimal processing - just louder and clearer
            "equalizer=f=2000:width_type=h:width=2:g=1.5",   # Clarity
            "acompressor=threshold=-26dB:ratio=3:attack=10:release=250:makeup=6dB",
            "alimiter=limit=0.98:attack=5:release=50",
            "volume=1.3",
        ]
    else:  # "off"
        clarity_filters = [
            # Just normalize volume with gentle compression
            "acompressor=threshold=-28dB:ratio=2:attack=10:release=250:makeup=4dB",
            "alimiter=limit=0.98:attack=5:release=50",
            "volume=1.2"
        ]
    
    # Combine all filters
    ffmpeg_filters = base_filters + clarity_filters + [
        "aresample=22050:resampler=soxr:precision=32",  # High quality resampling
        "alimiter=limit=0.99:attack=3:release=40"  # Final safety limiter
    ]
    
    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-i', input_path,
        '-af', ','.join(ffmpeg_filters),
        '-acodec', 'libmp3lame',
        '-ar', '22050',
        '-ac', '1',
        '-b:a', '192k',  # Higher bitrate for better quality
        str(output_path)
    ]
    
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"FFmpeg conversion failed: {result.stderr}")


def split_text_into_chunks(text: str, max_length: int = 100) -> list:
    """
    Split text into optimal chunks for TTS quality.
    Prioritizes natural speech boundaries: sentences > clauses > phrases.
    """
    import re
    
    # First split by sentences (periods, exclamation, question marks)
    sentences = re.split(r'([.!?]+)', text)
    
    chunks = []
    current_chunk = ""
    
    for i in range(0, len(sentences), 2):
        sentence = sentences[i].strip()
        punctuation = sentences[i+1] if i+1 < len(sentences) else '.'
        
        if not sentence:
            continue
        
        full_sentence = sentence + punctuation
        
        # If sentence is short enough, use as is
        if len(full_sentence) <= max_length:
            if current_chunk and len(current_chunk) + len(full_sentence) <= max_length:
                # Combine with previous if still under limit
                current_chunk += ' ' + full_sentence
            else:
                # Save previous chunk and start new one
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = full_sentence
        else:
            # Sentence too long - split at natural boundaries (commas, conjunctions)
            # Save any pending chunk first
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            
            # Split long sentence at commas, conjunctions, etc.
            sub_chunks = split_at_natural_boundaries(sentence, max_length)
            
            # Add punctuation back to last sub-chunk
            if sub_chunks:
                sub_chunks[-1] += punctuation
                chunks.extend(sub_chunks)
    
    # Add final chunk
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def split_at_natural_boundaries(text: str, max_length: int) -> list:
    """Split long text at natural speech boundaries (commas, conjunctions)."""
    import re
    
    # Split at commas, semicolons, dashes, conjunctions
    # Keep the delimiter with the preceding text
    parts = re.split(r'(\s+(?:and|but|or|so|yet|because|since|while|though|although|if|when|where|which|who)\s+|,\s*|;\s*|\s+-\s+)', text)
    
    chunks = []
    current = ""
    
    for part in parts:
        if not part or part.isspace():
            continue
            
        if len(current) + len(part) <= max_length:
            current += part
        else:
            if current:
                chunks.append(current.strip())
            current = part.strip()
    
    if current:
        chunks.append(current.strip())
    
    return chunks


def combine_audio_chunks_precise(chunk_paths: list, output_path: str):
    """Combine multiple audio files with minimal gaps for precise timing."""
    # Create a text file listing all chunks for ffmpeg
    list_file = output_path.replace('.wav', '_list.txt')
    with open(list_file, 'w') as f:
        for chunk_path in chunk_paths:
            f.write(f"file '{chunk_path}'\n")
    
    # Use ffmpeg to concatenate with minimal processing for timing accuracy
    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', list_file,
        '-acodec', 'pcm_s16le',  # Preserve quality
        '-ar', '22050',  # Match sample rate
        output_path
    ]
    
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Audio concatenation failed: {result.stderr}")
    
    # Clean up list file
    if os.path.exists(list_file):
        os.remove(list_file)


def combine_audio_chunks(chunk_paths: list, output_path: str):
    """Combine multiple audio files into one with smooth transitions."""
    # Create a text file listing all chunks for ffmpeg
    list_file = output_path.replace('.wav', '_list.txt')
    with open(list_file, 'w') as f:
        for chunk_path in chunk_paths:
            f.write(f"file '{chunk_path}'\n")
    
    # Use ffmpeg to concatenate with crossfade for smoother transitions
    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', list_file,
        # Add slight crossfade between chunks and normalize audio
        '-af', 'aresample=22050,volume=0.8,dynaudnorm=p=0.9',
        '-c:a', 'pcm_s16le',
        output_path
    ]
    
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Audio concatenation failed: {result.stderr}")
    
    # Clean up list file
    if os.path.exists(list_file):
        os.remove(list_file)


def fallback_gtts(text: str, output_path: str, voice_type: str = 'male'):
    """
    Fallback to gTTS if Coqui TTS fails.
    """
    try:
        from gtts import gTTS
        from app.utils.text_cleaning import prepare_text_for_tts
        
        # Preprocess text
        clean_text = prepare_text_for_tts(text)
        
        # Create TTS object with Australian English (sounds more male)
        tts = gTTS(text=clean_text, lang='en', tld='com.au', slow=False)
        
        # Create temporary path
        temp_output = output_path.replace('.mp3', '_temp.mp3')
        tts.save(temp_output)
        
        # Process with ffmpeg for consistent output
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-i', temp_output,
            '-af', 'atempo=1.12',
            '-acodec', 'libmp3lame',
            '-ar', '24000',
            '-ac', '1',
            '-b:a', '32k',
            output_path
        ]
        
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"FFmpeg processing failed: {result.stderr}")
        
        # Clean up
        if os.path.exists(temp_output):
            os.remove(temp_output)
        
        print(f"✅ Fallback gTTS audio generated: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ Fallback gTTS also failed: {e}")
        raise

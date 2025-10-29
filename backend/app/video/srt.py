from pathlib import Path
from typing import List
import subprocess
import re
import gc
import torch
import whisper
from app.video.subtitle_config import (
    WORDS_PER_SUBTITLE_MIN,
    WORDS_PER_SUBTITLE_MAX,
    WHISPER_MODEL,
    BREAK_PUNCTUATION,
    VIDEO_SPEED_MULTIPLIER
)


def generate_srt_from_audio_and_text(audio_path, text, speed_multiplier=1.0):
    """
    Generate SRT subtitles with accurate word-level timing using Whisper.
    
    Args:
        audio_path: Path to audio file
        text: Preprocessed text (with expanded contractions) that matches what's spoken in audio
        speed_multiplier: Video speed multiplier - NOT USED, kept for compatibility
                         Subtitles are burned in before speed-up, so they speed up naturally
    
    Note: Text should be the SAME preprocessed text used for TTS generation.
          This ensures perfect alignment between Whisper timing and subtitle text.
          Example: If audio says "he is", text should be "he is" (not "he's")
    """
    try:
        print("🎯 Generating word-level timestamps with Whisper...")
        
        # Load Whisper model
        model = whisper.load_model(WHISPER_MODEL)
        
        # Transcribe with word-level timestamps
        result = model.transcribe(
            audio_path,
            word_timestamps=True,
            language="en"
        )
        
        # Free up Whisper model memory immediately
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
        print("🗑️ Whisper model memory freed")
        
        # Extract word-level timing from Whisper
        whisper_words = []
        for segment in result.get("segments", []):
            for word_info in segment.get("words", []):
                whisper_words.append({
                    "word": word_info["word"].strip(),
                    "start": word_info["start"],
                    "end": word_info["end"]
                })
        
        print(f"📊 Whisper detected {len(whisper_words)} words in audio")
        
        # Split text into words (this should match Whisper 1:1 since text is preprocessed)
        text_words = text.strip().split()
        print(f"📝 Subtitle text has {len(text_words)} words")
        
        if not text_words:
            return ""
        
        # Map text words to Whisper timings
        # Since text is preprocessed to match audio, this should be 1:1 or very close
        word_timings = []
        
        for i, text_word in enumerate(text_words):
            if i < len(whisper_words):
                # Direct 1:1 mapping - text matches audio
                word_timings.append({
                    "word": text_word,  # Use subtitle text word
                    "start": whisper_words[i]["start"],
                    "end": whisper_words[i]["end"]
                })
            else:
                # If we run out of Whisper timings, estimate from last known timing
                print(f"⚠️ Warning: Ran out of timing data at word {i+1}/{len(text_words)}")
                if word_timings:
                    last_end = word_timings[-1]["end"]
                    word_timings.append({
                        "word": text_word,
                        "start": last_end + 0.1,
                        "end": last_end + 0.6  # Estimate ~0.5s per word
                    })
                else:
                    break
        
        print(f"✅ Mapped {len(word_timings)} words with timing")
        
        # Group words into phrases based on configuration
        print(f"📦 Grouping words into {WORDS_PER_SUBTITLE_MIN}-{WORDS_PER_SUBTITLE_MAX} word phrases...")
        srt_content = []
        phrase_num = 1
        i = 0
        
        while i < len(word_timings):
            # Collect words for this phrase
            phrase_words = []
            phrase_start = word_timings[i]["start"]
            phrase_end = word_timings[i]["end"]
            
            words_in_phrase = 0
            
            while i < len(word_timings) and words_in_phrase < WORDS_PER_SUBTITLE_MAX:
                word_data = word_timings[i]
                phrase_words.append(word_data["word"])
                phrase_end = word_data["end"]
                words_in_phrase += 1
                i += 1
                
                # Break at punctuation if we have at least min_words
                if words_in_phrase >= WORDS_PER_SUBTITLE_MIN:
                    if word_data["word"][-1] in BREAK_PUNCTUATION:
                        break
            
            # Create phrase subtitle
            phrase_text = " ".join(phrase_words)
            start_timestamp = format_timestamp(phrase_start)
            end_timestamp = format_timestamp(phrase_end)
            
            srt_content.append(f"{phrase_num}")
            srt_content.append(f"{start_timestamp} --> {end_timestamp}")
            srt_content.append(phrase_text)
            srt_content.append("")  # Empty line between entries
            
            phrase_num += 1
        
        print(f"✅ Generated {phrase_num - 1} subtitle phrases from {len(word_timings)} words")
        return "\n".join(srt_content)
        
    except Exception as e:
        print(f"❌ Error generating timed subtitles: {e}")
        print("🔄 Falling back to estimation method...")
        return generate_srt_fallback(text)


def generate_srt_fallback(text):
    """
    Fallback SRT generation using estimation (used if Whisper fails).
    """
    words = text.strip().split()
    if not words:
        return ""
    
    # Simple estimation: 0.6 seconds per word
    word_duration = 0.6
    
    srt_content = []
    current_time = 0.0
    
    for i, word in enumerate(words):
        start_time = current_time
        end_time = current_time + word_duration
        
        start_timestamp = format_timestamp(start_time)
        end_timestamp = format_timestamp(end_time)
        
        # Add SRT entry
        srt_content.append(f"{i + 1}")
        srt_content.append(f"{start_timestamp} --> {end_timestamp}")
        srt_content.append(word)
        srt_content.append("")  # Empty line between entries
        
        current_time = end_time
    
    return "\n".join(srt_content)


def format_timestamp(seconds):
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    """Generate SRT with perfect timing based on actual audio duration"""
    # Get actual audio duration
    total_duration = get_audio_duration(audio_file)
    
    # Split text into words
    words = text.split()
    
    if not words:
        return ""
    
    # Calculate timing weights for each word
    word_weights = [classify_word_timing_weight(word) for word in words]
    total_weight = sum(word_weights)
    
    # Distribute time proportionally based on weights
    srt_content = ""
    current_time = 0.0
    
    for i, (word, weight) in enumerate(zip(words, word_weights), 1):
        # Calculate duration for this word
        word_duration = (weight / total_weight) * total_duration
        
        # Ensure minimum duration for readability
        word_duration = max(0.25, word_duration)
        
        # Calculate end time
        end_time = current_time + word_duration
        
        # Format timestamps
        start_timestamp = format_srt_time(current_time)
        end_timestamp = format_srt_time(end_time)
        
        # Create SRT entry
        srt_content += f"{i}\n{start_timestamp} --> {end_timestamp}\n{word}\n\n"
        
        # Update current time (add small gap between words)
        current_time = end_time + 0.05  # 50ms gap between words
    
    return srt_content


def format_srt_time(seconds: float) -> str:
    """Format time in SRT format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def chunk_text_to_srt(text: str, out_srt: str, words_per_caption: int = 1, speed_multiplier: float = 1.1):
    """Legacy function - kept for backward compatibility but now uses audio-based timing"""
    # This function is now a wrapper - actual timing should be done with audio file
    # For backward compatibility, we'll use the old method as fallback
    words = text.split()
    chunks = [" ".join(words[i:i+words_per_caption]) for i in range(0, len(words), words_per_caption)]
    Path(out_srt).parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_srt, "w") as fh:
        start = 0.0
        wps = 2.15 * speed_multiplier
        
        for idx, chunk in enumerate(chunks, start=1):
            if words_per_caption == 1:
                word_length = len(chunk.strip())
                base_duration = max(0.2, word_length * 0.05)
                if word_length <= 3:
                    base_duration = max(0.2, base_duration)
                duration = base_duration + (len(chunk.split()) - 0.5) * 0.3
                gap = 0.0005
            else:
                base_duration = len(chunk.split()) / wps
                duration = max(1.2, base_duration)
                gap = 0.0005
            
            end = start + duration
            
            def fmt(t):
                h = int(t // 3600)
                m = int((t % 3600) // 60)
                s = int(t % 60)
                ms = int((t - int(t)) * 1000)
                return f"{h:02}:{m:02}:{s:02},{ms:03}"
            
            fh.write(f"{idx}\n")
            fh.write(f"{fmt(start)} --> {fmt(end)}\n")
            fh.write(chunk + "\n\n")
            start = end + gap
    
    return out_srt

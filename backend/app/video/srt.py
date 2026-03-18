import gc
import torch
from faster_whisper import WhisperModel
from app.config import settings

# Module-level Whisper singleton — loaded once, reused across all videos.
_whisper_model = None


def _ensure_whisper_loaded():
    """Load Whisper model on first use; subsequent calls are no-ops."""
    global _whisper_model
    if _whisper_model is not None:
        return
    print(f"Loading Whisper {settings.video.whisper_model} on {settings.video.whisper_device}...")
    _whisper_model = WhisperModel(settings.video.whisper_model, device=settings.video.whisper_device, compute_type=settings.video.whisper_compute_type)
    print("Whisper ready.")


def cleanup_whisper_memory():
    """Release the Whisper singleton and free GPU cache. Call at process shutdown."""
    global _whisper_model
    _whisper_model = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()
    print("Whisper memory cleaned up.")


def generate_srt_from_audio_and_text(audio_path, text, speed_multiplier=1.0):
    """
    Generate SRT subtitles with accurate word-level timing using faster-whisper.

    Args:
        audio_path: Path to audio file
        text: Preprocessed text that matches what's spoken in the audio
        speed_multiplier: NOT USED — subtitles are burned in before speed-up
    """
    try:
        print("[whisper] Generating word-level timestamps with faster-whisper...")

        _ensure_whisper_loaded()

        # transcribe() is a lazy generator — must be fully consumed before proceeding
        segments, _ = _whisper_model.transcribe(
            audio_path,
            word_timestamps=True,
            language="en",
            initial_prompt=text,
        )

        whisper_words = []
        for segment in segments:
            for word in segment.words:
                whisper_words.append({
                    "word": word.word.strip(),
                    "start": word.start,
                    "end": word.end,
                })

        print(f"Stats: Whisper detected {len(whisper_words)} words in audio")

        if not whisper_words:
            return generate_srt_fallback(text)

        # Use Whisper's own words as both text and timing source.
        # No mapping → no index drift, ever.
        word_timings = [
            {"word": w["word"], "start": w["start"], "end": w["end"]}
            for w in whisper_words
        ]
        print(f"Using {len(word_timings)} Whisper words directly (no index mapping)")

        # Write one entry per word — timestamps scaled to output time (after audio speed-up)
        # e.g. word at t=10s with speed=1.8x → subtitle at t=5.56s on the 1x video
        print(f"Writing {len(word_timings)} word-level SRT entries (scaled by 1/{speed_multiplier})...")
        srt_content = []
        for i, word_data in enumerate(word_timings):
            srt_content.append(f"{i + 1}")
            srt_content.append(f"{format_timestamp(word_data['start'] / speed_multiplier)} --> {format_timestamp(word_data['end'] / speed_multiplier)}")
            srt_content.append(word_data["word"])
            srt_content.append("")

        print(f"Generated {len(word_timings)} word-level subtitle entries")
        return "\n".join(srt_content)

    except Exception as e:
        print(f"Error generating timed subtitles: {e}")
        print("Falling back to estimation method...")
        return generate_srt_fallback(text)


def generate_srt_fallback(text):
    """
    Fallback SRT generation using estimation (used if Whisper fails).
    """
    words = text.strip().split()
    if not words:
        return ""

    # Estimation based on ~2.5 words/second (natural Kokoro pace at KOKORO_SPEED=1.0)
    word_duration = 0.4

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

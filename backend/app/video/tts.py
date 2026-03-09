import os
import re
import subprocess
from pathlib import Path
import gc
import torch
import numpy as np
import soundfile as sf
from app.config import settings

# Lazy-loaded Kokoro pipeline — nothing loads at import time
_pipeline = None

_EMOTION_TAG_RE = re.compile(r"<[a-z]+>")
_SILENCE_SAMPLES = 7200  # 0.3 s of silence at 24000 Hz


def _ensure_loaded():
    """Initialize Kokoro TTS pipeline on first use."""
    global _pipeline
    if _pipeline is not None:
        return
    from kokoro import KPipeline
    print("Loading Kokoro TTS model...")
    _pipeline = KPipeline(lang_code='a')  # 'a' = American English
    print("Kokoro TTS ready.")


def _chunk_to_audio(chunk: str) -> np.ndarray:
    """Convert one chunk to float32 audio at 24 kHz, replacing emotion tags with silence."""
    # Split on emotion tags; non-tag parts get narrated, tags become silence
    parts = _EMOTION_TAG_RE.split(chunk)
    tags = _EMOTION_TAG_RE.findall(chunk)

    segments = []
    for i, part in enumerate(parts):
        part = part.strip()
        if part:
            audio_parts = []
            for _, _, audio in _pipeline(part, voice=settings.video.kokoro_voice, speed=settings.video.kokoro_speed):
                audio_parts.append(audio)
            if audio_parts:
                segments.append(np.concatenate(audio_parts))
        if i < len(tags):
            # Insert silence where the emotion tag was
            segments.append(np.zeros(_SILENCE_SAMPLES, dtype=np.float32))

    return np.concatenate(segments) if segments else np.zeros(0, dtype=np.float32)


def text_to_speech(text: str, output_path: str, chunks: list = None) -> str:
    """
    Generate an MP3 audio file from text using Kokoro TTS (local model).

    Args:
        text: Raw story text (unused; chunks is used directly)
        output_path: Output MP3 path
        chunks: LLM-generated TTS chunks with optional emotion tags (required)

    Returns:
        str: Path to the generated MP3
    """
    if chunks is None:
        raise ValueError("chunks is required — run prepare_story_with_llm first.")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    _ensure_loaded()

    print(f"Generating {len(chunks)} chunks with Kokoro...")
    audio_segments = []
    for i, chunk in enumerate(chunks, 1):
        print(f"  Chunk {i}/{len(chunks)}...")
        audio_segments.append(_chunk_to_audio(chunk))

    if not audio_segments:
        raise RuntimeError("Kokoro produced no audio output.")

    full_audio = np.concatenate(audio_segments)

    # Write combined audio as WAV, then post-process to MP3
    temp_wav = str(output_path).replace('.mp3', '_temp.wav')
    sf.write(temp_wav, full_audio, settings.video.kokoro_sample_rate)
    try:
        convert_to_mp3_with_processing(temp_wav, output_path)
    finally:
        if os.path.exists(temp_wav):
            os.remove(temp_wav)

    print(f"Audio generated: {output_path}")
    return str(output_path)


def cleanup_tts_memory():
    """Release Kokoro TTS pipeline and clear any GPU cache."""
    global _pipeline
    _pipeline = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()
    print("TTS memory cleaned up.")


def convert_to_mp3_with_processing(input_path: str, output_path: str):
    """Convert WAV to MP3 with ffmpeg audio enhancement chain."""
    base_filters = [
        "highpass=f=50",
    ]

    if settings.video.audio_enhancement_level == "extreme":
        clarity_filters = [
            "equalizer=f=2500:width_type=h:width=1500:g=4",
            "equalizer=f=4000:width_type=h:width=2000:g=3",
            "equalizer=f=6000:width_type=h:width=2000:g=2",
            "acompressor=threshold=-24dB:ratio=3:attack=15:release=250:makeup=8dB",
            "volume=1.5",
        ]
    elif settings.video.audio_enhancement_level == "high":
        clarity_filters = [
            "atempo=1.02",
            "equalizer=f=100:width_type=h:width=2:g=-2",
            "equalizer=f=200:width_type=h:width=2:g=2.5",
            "equalizer=f=800:width_type=h:width=2:g=2",
            "equalizer=f=1500:width_type=h:width=2:g=3",
            "equalizer=f=3000:width_type=h:width=2000:g=3",
            "equalizer=f=5000:width_type=h:width=2000:g=2",
            "acompressor=threshold=-22dB:ratio=5:attack=3:release=150:makeup=10dB",
            "bass=g=3:f=100:w=0.6",
            "aexciter=level_in=1:level_out=1:amount=1.5:drive=2:blend=0:freq=3000:ceil=10000:listen=0",
            "alimiter=limit=0.98:attack=5:release=50",
            "volume=1.8",
        ]
    elif settings.video.audio_enhancement_level == "medium":
        clarity_filters = [
            "equalizer=f=150:width_type=h:width=2:g=2",
            "equalizer=f=1500:width_type=h:width=2:g=2",
            "equalizer=f=3000:width_type=h:width=2:g=2",
            "equalizer=f=5000:width_type=h:width=2:g=1.5",
            "acompressor=threshold=-24dB:ratio=4:attack=5:release=200:makeup=8dB",
            "bass=g=2:f=100:w=0.5",
            "alimiter=limit=0.98:attack=5:release=50",
            "volume=1.5",
        ]
    elif settings.video.audio_enhancement_level == "low":
        clarity_filters = [
            "equalizer=f=2000:width_type=h:width=2:g=1.5",
            "acompressor=threshold=-26dB:ratio=3:attack=10:release=250:makeup=6dB",
            "alimiter=limit=0.98:attack=5:release=50",
            "volume=1.3",
        ]
    else:  # "off"
        clarity_filters = [
            "acompressor=threshold=-28dB:ratio=2:attack=10:release=250:makeup=4dB",
            "alimiter=limit=0.98:attack=5:release=50",
            "volume=1.2",
        ]

    ffmpeg_filters = base_filters + clarity_filters + [
        "alimiter=limit=0.99:attack=15:release=80",
    ]

    cmd = [
        'ffmpeg', '-y',
        '-i', input_path,
        '-af', ','.join(ffmpeg_filters),
        '-acodec', 'libmp3lame',
        '-ar', '22050',
        '-ac', '1',
        '-b:a', settings.video.audio_bitrate,
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"FFmpeg audio conversion failed: {result.stderr}")

#!/usr/bin/env python3
"""
TTS quality test — no database, no LLM.

Drives 3 hardcoded horror story chunks straight through the full pipeline:
  chunks → TTS audio → Whisper subtitle alignment → video

Use this to verify audio quality, subtitle sync, pacing, and voice expressiveness
after changing TTS/audio parameters in subtitle_config.py.

Run from the backend/ directory:
    python -m tests.test_tts_quality
"""

import sys
import os
import uuid
from pathlib import Path

# Resolve backend/ as the package root
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.video.tts import text_to_speech, cleanup_tts_memory
from app.video.srt import generate_srt_from_audio_and_text
from app.video.ffmpeg_utils import merge_audio_with_video, burn_text_overlay, get_video_duration
from app.video.subtitle_config import VIDEO_SPEED_MULTIPLIER
from app.video.generator import OUT_DIR, BASE_VIDEOS

# ---------------------------------------------------------------------------
# Test content — 3 chunks, ~2 sentences each
# Emotion tags from the Orpheus spec are embedded at dramatic moments.
# The cleaned_text must match chunks joined by single spaces, minus emotion tags.
# ---------------------------------------------------------------------------

CHUNKS = [
    "The door at the end of the hallway had always been locked. Tonight it stood wide open. <gasp>",
    "I walked inside and found every mirror in the room covered with black cloth. Something whispered my name from behind the largest one.",
    "I ran. <sob> But when I reached the stairs I realized the house had no front door anymore.",
]

# cleaned_text = chunks joined, emotion tags stripped — this is what Whisper aligns against
import re

def _strip_emotion_tags(text: str) -> str:
    return re.sub(r"<[a-z]+>", "", text).strip()

CLEANED_TEXT = " ".join(_strip_emotion_tags(c) for c in CHUNKS)

STORY_TITLE = "The Open Door"

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def main():
    job_id = f"tts_quality_{uuid.uuid4().hex[:8]}"
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Clear all files in the generated_videos folder before starting
    cleared = 0
    for f in OUT_DIR.iterdir():
        if f.is_file():
            try:
                f.unlink()
                cleared += 1
            except Exception:
                pass
    if cleared:
        print(f"Cleared {cleared} file(s) from {OUT_DIR}")


    out_audio = OUT_DIR / f"{job_id}.mp3"
    out_srt   = OUT_DIR / f"{job_id}.srt"
    out_temp  = OUT_DIR / f"{job_id}.temp.mp4"
    out_final = OUT_DIR / f"{job_id}.mp4"

    base_video = BASE_VIDEOS / "minecraft_parkour_base.mp4"
    if not base_video.exists():
        print(f"Base video not found: {base_video}")
        print("Place a base video at that path and re-run.")
        sys.exit(1)

    print("=" * 60)
    print("TTS QUALITY TEST")
    print("=" * 60)
    print(f"Chunks  : {len(CHUNKS)}")
    print(f"Story   : {STORY_TITLE}")
    print(f"Speed   : {VIDEO_SPEED_MULTIPLIER}x")
    print(f"Job ID  : {job_id}")
    print()

    print("Chunk content:")
    for i, chunk in enumerate(CHUNKS, 1):
        print(f"  [{i}] {chunk}")
    print()

    try:
        # 1) TTS
        print("[1/4] Generating TTS audio...")
        full_text = f"{STORY_TITLE}. {CLEANED_TEXT}"
        full_chunks = [f"{STORY_TITLE}."] + CHUNKS
        text_to_speech(full_text, str(out_audio), chunks=full_chunks)
        cleanup_tts_memory()
        size_kb = out_audio.stat().st_size // 1024
        print(f"      Audio saved: {out_audio.name} ({size_kb} KB)\n")

        # 2) Whisper subtitle alignment
        print("[2/4] Aligning subtitles with Whisper...")
        srt_text = f"{STORY_TITLE}. {CLEANED_TEXT}"
        srt_content = generate_srt_from_audio_and_text(
            str(out_audio),
            srt_text,
            speed_multiplier=VIDEO_SPEED_MULTIPLIER,
        )
        with open(out_srt, "w") as f:
            f.write(srt_content)
        subtitle_count = srt_content.count("\n\n")
        print(f"      SRT saved: {out_srt.name} ({subtitle_count} subtitle blocks)\n")

        # 3) Merge audio with base video segment
        print("[3/4] Merging audio with base video...")
        video_duration = get_video_duration(str(base_video))
        # Use the first 30 seconds of the base video — deterministic for easy comparison
        segment_duration = min(30.0, video_duration)
        merge_audio_with_video(str(base_video), str(out_audio), str(out_temp),
                               start_time=0.0, duration=segment_duration)
        print(f"      Temp video saved: {out_temp.name}\n")

        # 4) Burn subtitles + speed-up → final output
        print(f"[4/4] Burning subtitles + applying {VIDEO_SPEED_MULTIPLIER}x speed...")
        burn_text_overlay(
            str(out_temp),
            str(out_srt),
            str(out_final),
            speed_multiplier=VIDEO_SPEED_MULTIPLIER,
        )
        final_size_mb = out_final.stat().st_size / (1024 * 1024)
        print(f"      Final video: {out_final.name} ({final_size_mb:.1f} MB)\n")

        print("=" * 60)
        print("DONE")
        print(f"Output: {out_final}")
        print("=" * 60)

        import subprocess, platform
        try:
            os.startfile(str(out_final))          # Windows
        except AttributeError:
            subprocess.call(["open", str(out_final)])   # macOS fallback
        print()
        print("What to listen/watch for:")
        print("  - Does the narration feel dramatic and expressive?")
        print("  - Do pauses and tension moments (gasp, sob) land correctly?")
        print("  - Does Josh's voice have depth and weight?")
        print("  - Are subtitles tightly synced to the audio?")
        print("  - Does the 1.1x speed feel natural (not rushed)?")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        # Clean up all intermediary files; keep only the final .mp4
        ass_path = OUT_DIR / f"{job_id}.ass"
        for path in (out_audio, out_srt, out_temp, ass_path):
            if path.exists():
                try:
                    path.unlink()
                except Exception:
                    pass


if __name__ == "__main__":
    main()

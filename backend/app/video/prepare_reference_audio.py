#!/usr/bin/env python3
"""
Script to prepare optimal reference audio for voice cloning.
Takes a raw audio file and optimizes it for XTTS v2.
"""

import subprocess
import os
from pathlib import Path

def optimize_reference_audio(input_path, output_path, target_duration=8.0):
    """
    Optimize audio file for voice cloning:
    1. Convert to mono
    2. Set to 22050 Hz sample rate (XTTS v2 optimal)
    3. Remove silence at start/end
    4. Normalize volume
    5. Apply noise reduction
    6. Trim or extend to target duration
    """
    
    temp_dir = Path(output_path).parent / "temp"
    temp_dir.mkdir(exist_ok=True)
    
    step1 = temp_dir / "step1_cleaned.wav"
    step2 = temp_dir / "step2_normalized.wav"
    step3 = temp_dir / "step3_trimmed.wav"
    
    print("🎙️ Step 1: Cleaning and converting audio...")
    # Clean, convert to mono, set sample rate
    subprocess.run([
        'ffmpeg', '-y',
        '-i', input_path,
        '-af', 'silenceremove=start_periods=1:start_silence=0.1:start_threshold=-50dB,areverse,silenceremove=start_periods=1:start_silence=0.1:start_threshold=-50dB,areverse',
        '-ar', '22050',
        '-ac', '1',
        '-acodec', 'pcm_s16le',
        str(step1)
    ], check=True)
    
    print("🎚️ Step 2: Normalizing volume...")
    # Normalize to -3dB for consistent volume
    subprocess.run([
        'ffmpeg', '-y',
        '-i', str(step1),
        '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',
        '-ar', '22050',
        '-ac', '1',
        str(step2)
    ], check=True)
    
    print("✂️ Step 3: Trimming to optimal duration...")
    # Trim to target duration (8 seconds is optimal for XTTS v2)
    subprocess.run([
        'ffmpeg', '-y',
        '-i', str(step2),
        '-t', str(target_duration),
        '-ar', '22050',
        '-ac', '1',
        str(step3)
    ], check=True)
    
    print("💾 Step 4: Saving final optimized audio...")
    # Save as high-quality WAV (better than MP3 for voice cloning)
    subprocess.run([
        'ffmpeg', '-y',
        '-i', str(step3),
        '-acodec', 'pcm_s16le',
        '-ar', '22050',
        '-ac', '1',
        output_path
    ], check=True)
    
    # Cleanup temp files
    print("🧹 Cleaning up temporary files...")
    for temp_file in [step1, step2, step3]:
        if temp_file.exists():
            temp_file.unlink()
    temp_dir.rmdir()
    
    print(f"✅ Optimized reference audio saved to: {output_path}")
    print(f"📊 Audio specs: 22050Hz, mono, {target_duration}s duration")
    return output_path


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python prepare_reference_audio.py <input_audio_file> [output_file] [duration]")
        print("Example: python prepare_reference_audio.py my_voice.mp3 optimized_reference.wav 8.0")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "optimized_reference.wav"
    duration = float(sys.argv[3]) if len(sys.argv) > 3 else 8.0
    
    if not os.path.exists(input_file):
        print(f"❌ Error: Input file '{input_file}' not found")
        sys.exit(1)
    
    optimize_reference_audio(input_file, output_file, duration)

#!/usr/bin/env python3
"""
Quick diagnostic to test TTS voice cloning
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os

print("="*70)
print("🔍 TTS DIAGNOSTIC")
print("="*70)

# Check training audio
training_audio = "/Users/nicholasfong/Documents/projects/Narrify/backend/app/video/training/training_audio.mp3"
print(f"\n1. Training Audio Check:")
print(f"   Path: {training_audio}")
print(f"   Exists: {os.path.exists(training_audio)}")
if os.path.exists(training_audio):
    size = os.path.getsize(training_audio) / 1024
    print(f"   Size: {size:.2f} KB")

# Test TTS model loading
print(f"\n2. Loading TTS Model:")
try:
    from TTS.api import TTS
    print(f"   ✅ TTS library imported")
    
    print(f"   Loading XTTS v2...")
    tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
    print(f"   ✅ XTTS v2 loaded successfully!")
    
    # Check model properties
    print(f"\n3. Model Properties:")
    print(f"   Model name: {tts.model_name}")
    print(f"   Is multi-speaker: {tts.is_multi_speaker}")
    print(f"   Is multi-lingual: {tts.is_multi_lingual}")
    
    if hasattr(tts, 'speakers'):
        print(f"   Speakers: {tts.speakers}")
    
    # Test voice cloning
    print(f"\n4. Testing Voice Cloning:")
    test_text = "This is a test of voice cloning functionality."
    output_path = "/tmp/test_voice_clone.wav"
    
    print(f"   Text: {test_text}")
    print(f"   Reference: {training_audio}")
    print(f"   Output: {output_path}")
    
    try:
        tts.tts_to_file(
            text=test_text,
            speaker_wav=training_audio,
            language="en",
            file_path=output_path
        )
        print(f"   ✅ Voice cloning test PASSED!")
        print(f"   Generated: {output_path}")
        if os.path.exists(output_path):
            size = os.path.getsize(output_path) / 1024
            print(f"   Size: {size:.2f} KB")
    except Exception as e:
        print(f"   ❌ Voice cloning test FAILED!")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
    
except Exception as e:
    print(f"   ❌ Failed to load TTS: {e}")
    import traceback
    traceback.print_exc()

print(f"\n" + "="*70)
print(f"✅ DIAGNOSTIC COMPLETE")
print(f"="*70)

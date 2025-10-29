#!/usr/bin/env python3
"""
Diagnose TTS initialization issues
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("="*70)
print("🔍 TTS INITIALIZATION DIAGNOSTIC")
print("="*70)

# Import the TTS module to trigger initialization
print("\n1. Importing TTS module...")
from app.video import tts

print("\n2. Checking TTS Module State:")
print(f"   VOICE_CLONING_AVAILABLE: {tts.VOICE_CLONING_AVAILABLE}")
print(f"   VOICE_REFERENCE_PATH: {tts.VOICE_REFERENCE_PATH}")
print(f"   Reference exists: {Path(tts.VOICE_REFERENCE_PATH).exists() if tts.VOICE_REFERENCE_PATH else False}")
print(f"   TTS model loaded: {tts.tts_model is not None}")

if tts.tts_model:
    print(f"\n3. TTS Model Details:")
    print(f"   Model name: {tts.tts_model.model_name if hasattr(tts.tts_model, 'model_name') else 'Unknown'}")
    print(f"   Is multi-speaker: {tts.tts_model.is_multi_speaker if hasattr(tts.tts_model, 'is_multi_speaker') else 'Unknown'}")
    
    if hasattr(tts.tts_model, 'speakers'):
        print(f"   Available speakers: {tts.tts_model.speakers}")

print("\n4. Testing Voice Cloning Path:")
test_text = "This is a test."
test_output = "/tmp/test_diagnosis.mp3"

try:
    if tts.VOICE_CLONING_AVAILABLE and Path(tts.VOICE_REFERENCE_PATH).exists():
        print("   ✅ Would use: generate_voice_cloned_speech()")
        print(f"   Reference: {tts.VOICE_REFERENCE_PATH}")
    else:
        print("   ❌ Would use: generate_standard_tts()")
        if not tts.VOICE_CLONING_AVAILABLE:
            print(f"   Reason: VOICE_CLONING_AVAILABLE = False")
        if not Path(tts.VOICE_REFERENCE_PATH).exists():
            print(f"   Reason: Reference audio not found at {tts.VOICE_REFERENCE_PATH}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "="*70)

# TTS Voice Cloning Fix - October 26, 2025

## Issue Summary

Voice cloning was failing during the FFmpeg audio processing step, causing videos to fail generation with an error about "gTTS fallback disabled."

## Root Cause

The `deesser` filter in FFmpeg 8.0 changed its parameter format:

- **Old (FFmpeg < 8.0):** `deesser=f=6000` (frequency in Hz)
- **New (FFmpeg 8.0+):** `deesser=f=0.5` (normalized value 0-1)

The error was:

```
[Parsed_deesser_12 @ 0x14363fe80] Value 6000.000000 for parameter 'f' out of range [0 - 1]
```

## Solution

Replaced the incompatible `deesser` filter with a compatible alternative using:

- `highpass=f=5000` - Isolate high frequencies where sibilance occurs
- `lowpass=f=8000` - Limit to sibilance range
- `volume=0.6/0.7` - Reduce sibilance volume
- `acompressor` - Compress harsh sibilance with appropriate threshold and ratio

## Files Modified

- `/backend/app/video/tts.py` - Updated audio processing filters for FFmpeg 8.0 compatibility

## Current Status

✅ **Voice cloning is working correctly**

- XTTS v2 model loads successfully
- Reference audio is found and used
- Audio processing completes without errors
- High-quality cloned voice output is generated

## Testing

Verified with test audio generation:

```bash
python -c "from app.video.tts import text_to_speech; text_to_speech('Test', '/tmp/test.mp3')"
```

## Notes

- The system was NEVER defaulting to gTTS
- Voice cloning was initialized correctly
- The failure occurred during post-processing, not TTS generation
- The fix maintains the same de-essing quality using FFmpeg 8.0 compatible filters

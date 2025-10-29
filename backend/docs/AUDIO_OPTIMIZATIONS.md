# Audio & Subtitle Optimization Guide

## Current Optimizations (Implemented)

### 1. Text Preprocessing (Minimal)

**Location:** `app/video/tts.py` - `preprocess_text_for_tts()`

**What we do:**

- Replace smart quotes with regular quotes (only for TTS compatibility)
- Fix only critical contractions that break pronunciation:
  - won't → will not
  - can't → cannot
  - ain't → am not
- **Keep most contractions** (he's, she's, they're, etc.) to preserve original text

**Why minimal preprocessing?**

- Original text displays correctly in subtitles
- Most contractions sound fine with modern TTS
- Reduces text mismatch between audio and display

### 2. Audio Processing (Less Aggressive)

**Location:** `app/video/tts.py` - `convert_to_mp3_with_processing()`

**For Voice Cloned Audio:**

- Pitch shift: 6% (was 12%) - more natural
- Speed: 1.05x (was 1.08x) - better pacing
- EQ: Gentle boosts (1.5-2dB instead of 3-4dB)
- Compression: Moderate for consistency
- Preserves voice cloning characteristics

**For Standard TTS:**

- Pitch shift: 8% (was 15%)
- Speed: 1.08x (was 1.12x)
- EQ: Moderate boosts (2-2.5dB instead of 4-5dB)
- Still bright but more natural

### 3. Chunk Size Optimization

**Location:** `app/video/tts.py` - `generate_voice_cloned_speech()` and `generate_standard_tts()`

- Voice cloned: **120 characters** (was 200)
- Standard TTS: **150 characters** (was 500)

**Benefits:**

- Better prosody and natural speech rhythm
- More accurate voice cloning
- Clearer pronunciation
- Less robotic sound

### 4. Subtitle Timing (Fixed Desync)

**Location:** `app/video/srt.py` - `generate_srt_from_audio_and_text()`

**New Method:**

- Uses actual audio duration from ffprobe
- Even distribution across all words
- Adjusts for word length and punctuation
- 50ms gap between words for readability

**Why this works better than Whisper:**

- No drift over time
- Consistent pacing
- More predictable timing
- Works even if Whisper misses words

## Additional Optimization Ideas

### A. Reference Audio Quality

**Current:** Using training_audio.mp3

**Improvements to try:**

```bash
# Preprocess your reference audio for optimal voice cloning
cd app/video
python prepare_reference_audio.py training/your_audio.mp3 training/training_audio.wav 8.0
```

**Best practices:**

- 6-10 seconds of clean speech
- Single speaker, no background noise
- Natural conversational tone (not reading)
- WAV format at 22050Hz
- Properly normalized volume

### B. Model Alternatives (If Quality Still Not Sufficient)

**Option 1: StyleTTS 2**

- Better prosody than XTTS v2
- More natural voice cloning
- Slower but higher quality

**Option 2: Kokoro-82M**

- Recent model (2024)
- Fast inference
- Good balance of speed/quality

**Option 3: F5-TTS**

- Very natural prosody
- Fast generation
- Good voice cloning with short samples

### C. Post-Processing Tweaks

**If voice still sounds harsh:**

- Reduce pitch shift to 3-4%
- Lower EQ boosts by another 0.5-1dB
- Increase low-pass filter frequency

**If voice lacks energy:**

- Slight increase in compression ratio
- Add gentle exciter at 4-5kHz
- Increase high-shelf boost at 8kHz

### D. Subtitle Readability

**Current settings:**

- Bold white text with black outline
- 36pt font, Arial
- 105% horizontal scaling

**Optional improvements:**

- Increase font size to 38-40pt for mobile viewing
- Add slight shadow for more depth
- Consider all-caps for emphasis (some creators prefer this)

## Testing Checklist

After generating a video, check:

- [ ] Audio sounds natural (not robotic)
- [ ] Contractions are pronounced correctly
- [ ] Subtitles stay in sync throughout
- [ ] Text displays match what's spoken
- [ ] No harsh/sharp frequencies
- [ ] Volume is consistent
- [ ] Pacing feels natural

## Performance Notes

**Current generation time:**

- ~2-3 seconds per chunk with XTTS v2
- ~10-15 seconds total for Whisper analysis (if used)
- ~5-10 seconds for video composition

**Total:** ~2-3 minutes for a 1-minute video

## Recommended Settings for Different Content Types

### Reddit Stories (Current)

- Chunk size: 120 chars
- Pitch shift: 6%
- Speed: 1.05x
- ✅ Current settings are optimal

### Shorter TikTok Content

- Chunk size: 100 chars (more dynamic)
- Pitch shift: 8% (more energy)
- Speed: 1.10x (faster pacing)

### Long-Form YouTube

- Chunk size: 150 chars (smoother)
- Pitch shift: 4% (more natural)
- Speed: 1.02x (more relaxed)

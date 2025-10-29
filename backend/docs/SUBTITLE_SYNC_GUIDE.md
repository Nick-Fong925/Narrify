# Subtitle Synchronization Guide

## Problem Solved

When audio says "he is" but subtitles show "he's", we need to ensure perfect timing alignment.

## Solution: Whisper Word-Level Alignment

### How It Works

1. **Audio Generation**

   - Text is preprocessed for TTS: "he's" → "he is"
   - Audio is generated with expanded text
   - Audio file is saved

2. **Whisper Transcription**

   - Whisper analyzes the audio
   - Extracts word-level timestamps for what was actually spoken
   - Returns: `[{word: "he", start: 1.2, end: 1.4}, {word: "is", start: 1.4, end: 1.6}]`

3. **Contraction Mapping**

   - Original text: "he's being"
   - Whisper heard: "he is being"
   - Mapping: "he's" (1 original word) = "he" + "is" (2 audio words)
   - Timing: Use combined span of both audio words

4. **Phrase Grouping**
   - Words are grouped into 3-4 word phrases
   - Natural breaks at punctuation
   - Each phrase gets accurate start/end timestamps

### Example Flow

**Original Text:**

```
"I'm 17M and he's being ridiculous!"
```

**TTS Audio (expanded):**

```
"I am seventeen M and he is being ridiculous!"
```

**Whisper Word Timings:**

```
I       → 0.0 - 0.2s
am      → 0.2 - 0.4s
seventeen → 0.4 - 0.8s
M       → 0.8 - 1.0s
and     → 1.0 - 1.2s
he      → 1.2 - 1.4s
is      → 1.4 - 1.6s
being   → 1.6 - 2.0s
ridiculous → 2.0 - 2.5s
```

**Subtitle Groups (3-4 words):**

```
1
00:00:00,000 --> 00:00:01,200
I'm 17M and he's

2
00:00:01,200 --> 00:00:02,500
being ridiculous!
```

### Configuration

Edit `subtitle_config.py` to customize:

```python
# Number of words per subtitle
WORDS_PER_SUBTITLE_MIN = 3  # Minimum before breaking
WORDS_PER_SUBTITLE_MAX = 4  # Maximum per group

# Whisper accuracy vs speed
WHISPER_MODEL = "base"  # "tiny", "base", "small", "medium", "large"
```

### Supported Contractions

The system automatically maps 50+ contractions:

- `I'm` ↔ "I am"
- `he's` ↔ "he is" / "he has"
- `won't` ↔ "will not"
- `can't` ↔ "cannot"
- `shouldn't've` ↔ "should not have"
- And many more...

### Age/Gender Patterns

Also handles Reddit abbreviations:

- `17M` ↔ "seventeen M"
- `25F` ↔ "twenty five F"

### Benefits

✅ **Perfect Sync**: Subtitles match audio timing exactly
✅ **Natural Reading**: Shows contractions, not expanded text
✅ **Readable Groups**: 3-4 words at a time
✅ **Smart Breaks**: Pauses at punctuation
✅ **Automatic**: No manual timing needed

### Troubleshooting

**Subtitles appear too fast/slow?**

- Check `WHISPER_MODEL` - use "small" for better accuracy
- Verify audio quality - poor audio = poor timing

**Words grouping incorrectly?**

- Adjust `WORDS_PER_SUBTITLE_MIN/MAX` in config
- Check `BREAK_PUNCTUATION` for natural breaks

**Contraction mapping issues?**

- Check `is_contraction_expansion()` in `srt.py`
- Add custom mappings if needed

### Performance

| Model  | Speed  | Accuracy   | Recommended For      |
| ------ | ------ | ---------- | -------------------- |
| tiny   | 🚀🚀🚀 | ⭐⭐       | Quick tests          |
| base   | 🚀🚀   | ⭐⭐⭐     | Production (default) |
| small  | 🚀     | ⭐⭐⭐⭐   | High accuracy needed |
| medium | 🐌     | ⭐⭐⭐⭐⭐ | Critical content     |
| large  | 🐌🐌   | ⭐⭐⭐⭐⭐ | Maximum quality      |

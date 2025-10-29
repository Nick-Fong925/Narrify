# Text Preprocessing Strategy

## The Problem

When generating videos from Reddit content, we face two competing needs:

1. **Audio clarity**: TTS models struggle with contractions ("he's", "won't") and Reddit abbreviations ("17M", "AITA")
2. **Visual aesthetics**: Expanded text ("he is", "will not") looks unnatural in subtitles

## The Solution: Dual Text Processing

### Architecture

```
Reddit Story
     │
     ├─→ clean_story() ────→ Original text with contractions
     │                        └─→ Used for SUBTITLES (looks natural)
     │
     └─→ prepare_text_for_tts() ─→ Expanded contractions & Reddit patterns
                                   └─→ Used for AUDIO (sounds clear)
```

### Text Flow

1. **Original Reddit Text**

   ```
   "AITA? I'm 17M and he's being weird. Won't listen to me!"
   ```

2. **Subtitle Text** (via `clean_story()`)

   ```
   "AITA? I'm 17M and he's being weird. Won't listen to me!"
   ```

   - Keeps contractions: "I'm", "he's", "Won't"
   - Keeps age/gender as typed: "17M"
   - Removes markdown, links, edits
   - Natural reading experience

3. **Audio Text** (via `prepare_text_for_tts()`)
   ```
   "Am I the asshole? I am seventeen M and he is being weird. Will not listen to me!"
   ```
   - Expands contractions: "I'm" → "I am", "he's" → "he is"
   - Expands age/gender: "17M" → "seventeen M"
   - Expands Reddit acronyms: "AITA" → "Am I the asshole"
   - Clear pronunciation

## Implementation

### In `text_cleaning.py`:

```python
def clean_story(text: str) -> str:
    """Clean Reddit story - keeps contractions for natural display"""
    # Remove markdown, links, edits
    # Returns original text style

def prepare_text_for_tts(text: str) -> str:
    """Prepare text for audio generation - expands everything"""
    text = clean_story(text)  # First clean
    text = preprocess_for_tts(text)  # Then expand
    return text
```

### In `generator.py`:

```python
# Original text for subtitles
text = clean_story(post.story)

# Generate audio (TTS handles expansion internally)
text_to_speech(text, out_audio)

# Generate subtitles with ORIGINAL text
generate_srt_from_audio_and_text(out_audio, text)
```

### In `tts.py`:

```python
def text_to_speech(text: str, out_path: str):
    # Expand text for TTS only
    tts_text = prepare_text_for_tts(text)

    # Generate audio with expanded text
    tts_model.tts_to_file(text=tts_text, ...)
```

## Supported Transformations

### Age/Gender Abbreviations

- `17M` → "seventeen M"
- `25F` → "twenty five F"
- `(19M)` → "(nineteen M)"

### Reddit Acronyms

- `AITA` → "Am I the asshole"
- `TIFU` → "Today I fucked up"
- `SO` → "significant other"
- `BF/GF` → "boyfriend/girlfriend"
- `IMO/IMHO` → "in my opinion/in my humble opinion"
- `TBH` → "to be honest"
- `BTW` → "by the way"

### Contractions (50+)

- `he's` → "he is"
- `won't` → "will not"
- `can't` → "cannot"
- `shouldn't've` → "should not have"
- `I'm` → "I am"
- `you're` → "you are"
- And many more...

## Benefits

✅ **Clear Audio**: TTS pronounces everything correctly
✅ **Natural Subtitles**: Text looks like normal conversation
✅ **No Manual Work**: Automatic preprocessing
✅ **Reddit-Optimized**: Handles common patterns
✅ **Maintains Original Style**: Users see authentic Reddit text

## Testing

Run the test suite:

```bash
python test_text_flow.py
```

This will show you:

- Original text
- Subtitle text (what users see)
- Audio text (what TTS reads)
- All transformations applied

# Video Metadata Management Guide

## Problem Solved

**Before:** Generated videos inherited all metadata from the base video (Minecraft parkour), including:

- Title: "Minecraft Parkour Gameplay NO COPYRIGHT (Vertical)"
- Artist: "Orbital - No Copyright Gameplay"
- Description: Long YouTube description with links
- Comments and other irrelevant metadata

**After:** Generated videos have clean metadata (stripped by default)

## Current Implementation

### Automatic Metadata Stripping

Both video processing steps now automatically strip metadata:

1. **Audio merge step** (`merge_audio_with_video`)

   - Removes all metadata from base video
   - Clean slate for your content

2. **Subtitle burn-in step** (`burn_text_overlay`)
   - Ensures no metadata carries through
   - Final output is clean

### FFmpeg Flags Used

```python
"-map_metadata", "-1",  # Remove all metadata
"-fflags", "+bitexact"   # Remove encoder info
```

## Optional: Adding Custom Metadata

If you want to add your own branding/metadata, use the new utility functions:

### View Current Metadata

```python
from app.video.metadata_utils import view_metadata

# Check what metadata is in a video
metadata = view_metadata('path/to/video.mp4')
print(metadata)
# Output: {'title': '...', 'artist': '...', 'description': '...'}
```

### Add Custom Metadata

```python
from app.video.metadata_utils import add_custom_metadata

# Add your own metadata
add_custom_metadata(
    'input.mp4',
    'output_with_metadata.mp4',
    {
        'title': 'AITA: Daughter Sleepover Drama',
        'artist': 'Narrify',
        'comment': 'Reddit story narration',
        'description': 'A story from r/AmItheAsshole',
        'date': '20250115',  # YYYYMMDD format
        'genre': 'Reddit Stories'
    }
)
```

### Strip Metadata Manually

```python
from app.video.metadata_utils import strip_all_metadata

# Remove all metadata from a video
strip_all_metadata('input.mp4', 'clean_output.mp4')
```

## Integration with Video Generator

If you want to automatically add metadata to all generated videos, modify `generator.py`:

```python
def generate_video_from_text(text: str, base_video_name: str, job_id: str = None,
                            voice_type: str = "male", custom_metadata: dict = None):
    """
    ... existing code ...
    """

    # After burning subtitles
    burn_text_overlay(str(out_temp), str(out_srt), str(out_final))

    # Optionally add custom metadata
    if custom_metadata:
        from app.video.metadata_utils import add_custom_metadata
        temp_final = OUT_DIR / f"{job_id}_temp_final.mp4"
        add_custom_metadata(str(out_final), str(temp_final), custom_metadata)
        out_final.unlink()
        temp_final.rename(out_final)

    # ... rest of cleanup ...
```

## Common Metadata Keys

### Standard Keys

- `title` - Video title
- `artist` - Creator/channel name
- `album` - Series or collection name
- `date` - Publication date (YYYYMMDD)
- `comment` - Short comment or tagline
- `description` - Full description
- `genre` - Content genre/category
- `copyright` - Copyright information

### Platform-Specific

- `synopsis` - Short summary (used by some players)
- `episode_id` - Episode number for series
- `season_number` - Season number for series
- `show` - Show name

## Example Use Cases

### 1. Branding Your Content

```python
metadata = {
    'title': f'Reddit Story: {post.title[:50]}',
    'artist': 'YourChannelName',
    'comment': f'From r/{post.subreddit}',
    'date': datetime.now().strftime('%Y%m%d')
}
```

### 2. Series Organization

```python
metadata = {
    'title': f'AITA Stories - Episode {episode_num}',
    'album': 'AITA Story Collection',
    'episode_id': str(episode_num),
    'artist': 'Narrify Stories'
}
```

### 3. Source Attribution

```python
metadata = {
    'title': post.title,
    'comment': f'Original post: {post.url}',
    'description': f'Score: {post.score} | Comments: {post.num_comments}',
    'genre': 'Reddit Stories'
}
```

## API Endpoint Enhancement

You could add metadata support to the API endpoint:

```python
class VideoRequest(BaseModel):
    post_id: Optional[int] = None
    raw_text: Optional[str] = None
    base_video: Optional[str] = "minecraft_parkour_base.mp4"
    voice_type: Optional[str] = "male"
    metadata: Optional[dict] = None  # NEW: Custom metadata

@router.post("/video/")
def generate_video(req: VideoRequest, db: Session = Depends(get_db)):
    # ... existing code ...

    video_path = generate_video_from_text(
        text,
        req.base_video,
        job_id,
        req.voice_type,
        custom_metadata=req.metadata  # Pass metadata
    )
```

## Benefits of Clean Metadata

✅ **Professional Appearance**

- No third-party branding in your videos
- Clean file info when uploading to platforms

✅ **Privacy**

- No source video information exposed
- Clean chain of custody

✅ **Platform Compatibility**

- Some platforms scan metadata for copyright
- Clean metadata avoids false positives

✅ **SEO Control**

- Add your own titles and descriptions
- Better platform optimization

## Testing Metadata

### Check if metadata is stripped:

```bash
# View metadata with ffprobe
ffprobe -v error -show_entries format_tags -of json video.mp4

# Should return empty or minimal metadata
```

### Before Fix:

```json
{
  "format": {
    "tags": {
      "title": "Minecraft Parkour Gameplay NO COPYRIGHT (Vertical)",
      "artist": "Orbital - No Copyright Gameplay",
      "date": "20240803",
      "description": "⭐ If you want to have the BEST quality...",
      "comment": "https://www.youtube.com/watch?v=..."
    }
  }
}
```

### After Fix:

```json
{
  "format": {}
}
```

## Notes

- Metadata stripping happens **automatically** now
- No action needed for basic usage
- Use `metadata_utils.py` only if you want to **add** custom metadata
- Metadata operations are fast (no re-encoding, just copying streams)

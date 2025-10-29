"""
Subtitle configuration for video generation

IMPORTANT: Video Quality Notes
- Current base video resolution: 2560x1440 @ 60fps (2K horizontal, auto-cropped to 810x1440 vertical)
- Auto-crop system: Horizontal videos are automatically center-cropped to 9:16 aspect ratio
- Final output: ~810x1440 (HD quality, between 720p and 1080p)
- This resolution is EXCELLENT for YouTube Shorts - much better than old 480x854
"""

# Subtitle grouping settings
WORDS_PER_SUBTITLE_MIN = 2  # Minimum words before breaking at punctuation
WORDS_PER_SUBTITLE_MAX = 3  # Maximum words per subtitle group (increased for better readability)

# Timing adjustments
SUBTITLE_GAP_SECONDS = 0.7  # Smaller gap for tighter timing (reduced from 0.1)
MIN_SUBTITLE_DURATION = 2.1  # Minimum time a subtitle should be visible (reduced from 0.8)

# Whisper model settings
WHISPER_MODEL = "tiny"  # Options: "tiny", "base", "small", "medium", "large"
                        # tiny: fastest, least accurate (390 MB RAM) ← USING FOR LOW RAM
                        # base: good balance (1 GB RAM)
                        # small: better accuracy (2 GB RAM)
                        # medium: excellent accuracy (5 GB RAM) - TOO MUCH
                        # Changed to "tiny" to minimize RAM usage
                        # Still accurate enough for clean narration audio

# Break subtitle at these punctuation marks (if min words met)
BREAK_PUNCTUATION = '.!?,;:'

# Video speed settings
VIDEO_SPEED_MULTIPLIER = 1.3  # Speed up final video (1.0 = normal, 1.25 = 25% faster, 1.5 = 50% faster)
                               # Speeds up both video AND audio while preserving audio pitch
                               # Recommended: 1.15-1.35 for content pacing improvements

# Video quality settings (for YouTube Shorts)
# LOW RAM OPTIMIZED: Prioritize not crashing over maximum quality
VIDEO_CRF = 23                # Constant Rate Factor: 20=high, 23=medium, 26=acceptable
                              # CRF 23 is "medium quality" - much lower file sizes
                              # YouTube compresses heavily anyway, final quality is acceptable
VIDEO_PRESET = "veryfast"     # Encoding preset: ultrafast/veryfast/medium/slow
                              # "veryfast" = 8x faster than "slow", very low RAM usage
                              # Encodes quickly with minimal memory footprint
VIDEO_BITRATE_MAX = "4M"      # Maximum video bitrate (higher = better quality, larger files)
                              # 4 Mbps keeps temp files small (~50-70 MB instead of 150 MB)
                              # Sufficient for 810x1440 after YouTube compression

# Title narration settings
NARRATE_TITLE = True            # Have TTS read the title at the beginning
TITLE_PAUSE_AFTER = 0.5         # Pause after title (seconds) before story starts

# Audio clarity settings
AUDIO_ENHANCEMENT_LEVEL = "high"  # Options: "off", "low", "medium", "high", "extreme"
                                   # Higher = clearer/sharper but may sound more processed
AUDIO_BITRATE = "128k"            # Audio quality: "64k" (smaller), "96k" (balanced), "128k" (high quality), "192k" (very high)

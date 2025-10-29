# Narrify Project Structure

## Directory Organization

```
backend/
├── app/                          # Main application package
│   ├── api/                      # FastAPI routes and endpoints
│   │   ├── __init__.py
│   │   └── endpoints.py          # API endpoints for posts and videos
│   │
│   ├── models/                   # Database models
│   │   ├── __init__.py
│   │   └── post.py               # Post model with automation fields
│   │
│   ├── services/                 # Business logic layer
│   │   ├── __init__.py
│   │   ├── reddit_scraper.py     # Reddit scraping service
│   │   ├── video_service.py      # Video generation orchestration
│   │   └── youtube_service.py    # YouTube upload service
│   │
│   ├── utils/                    # Utility functions
│   │   ├── logger.py             # Centralized logging
│   │   └── text_cleaning.py      # Text preprocessing for TTS
│   │
│   ├── video/                    # Video generation components
│   │   ├── __init__.py
│   │   ├── ffmpeg_utils.py       # FFmpeg wrapper functions
│   │   ├── generator.py          # Main video generation pipeline
│   │   ├── metadata_utils.py     # YouTube metadata generation
│   │   ├── prepare_reference_audio.py  # Voice reference prep
│   │   ├── srt.py                # Subtitle generation with Whisper
│   │   ├── subtitle_config.py    # Subtitle and video settings
│   │   ├── tts.py                # Text-to-speech with voice cloning
│   │   └── tts_enhanced.py       # Enhanced TTS (legacy)
│   │
│   ├── config.py                 # Configuration management (pydantic-settings)
│   ├── db.py                     # Database connection and session
│   ├── main.py                   # FastAPI application entry point
│   └── scheduler.py              # Reddit scraping scheduler
│
├── automation/                   # Automation system
│   ├── __init__.py
│   └── scheduler.py              # YouTube posting automation scheduler
│
├── config/                       # Configuration files
│   ├── automation.yaml           # Automation settings (editable)
│   ├── youtube_credentials.json  # OAuth credentials (not in git)
│   └── youtube_token.json        # OAuth token (not in git)
│
├── docs/                         # Documentation
│   ├── AUTOMATION_GUIDE.md       # Complete automation setup guide
│   ├── AUDIO_OPTIMIZATIONS.md    # Audio enhancement details
│   ├── CHUNK_SIZE_ANALYSIS.md    # TTS chunking strategy
│   ├── METADATA_GUIDE.md         # YouTube metadata guide
│   ├── SUBTITLE_SYNC_GUIDE.md    # Subtitle synchronization details
│   ├── TEXT_PREPROCESSING_STRATEGY.md  # Text processing logic
│   └── TITLE_CARD_GUIDE.md       # Title card implementation (deprecated)
│
├── logs/                         # Application logs
│   └── narrify.log               # Main log file (auto-rotated)
│
├── scripts/                      # CLI utilities
│   ├── run_automation.py         # Manual automation trigger
│   └── upload_video.py           # Manual YouTube upload
│
├── tests/                        # Test files
│   ├── debug_subtitles.py        # Subtitle debugging
│   ├── test_text_flow.py         # Text processing tests
│   ├── test_text_preprocessing.py # Text preprocessing tests
│   ├── test_video_generation.py  # Video generation tests
│   └── test_voice_clone.wav      # Test audio file
│
├── .env                          # Environment variables (not in git)
├── .env.example                  # Environment template
├── .gitignore                    # Git ignore rules
├── requirements.txt              # Python dependencies
└── stories.db                    # SQLite database
```

## Key Components

### Application Layer (`app/`)

**API Layer** (`app/api/`)

- RESTful endpoints for post management
- Video generation triggers
- Status queries

**Models** (`app/models/`)

- `Post`: Reddit post with generation/posting status
- Fields: reddit_id, title, story, score, posted, youtube_video_id, etc.

**Services** (`app/services/`)

- `reddit_scraper.py`: Scrapes subreddits for content
- `video_service.py`: Orchestrates video generation pipeline
- `youtube_service.py`: Handles YouTube OAuth and uploads

**Utils** (`app/utils/`)

- `logger.py`: Structured logging with rotation
- `text_cleaning.py`: Text preprocessing (contractions, slang, numbers)

**Video** (`app/video/`)

- `generator.py`: Main pipeline (audio → subtitles → merge → speed)
- `tts.py`: Voice cloning with XTTS v2
- `srt.py`: Whisper-based subtitle generation
- `subtitle_config.py`: Centralized video settings

### Automation Layer (`automation/`)

**Scheduler** (`automation/scheduler.py`)

- APScheduler integration
- Cron-based job scheduling
- Batch processing at configured times (5 PM, 9 PM EST)

### Configuration (`config/`)

**automation.yaml**

```yaml
automation:
  videos_per_day: 10
  schedule_times: ["17:00", "21:00"]
youtube:
  privacy: "public"
  title_suffix: " #shorts"
video:
  delete_after_upload: true
```

**Secrets** (not in git)

- `youtube_credentials.json`: OAuth client secrets from Google Cloud
- `youtube_token.json`: OAuth access/refresh tokens

### Documentation (`docs/`)

Comprehensive guides covering:

- Setup and deployment
- Feature explanations
- Technical implementation details
- Troubleshooting

### Scripts (`scripts/`)

**CLI Tools**

- `run_automation.py`: Manual trigger with `--dry-run` option
- `upload_video.py`: Direct YouTube upload utility

### Tests (`tests/`)

Test files for:

- Text preprocessing validation
- Video generation testing
- Subtitle synchronization debugging

## Data Flow

### Reddit Scraping Flow

```
Reddit API → reddit_scraper.py → Database (Post model)
                                     ↓
                              (posted=False, status=pending)
```

### Video Generation Flow

```
Database → video_service.py → Select posts (score ≥ 500)
              ↓
          generator.py → Text Processing → text_cleaning.py
              ↓                              ↓
          TTS Audio ← prepare_text_for_tts() ← Expand contractions
              ↓
          Whisper AI → srt.py → Word-level timing + contraction mapping
              ↓
          FFmpeg Merge → Audio + Video + Subtitles
              ↓
          Speed 1.3x + Metadata
              ↓
          video_service.py (return video path)
```

### YouTube Upload Flow

```
video_service.py → youtube_service.py → OAuth Auth
                                          ↓
                                    Upload with metadata
                                          ↓
                                    Get video_id
                                          ↓
                                    Update database
                                          ↓
                                    Delete local file
```

### Automation Flow

```
APScheduler (5 PM, 9 PM) → automation/scheduler.py
                              ↓
                        video_service.process_batch(5)
                              ↓
                        For each post:
                          - Generate video
                          - Upload to YouTube
                          - Mark as posted
                          - Delete file
                              ↓
                        Log results (successful, failed)
```

## Configuration Files

### Environment Variables (`.env`)

```ini
DATABASE_URL=sqlite:///./stories.db
YOUTUBE_CLIENT_SECRETS_FILE=config/youtube_credentials.json
YOUTUBE_TOKEN_FILE=config/youtube_token.json
AUTOMATION_CONFIG_FILE=config/automation.yaml
LOG_LEVEL=INFO
LOG_FILE=logs/narrify.log
REDDIT_CLIENT_ID=xxx
REDDIT_CLIENT_SECRET=xxx
```

### Python Settings (`app/config.py`)

Pydantic-based settings management:

- Loads `.env` variables
- Parses `automation.yaml`
- Provides typed configuration objects

### Video Settings (`app/video/subtitle_config.py`)

```python
WORDS_PER_SUBTITLE_MIN = 2
WORDS_PER_SUBTITLE_MAX = 3
VIDEO_SPEED_MULTIPLIER = 1.3
AUDIO_ENHANCEMENT_LEVEL = "high"
NARRATE_TITLE = True
```

## Database Schema

### Post Table

```sql
CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    reddit_id TEXT UNIQUE,
    subreddit TEXT,
    title TEXT,
    story TEXT,
    score INTEGER,
    num_comments INTEGER,
    url TEXT,

    -- Generation tracking
    generation_status TEXT DEFAULT 'pending',
    generation_error TEXT,
    generated_at TIMESTAMP,

    -- YouTube tracking
    posted BOOLEAN DEFAULT 0,
    posted_at TIMESTAMP,
    youtube_video_id TEXT,
    upload_error TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Logging

### Log Levels

- **INFO**: Normal operations (uploads, generations)
- **WARNING**: Recoverable issues (retries, cleanup failures)
- **ERROR**: Failed operations (upload errors, generation failures)
- **DEBUG**: Detailed execution info

### Log Format

```
2025-10-22 17:00:15 - narrify - INFO - Video generation started | post_id=123 | reddit_id=abc123
2025-10-22 17:01:45 - narrify - INFO - YouTube upload completed | video_id=xyz789 | url=https://youtube.com/shorts/xyz789
```

### Log Rotation

- Max size: 10MB per file
- Backup count: 5 files
- Total storage: ~50MB

## Git Ignore

Files excluded from version control:

```
# Environment
.env
config/youtube_credentials.json
config/youtube_token.json

# Logs
logs/
*.log

# Media (generated files)
*.mp4
*.mp3
*.wav
*.srt

# Python
__pycache__/
*.pyc
venv/

# Database (optional)
# stories.db
```

## Dependencies

### Core

- `fastapi` - Web framework
- `sqlalchemy` - ORM
- `pydantic-settings` - Configuration
- `apscheduler` - Job scheduling

### Video/Audio

- `TTS` (Coqui) - Voice cloning
- `whisper` - Subtitle timing
- `ffmpeg-python` - Video processing

### APIs

- `google-api-python-client` - YouTube API
- `google-auth-oauthlib` - OAuth
- `praw` / `requests` - Reddit API

### Utilities

- `pyyaml` - Config parsing
- `python-dotenv` - Environment variables
- `pytz` - Timezone support

## Development vs Production

### Development

```bash
# Local SQLite database
python -m uvicorn app.main:app --reload --port 8000

# Manual testing
python scripts/run_automation.py --dry-run
```

### Production

```bash
# Use production WSGI server
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# Background process with systemd/supervisor
# Monitor logs: tail -f logs/narrify.log
# Database backups: daily cron job
```

## Security Considerations

1. **Never commit secrets**

   - `.env` in `.gitignore`
   - OAuth credentials in `config/` (ignored)

2. **YouTube API quota**

   - Monitor daily usage
   - Implement rate limiting

3. **Database access**

   - Use read-only user for queries
   - Regular backups

4. **File permissions**
   - Restrict config directory: `chmod 700 config/`
   - Secure credentials: `chmod 600 config/*.json`

## Maintenance Tasks

### Daily

- Monitor logs for errors
- Check YouTube upload success rate
- Verify disk space

### Weekly

- Review video performance on YouTube
- Check Reddit scraping quality
- Rotate old log files

### Monthly

- Database cleanup (old posts)
- Update dependencies
- Review YouTube analytics

## Future Enhancements

Planned features:

- [ ] Slack notifications for failures
- [ ] Video performance analytics dashboard
- [ ] Automatic thumbnail generation
- [ ] Multi-channel support
- [ ] Advanced scheduling (day-of-week specific)
- [ ] Retry logic with exponential backoff
- [ ] A/B testing for video styles

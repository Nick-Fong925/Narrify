# Narrify Quick Reference

## Installation

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
```

## First-Time Setup

### 1. YouTube API

```bash
# Get credentials from: https://console.cloud.google.com/
# Enable YouTube Data API v3
# Download OAuth credentials → save as config/youtube_credentials.json

# Run first-time auth (opens browser)
python scripts/upload_video.py --title "Test" test_video.mp4
```

### 2. Reddit API

```bash
# Create app at: https://www.reddit.com/prefs/apps
# Add to .env:
REDDIT_CLIENT_ID=your_id
REDDIT_CLIENT_SECRET=your_secret
```

## Daily Usage

### Start Server

```bash
python -m uvicorn app.main:app --reload --port 8000
```

### Manual Testing

```bash
# Preview what would be processed
python scripts/run_automation.py --dry-run

# Generate specific number of videos
python scripts/run_automation.py --count 3

# Upload single video
python scripts/upload_video.py --title "Story" --privacy public video.mp4
```

## Monitoring

### View Logs

```bash
# Real-time logs
tail -f logs/narrify.log

# Search errors
grep ERROR logs/narrify.log

# Count uploads today
grep "YouTube upload completed" logs/narrify.log | grep $(date +%Y-%m-%d) | wc -l
```

### Check Database

```python
from app.db import SessionLocal
from app.models.post import Post

db = SessionLocal()

# Posted count
posted = db.query(Post).filter(Post.posted == True).count()
print(f"Posted: {posted}")

# Pending count
pending = db.query(Post).filter(Post.posted == False).count()
print(f"Pending: {pending}")

# Recent uploads
recent = db.query(Post).filter(Post.posted == True).order_by(Post.posted_at.desc()).limit(5).all()
for p in recent:
    print(f"{p.title} - https://youtube.com/shorts/{p.youtube_video_id}")
```

## Configuration

### Schedule (config/automation.yaml)

```yaml
automation:
  videos_per_day: 10
  schedule_times: ["17:00", "21:00"] # 5 PM & 9 PM EST
  videos_per_batch: 5
```

### Video Settings (app/video/subtitle_config.py)

```python
WORDS_PER_SUBTITLE_MIN = 2
WORDS_PER_SUBTITLE_MAX = 3
VIDEO_SPEED_MULTIPLIER = 1.3
AUDIO_ENHANCEMENT_LEVEL = "high"  # off/low/medium/high/extreme
```

## Common Commands

### Development

```bash
# Install packages
pip install -r requirements.txt

# Activate venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate      # Windows

# Start dev server
python -m uvicorn app.main:app --reload
```

### Testing

```bash
# Run tests
python tests/test_video_generation.py
python tests/test_text_preprocessing.py

# Dry run automation
python scripts/run_automation.py --dry-run

# Generate 1 video for testing
python scripts/run_automation.py --count 1
```

### Database

```bash
# Backup
cp stories.db backups/stories_$(date +%Y%m%d).db

# Reset (CAUTION: deletes all data)
rm stories.db
python -m uvicorn app.main:app  # Creates new schema
```

## Troubleshooting

### YouTube Upload Fails

**Quota exceeded**

```bash
# Check: https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas
# Free tier: 10,000 units/day (~6 uploads)
# Solution: Apply for quota increase or reduce videos_per_day
```

**Invalid credentials**

```bash
# Delete token and re-authenticate
rm config/youtube_token.json
python scripts/upload_video.py --title "Test" test.mp4
```

### Video Generation Fails

**FFmpeg not found**

```bash
# Mac
brew install ffmpeg

# Ubuntu
sudo apt install ffmpeg

# Check
ffmpeg -version
```

**TTS model not loaded**

```bash
# First run downloads model automatically
# Check logs for download progress
tail -f logs/narrify.log
```

### Scheduler Not Running

**Check status**

```bash
# Look for these in logs:
grep "Automation scheduler started" logs/narrify.log
grep "Scheduled job" logs/narrify.log
```

**Manual trigger**

```bash
# Force run immediately
python scripts/run_automation.py
```

## API Endpoints

```bash
# Health check
curl http://localhost:8000/

# Get all posts
curl http://localhost:8000/api/posts

# Get posted videos
curl http://localhost:8000/api/posts?posted=true

# Get pending videos
curl http://localhost:8000/api/posts?posted=false

# Get post by ID
curl http://localhost:8000/api/posts/123
```

## File Locations

### Configuration

- `.env` - Environment variables
- `config/automation.yaml` - Automation settings
- `config/youtube_credentials.json` - OAuth secrets
- `app/video/subtitle_config.py` - Video settings

### Data

- `stories.db` - SQLite database
- `logs/narrify.log` - Application logs

### Generated (auto-cleanup)

- `app/video/media/generated_videos/*.mp4` - Temp videos (deleted after upload)

## Environment Variables

Required in `.env`:

```ini
DATABASE_URL=sqlite:///./stories.db
YOUTUBE_CLIENT_SECRETS_FILE=config/youtube_credentials.json
YOUTUBE_TOKEN_FILE=config/youtube_token.json
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
```

Optional:

```ini
LOG_LEVEL=INFO
LOG_FILE=logs/narrify.log
AUTOMATION_CONFIG_FILE=config/automation.yaml
```

## Automation Schedule

**Default: 10 videos/day**

- 5 PM EST: Generate + upload 5 videos
- 9 PM EST: Generate + upload 5 videos

**Selection criteria:**

- `posted=False` (not yet uploaded)
- `score >= 500` (high quality)
- Ordered by score (descending)

**After upload:**

- Mark `posted=True`
- Store `youtube_video_id`
- Record `posted_at` timestamp
- Delete local video file

## Performance Tips

### Optimize Generation Speed

1. Use base Whisper model (faster than large)
2. Keep audio enhancement at "high" (not "extreme")
3. Process in batches during off-peak hours

### Save Disk Space

1. Auto-cleanup enabled by default
2. Rotate logs regularly
3. Clean old database entries monthly

### Improve Upload Success

1. Monitor YouTube API quota
2. Implement exponential backoff (future)
3. Retry failed uploads in next batch

## Useful Queries

### Database

```python
from app.db import SessionLocal
from app.models.post import Post, GenerationStatus

db = SessionLocal()

# Failed generations
failed = db.query(Post).filter(Post.generation_status == GenerationStatus.FAILED.value).all()

# Today's uploads
from datetime import datetime, timedelta
today = datetime.utcnow().date()
uploads_today = db.query(Post).filter(
    Post.posted == True,
    Post.posted_at >= today
).count()

# Top performing posts (by score)
top = db.query(Post).order_by(Post.score.desc()).limit(10).all()
```

### Logs

```bash
# Errors in last hour
grep ERROR logs/narrify.log | tail -n 50

# Upload summary
grep "YouTube upload" logs/narrify.log | tail -n 20

# Generation times
grep "duration_seconds" logs/narrify.log | tail -n 10
```

## Support

📖 **Full Documentation**: `backend/docs/`

- `AUTOMATION_GUIDE.md` - Complete setup
- `PROJECT_STRUCTURE.md` - Architecture
- `AUDIO_OPTIMIZATIONS.md` - Audio settings
- `SUBTITLE_SYNC_GUIDE.md` - Subtitle details

🐛 **Issues**: Check logs first, then review documentation

💬 **Updates**: Check GitHub for latest features

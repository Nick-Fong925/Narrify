# Narrify Automation Setup Guide

## Overview

Narrify now includes a fully automated system that:

- **Generates videos** from top Reddit posts daily
- **Uploads to YouTube** automatically at scheduled times
- **Manages database** to track posting status
- **Cleans up** video files after upload to conserve space

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   FastAPI App                        │
│  ┌──────────────┐  ┌──────────────┐                │
│  │ API Layer    │  │ Automation   │                │
│  │ (endpoints)  │  │ Scheduler    │                │
│  └──────────────┘  └──────────────┘                │
│         │                  │                         │
│         ▼                  ▼                         │
│  ┌──────────────────────────────────────┐          │
│  │        Service Layer                  │          │
│  │  ┌──────────────┐  ┌───────────────┐ │          │
│  │  │ Video        │  │ YouTube       │ │          │
│  │  │ Service      │  │ Service       │ │          │
│  │  └──────────────┘  └───────────────┘ │          │
│  └──────────────────────────────────────┘          │
│         │                  │                         │
│         ▼                  ▼                         │
│  ┌──────────────────────────────────────┐          │
│  │        Data Layer                     │          │
│  │  - Post Model (SQLAlchemy)           │          │
│  │  - Database (SQLite)                 │          │
│  └──────────────────────────────────────┘          │
└─────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

New dependencies added:

- `google-api-python-client` - YouTube API client
- `google-auth-oauthlib` - OAuth authentication
- `pyyaml` - Configuration management
- `python-dotenv` - Environment variables
- `pydantic-settings` - Settings management
- `pytz` - Timezone support

### 2. Setup YouTube API

#### A. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g., "Narrify")
3. Enable **YouTube Data API v3**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "YouTube Data API v3"
   - Click "Enable"

#### B. Create OAuth Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Configure consent screen:
   - User type: External
   - Add your email
   - Add scopes: `https://www.googleapis.com/auth/youtube.upload`
4. Create OAuth 2.0 Client ID:
   - Application type: Desktop app
   - Name: "Narrify Desktop"
5. Download credentials JSON file
6. Save as `config/youtube_credentials.json`

#### C. First-Time Authentication

```bash
# Run manual upload to trigger OAuth flow
python scripts/upload_video.py \
    --title "Test Video" \
    path/to/test_video.mp4
```

This will:

- Open your browser
- Ask you to grant permissions
- Save credentials to `config/youtube_token.json`

### 3. Configure Environment

Create `.env` file (use `.env.example` as template):

```bash
cp .env.example .env
```

Edit `.env`:

```ini
DATABASE_URL=sqlite:///./stories.db
YOUTUBE_CLIENT_SECRETS_FILE=config/youtube_credentials.json
YOUTUBE_TOKEN_FILE=config/youtube_token.json
AUTOMATION_CONFIG_FILE=config/automation.yaml
LOG_LEVEL=INFO
LOG_FILE=logs/narrify.log

# Reddit API (for scraping)
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=Narrify Video Bot v1.0
```

### 4. Configure Automation

Edit `config/automation.yaml` to customize:

```yaml
automation:
  videos_per_day: 10
  schedule_times:
    - "17:00" # 5 PM EST
    - "21:00" # 9 PM EST
  videos_per_batch: 5

youtube:
  privacy: "public"
  title_suffix: " #shorts"

video:
  delete_after_upload: true
```

### 5. Database Migration

The Post model now includes automation fields:

- `posted` - Boolean flag for YouTube posting status
- `posted_at` - Timestamp of upload
- `youtube_video_id` - YouTube video ID
- `generation_status` - Video generation status (pending/processing/completed/failed)

**Important:** If you have existing data, you may need to recreate the database:

```bash
# Backup existing database
cp stories.db stories.db.backup

# Delete and recreate (will lose data)
rm stories.db

# Start app to create new schema
python -m uvicorn app.main:app --reload
```

### 6. Start the Application

```bash
# Start FastAPI server
python -m uvicorn app.main:app --reload --port 8000
```

The automation scheduler will start automatically and run at configured times.

## Manual Testing

### Test Automation (Dry Run)

```bash
# See what would be processed without generating videos
python scripts/run_automation.py --dry-run
```

### Run Automation Immediately

```bash
# Generate and upload default number of videos
python scripts/run_automation.py

# Generate and upload specific number
python scripts/run_automation.py --count 3
```

### Upload Single Video

```bash
python scripts/upload_video.py \
    --title "My Reddit Story" \
    --description "Check out this story from r/AmItheAsshole" \
    --tags reddit story aita \
    --privacy public \
    path/to/video.mp4
```

## How It Works

### Daily Schedule

**Default Schedule (EST):**

- **5:00 PM** - Generate and upload 5 videos
- **9:00 PM** - Generate and upload 5 videos

### Selection Criteria

Videos are generated from posts that:

- Have `posted=False` (not yet posted to YouTube)
- Have `generation_status` of `pending` or `failed`
- Have score >= 500 (configurable)
- Are ordered by score (highest first)

### Processing Pipeline

For each batch:

1. **Select Posts**

   - Query database for top N unpublished posts
   - Order by Reddit score (descending)

2. **Generate Video**

   - Update status to `processing`
   - Call video generation pipeline
   - Create audio with voice cloning
   - Generate subtitles with Whisper
   - Merge audio + video + subtitles
   - Speed up to 1.3x
   - Mark status as `completed`

3. **Upload to YouTube**

   - Generate metadata (title, description, tags)
   - Upload with YouTube API
   - Add "#shorts" to title
   - Store YouTube video ID

4. **Cleanup**

   - Delete video file from local storage
   - Mark post as `posted=True`
   - Update `posted_at` timestamp

5. **Error Handling**
   - Log all errors
   - Store error messages in database
   - Failed posts can be retried in next batch

## Monitoring

### Logs

All operations are logged to `logs/narrify.log`:

```bash
# View logs in real-time
tail -f logs/narrify.log

# Search for errors
grep ERROR logs/narrify.log

# View YouTube uploads
grep "YouTube upload" logs/narrify.log
```

### Database Queries

```python
from app.db import SessionLocal
from app.models.post import Post

db = SessionLocal()

# Check posted videos
posted = db.query(Post).filter(Post.posted == True).count()
print(f"Posted: {posted}")

# Check pending videos
pending = db.query(Post).filter(Post.posted == False).count()
print(f"Pending: {pending}")

# View recent uploads
recent = db.query(Post).filter(
    Post.posted == True
).order_by(
    Post.posted_at.desc()
).limit(5).all()

for post in recent:
    print(f"{post.title} - {post.youtube_video_id}")
```

## Configuration Options

### `config/automation.yaml`

| Setting                     | Description                             | Default            |
| --------------------------- | --------------------------------------- | ------------------ |
| `automation.videos_per_day` | Total videos per day                    | 10                 |
| `automation.schedule_times` | Posting times (24h format)              | ["17:00", "21:00"] |
| `automation.timezone`       | Timezone for scheduling                 | America/New_York   |
| `youtube.privacy`           | Video privacy (public/unlisted/private) | public             |
| `youtube.title_suffix`      | Text added to all titles                | " #shorts"         |
| `video.delete_after_upload` | Delete video files after upload         | true               |

### Environment Variables (`.env`)

| Variable                      | Description                      | Required           |
| ----------------------------- | -------------------------------- | ------------------ |
| `DATABASE_URL`                | SQLite database path             | Yes                |
| `YOUTUBE_CLIENT_SECRETS_FILE` | OAuth credentials file           | Yes                |
| `YOUTUBE_TOKEN_FILE`          | OAuth token storage              | Yes                |
| `LOG_LEVEL`                   | Logging level (INFO/DEBUG/ERROR) | No                 |
| `REDDIT_CLIENT_ID`            | Reddit API client ID             | Yes (for scraping) |
| `REDDIT_CLIENT_SECRET`        | Reddit API secret                | Yes (for scraping) |

## Troubleshooting

### YouTube Upload Fails

**Error:** `quota_exceeded`

- YouTube API has daily quota limits
- Free tier: 10,000 units/day
- Upload costs ~1,600 units
- Solution: Apply for quota increase or reduce videos_per_day

**Error:** `invalid_credentials`

- Delete `config/youtube_token.json`
- Re-run authentication flow

### Video Generation Fails

Check logs for specific errors:

```bash
grep "Video generation failed" logs/narrify.log
```

Common issues:

- TTS model not downloaded
- FFmpeg not installed
- Insufficient disk space

### Scheduler Not Running

Check if scheduler started:

```bash
grep "Automation scheduler started" logs/narrify.log
```

Verify scheduled jobs:

```bash
grep "Scheduled job" logs/narrify.log
```

### Database Issues

If you see column errors after update:

```bash
# Recreate database with new schema
rm stories.db
python -m uvicorn app.main:app
```

## Best Practices

1. **Monitor Logs Daily**

   - Check for upload failures
   - Track generation errors
   - Monitor quota usage

2. **Backup Database**

   ```bash
   cp stories.db backups/stories_$(date +%Y%m%d).db
   ```

3. **Test Before Production**

   - Use `--dry-run` to preview
   - Start with `privacy: unlisted`
   - Gradually increase video count

4. **Manage Disk Space**

   - Videos auto-delete after upload
   - Rotate log files regularly
   - Clean old database entries

5. **YouTube Optimization**
   - Use relevant tags
   - Write engaging descriptions
   - Monitor video performance
   - Adjust posting times based on analytics

## API Endpoints

The automation system is fully automated, but you can still use the API:

```bash
# Check health
curl http://localhost:8000/

# Get all posts
curl http://localhost:8000/api/posts

# Get posted videos
curl http://localhost:8000/api/posts?posted=true

# Get pending videos
curl http://localhost:8000/api/posts?posted=false
```

## Support

For issues or questions:

1. Check logs first: `logs/narrify.log`
2. Review configuration: `config/automation.yaml`
3. Verify OAuth credentials are valid
4. Test with manual scripts before automation

## Next Steps

Future enhancements (not yet implemented):

- Slack notifications for failures
- Video performance analytics
- Automatic thumbnail generation
- Multi-channel support
- Advanced scheduling (different times per day of week)
- Retry logic with exponential backoff

# Narrify — Automated Reddit Story Video Generator

Narrify is a fully automated pipeline that scrapes top Reddit horror/story posts, generates YouTube Shorts with GPU-accelerated TTS narration and word-synced subtitles, and schedules them to publish automatically.

## How It Works

1. **Scrape** — Fetches top posts from `shortscarystories` and `scarystories`, filtered by score (≥200), engagement composite, and word count (≥150)
2. **Generate** — Converts each story to a YouTube Short: Kokoro TTS narration → Whisper subtitles → FFmpeg encode over Minecraft parkour base video (9:16, 1.8× speed, NVENC)
3. **Upload** — Posts to YouTube as scheduled (next day at 8 PM), then deletes the local file
4. **Automate** — Runs daily at 5 AM via APScheduler (Docker) or Windows Task Scheduler (standalone)

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| Database | SQLAlchemy + SQLite |
| TTS | Kokoro (`am_onyx` voice, CUDA) |
| Transcription | Faster-Whisper `large-v3` (CUDA, int8) |
| Video | FFmpeg + NVENC hardware encoding |
| YouTube | Google API Python Client (OAuth 2.0) |
| AI Text Processing | Anthropic Claude API |
| Scheduling | APScheduler |
| Deployment | Docker + NVIDIA CUDA 12.1 |

---

## Project Structure

```
Narrify/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app + scheduler startup
│   │   ├── config.py                # Pydantic settings
│   │   ├── db.py                    # SQLAlchemy setup
│   │   ├── scheduler.py             # scheduled_scrape()
│   │   ├── api/endpoints.py         # REST endpoints
│   │   ├── models/                  # Post DB model
│   │   ├── services/
│   │   │   ├── reddit_scraper.py    # Reddit API fetching
│   │   │   ├── video_service.py     # Video generation orchestration
│   │   │   ├── youtube_service.py   # YouTube upload + OAuth
│   │   │   ├── upload_service.py    # Batch queue processing
│   │   │   └── post_selector.py     # Post ranking/selection
│   │   ├── video/
│   │   │   ├── generator.py         # Full video pipeline
│   │   │   ├── tts.py               # Kokoro TTS
│   │   │   ├── srt.py               # Whisper → SRT subtitles
│   │   │   └── ffmpeg_utils.py      # Encoding helpers
│   │   └── utils/
│   │       ├── logger.py
│   │       └── text_cleaning.py
│   ├── automation/
│   │   └── scheduler.py             # APScheduler orchestration
│   ├── scripts/
│   │   ├── generate_and_upload_one.py  # Manually run one video
│   │   ├── run_nightly.py              # Standalone nightly pipeline
│   │   └── run_nightly.bat             # Task Scheduler launcher
│   ├── config/                      # Credentials + YAML config (gitignored)
│   ├── logs/
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Prerequisites

- Python 3.10+
- NVIDIA GPU (tested on RTX 3060, 8 GB VRAM)
- FFmpeg installed on host (Docker includes it)
- [Google Cloud project](https://console.cloud.google.com/) with YouTube Data API v3 enabled
- Reddit API credentials
- Anthropic API key

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/Nick-Fong925/Narrify.git
cd Narrify/backend
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

### 2. Environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```ini
ANTHROPIC_API_KEY=your_anthropic_key
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=Narrify/1.0
```

### 3. YouTube credentials

- Download OAuth 2.0 client secrets from Google Cloud Console
- Save as `backend/config/youtube_credentials.json`
- First run will open a browser for authorization and save `config/youtube_token.json`

### 4. Base video

Place a vertical (9:16) background video at:

```
backend/app/video/media/base_videos/minecraft_parkour_base.mp4
```

### 5. Configure automation

Edit `backend/config/automation.yaml`:

```yaml
automation:
  schedule_times: ["05:00"]        # 24h, runs daily
  timezone: "America/New_York"
  videos_per_batch: 5

youtube:
  privacy: "private"               # videos publish automatically next day
  publish_hour: 20                 # 8 PM
  publish_days_ahead: 1

video:
  whisper_model: "large-v3"
  kokoro_voice: "am_onyx"
  video_speed_multiplier: 1.8
  audio_enhancement_level: "extreme"

database:
  min_score_threshold: 200
  min_word_count: 150
```

---

## Running

### Docker (recommended)

```bash
# Build and start
docker compose up -d

# Follow logs
docker compose logs -f narrify

# Stop
docker compose down
```

The container automatically starts the daily scheduler at the configured time.

> Requires [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) for GPU access.

### Local (development)

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

### Nightly automation via Windows Task Scheduler

For a sleep-friendly setup where the PC wakes at 5 AM, runs the pipeline, then goes back to sleep:

1. Open **Task Scheduler** → Create Task
2. **General**: Run whether user is logged on or not, Run with highest privileges
3. **Triggers**: Daily at `5:00 AM`, check **Wake the computer to run this task**
4. **Actions**: Program: `C:\Projects\Narrify\backend\scripts\run_nightly.bat`
5. **Settings**: If already running → Stop the existing instance

Manual test:
```bash
cd backend
python scripts/run_nightly.py --count 1
# Output: logs/nightly.log
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Health check |
| POST | `/api/scrape/` | Manually trigger Reddit scrape |
| GET | `/api/posts/` | List stored posts |
| DELETE | `/api/posts/` | Clear all posts |
| GET | `/api/counts/` | Post counts by subreddit |
| POST | `/api/video/` | Generate video from post ID or raw text |
| GET | `/api/video/highest-score/` | Generate from top-scoring post |
| GET | `/api/video/bases/` | List available base videos |

---

## Manual Scripts

```bash
# Generate + upload the highest-scoring unposted story
python scripts/generate_and_upload_one.py

# Generate + upload a specific post by DB ID
python scripts/generate_and_upload_one.py --post-id 42

# Run the full nightly pipeline manually
python scripts/run_nightly.py

# Override video count
python scripts/run_nightly.py --count 3
```

---

## Monitoring

```bash
# Live logs (Docker)
docker compose logs -f narrify

# Live logs (local)
tail -f backend/logs/narrify.log

# Nightly run log
tail -f backend/logs/nightly.log

# Count successful uploads
grep "YouTube upload completed" backend/logs/narrify.log | wc -l

# View errors
grep ERROR backend/logs/narrify.log
```

---

## Troubleshooting

**YouTube quota exceeded**
- Free tier: 10,000 units/day (~6 uploads)
- The pending queue retries automatically on the next run
- Apply for quota increase in Google Cloud Console

**Re-authenticate YouTube**
- Delete `config/youtube_token.json`
- Restart the app — browser auth flow will trigger

**GPU out of memory**
- Whisper and Kokoro both load on GPU simultaneously (~6 GB VRAM)
- Reduce Whisper model: change `whisper_model` to `medium` in `automation.yaml`

**Video generation fails**
- Check FFmpeg is installed: `ffmpeg -version`
- Verify base video exists at `app/video/media/base_videos/`
- Check `logs/narrify.log` for the specific error

---

## Notes

- Videos are scheduled for publication, not immediately public — they appear as "Scheduled" in YouTube Studio
- Generated video files are deleted after successful upload to save disk space; failed uploads stay in `app/video/media/pending_uploads/` and are retried next run
- Wake from sleep (Task Scheduler) requires the PC to be in **sleep mode**, not fully powered off

---

## License

MIT License

## Author

Created by [Nick Fong](https://github.com/Nick-Fong925)

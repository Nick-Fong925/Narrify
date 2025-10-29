# Narrify - Automated Reddit Story Video Generator

**Narrify** is a fully automated system that transforms top Reddit stories into engaging YouTube Shorts with professional voice narration, synchronized subtitles, and automatic posting.

## ✨ Features

- 🎙️ **Voice Cloning TTS** - Natural-sounding narration using XTTS v2
- 📝 **Smart Text Processing** - Handles contractions, Reddit slang, and age/gender patterns
- 🎬 **Professional Subtitles** - Word-level synchronized subtitles with Whisper AI
- 🚀 **Automated YouTube Upload** - Scheduled posting at optimal times
- 🎨 **Multi-level Audio Enhancement** - Crystal-clear voice quality
- 🤖 **Fully Automated** - Daily scraping, generation, and posting
- 💾 **Space Efficient** - Auto-cleanup after upload

## 🏗️ Project Structure

```
Narrify/
├── backend/
│   ├── app/                      # Main application
│   │   ├── api/                  # FastAPI endpoints
│   │   ├── models/               # Database models
│   │   ├── services/             # Business logic
│   │   │   ├── reddit_scraper.py
│   │   │   ├── video_service.py
│   │   │   └── youtube_service.py
│   │   ├── utils/                # Utilities
│   │   │   ├── logger.py
│   │   │   └── text_cleaning.py
│   │   ├── video/                # Video generation
│   │   │   ├── generator.py
│   │   │   ├── tts.py
│   │   │   ├── srt.py
│   │   │   └── subtitle_config.py
│   │   ├── config.py             # Configuration management
│   │   └── main.py               # FastAPI app
│   ├── automation/               # Automation system
│   │   └── scheduler.py
│   ├── config/                   # Configuration files
│   │   └── automation.yaml
│   ├── docs/                     # Documentation
│   │   ├── AUTOMATION_GUIDE.md
│   │   ├── AUDIO_OPTIMIZATIONS.md
│   │   └── ...
│   ├── scripts/                  # CLI utilities
│   │   ├── run_automation.py
│   │   └── upload_video.py
│   ├── tests/                    # Test files
│   └── requirements.txt
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- FFmpeg (for video processing)
- Google Cloud Project (for YouTube API)
- Reddit API credentials

### Installation

```bash
# Clone repository
git clone https://github.com/Nick-Fong925/Narrify.git
cd Narrify/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your API credentials
```

### Configuration

1. **YouTube API Setup**

   - Create project at [Google Cloud Console](https://console.cloud.google.com/)
   - Enable YouTube Data API v3
   - Download OAuth credentials → save as `config/youtube_credentials.json`
   - Run first-time auth: `python scripts/upload_video.py --title "Test" test.mp4`

2. **Reddit API Setup**

   - Create app at [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
   - Add credentials to `.env`

3. **Configure Automation**
   - Edit `config/automation.yaml` to set posting schedule
   - Default: 5 PM and 9 PM EST, 5 videos each

### Running

```bash
# Start application (includes automation scheduler)
python -m uvicorn app.main:app --reload --port 8000

# Or run automation manually
python scripts/run_automation.py

# Dry run (preview without generating)
python scripts/run_automation.py --dry-run
```

## 📊 How It Works

### Daily Workflow

1. **Reddit Scraping** (Daily)

   - Scrapes top posts from 5 subreddits
   - Filters by score (≥500) and word count (≥150)
   - Stores in database

2. **Automated Video Generation** (5 PM & 9 PM EST)

   - Selects top 5 unpublished posts by score
   - Generates videos with:
     - Voice cloning (XTTS v2)
     - Professional subtitles (Whisper AI)
     - 1.3x speed optimization
     - Multi-level audio enhancement

3. **YouTube Upload**
   - Uploads with optimized metadata
   - Adds #shorts hashtag
   - Marks as posted in database
   - **Deletes video file** to save space

### Video Generation Pipeline

```
Reddit Post → Text Processing → TTS Audio → Whisper Subtitles
    ↓              ↓                ↓              ↓
Database    Clean contractions   Voice clone   Word timing
             Handle slang         Enhancement   Sync mapping
    ↓              ↓                ↓              ↓
    └──────────→ Video Merge ←─────┴──────────────┘
                    ↓
              Speed 1.3x + Metadata
                    ↓
            YouTube Upload → Cleanup
```

## 📖 Documentation

Comprehensive guides in `backend/docs/`:

- **[AUTOMATION_GUIDE.md](backend/docs/AUTOMATION_GUIDE.md)** - Complete setup and configuration
- **[AUDIO_OPTIMIZATIONS.md](backend/docs/AUDIO_OPTIMIZATIONS.md)** - Audio enhancement details
- **[SUBTITLE_SYNC_GUIDE.md](backend/docs/SUBTITLE_SYNC_GUIDE.md)** - Subtitle synchronization
- **[TEXT_PREPROCESSING_STRATEGY.md](backend/docs/TEXT_PREPROCESSING_STRATEGY.md)** - Text processing logic

## 🛠️ Tech Stack

- **Backend**: FastAPI, SQLAlchemy, APScheduler
- **TTS**: XTTS v2 (voice cloning), Coqui TTS
- **Video**: FFmpeg, Whisper AI
- **APIs**: YouTube Data API v3, Reddit API
- **Database**: SQLite

## 📈 Key Features

### Text Processing

- Expands 50+ contractions for clear speech
- Handles Reddit slang (AITA, TIFU, SO, etc.)
- Converts age/gender patterns (17M → "seventeen M")
- Maintains original text for subtitles

### Subtitle System

- Word-level timing with Whisper
- Contraction mapping for perfect sync
- Configurable phrase grouping (2-3 words)
- Punctuation-aware breaks

### Audio Enhancement

5 quality levels (off/low/medium/high/extreme):

- Multi-band EQ (8-10 bands)
- De-esser for sibilance
- Dynamic compression
- Harmonic exciter
- Clarity boost at 2-4kHz

### Automation

- Configurable schedule (YAML)
- Error logging and tracking
- Retry logic for failures
- Automatic cleanup
- Database status tracking

## 🎯 Configuration

### `config/automation.yaml`

```yaml
automation:
  videos_per_day: 10
  schedule_times: ["17:00", "21:00"] # 5 PM & 9 PM EST

youtube:
  privacy: "public"
  title_suffix: " #shorts"

video:
  delete_after_upload: true
```

### `.env`

```ini
DATABASE_URL=sqlite:///./stories.db
YOUTUBE_CLIENT_SECRETS_FILE=config/youtube_credentials.json
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_secret
LOG_LEVEL=INFO
```

## 🧪 Testing

```bash
# Dry run automation
python scripts/run_automation.py --dry-run

# Generate specific number
python scripts/run_automation.py --count 3

# Manual upload
python scripts/upload_video.py \
    --title "My Story" \
    --privacy public \
    video.mp4
```

## 📊 Monitoring

```bash
# View logs
tail -f logs/narrify.log

# Check posted count
grep "YouTube upload completed" logs/narrify.log | wc -l

# View errors
grep ERROR logs/narrify.log
```

## 🐛 Troubleshooting

**YouTube quota exceeded**

- Free tier: 10,000 units/day (~6 videos)
- Apply for quota increase

**Authentication errors**

- Delete `config/youtube_token.json`
- Re-run authentication flow

**Video generation fails**

- Check FFmpeg installation
- Verify TTS model downloaded
- Check disk space

See [AUTOMATION_GUIDE.md](backend/docs/AUTOMATION_GUIDE.md) for detailed troubleshooting.

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Test thoroughly
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Coqui TTS** - Voice cloning technology
- **OpenAI Whisper** - Subtitle timing
- **FFmpeg** - Video processing
- **FastAPI** - Backend framework

## 📬 Contact

Created by [Nick Fong](https://github.com/Nick-Fong925)

---

**⚠️ Note**: Respect Reddit's API terms and YouTube's content policies. Always verify you have rights to the content you're posting.

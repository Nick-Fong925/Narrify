# Horizontal Scaling: Multi-Channel Architecture

This document outlines how to scale Narrify to run multiple independent instances, each targeting different subreddits and posting to a separate YouTube channel — using a single codebase and single Docker image.

---

## Overview

Each "instance" is isolated by its own:
- `config/automation.yaml` — subreddits, schedule time, YouTube metadata
- `config/youtube_credentials.json` + `config/youtube_token.json` — per-channel OAuth
- `stories.db` — independent post history
- `media/` and `logs/` directories

The shared codebase and Docker image require no changes between instances.

---

## What Needs to Change in the Code

Currently 5 values are hardcoded in `backend/app/scheduler.py:13-29` and must move to config. Everything else (`automation`, `youtube`, `video`, `database`) is already YAML-driven.

### 1. Add `ScrapingSettings` class — `backend/app/config.py`

Add after `DatabaseSettings`, before `Settings`:

```python
class ScrapingSettings(BaseSettings):
    subreddits: List[str] = Field(default=["shortscarystories", "scarystories"])
    min_score_floor: int = 200
    min_composite: int = 800
    min_words: int = 150
    time_filter: str = "year"
    limit: int = 100
```

In the `Settings` class body, add:

```python
scraping: Optional[ScrapingSettings] = None
```

In `load_automation_config()`, wire it up in both branches:

```python
# YAML branch:
self.scraping = ScrapingSettings(**config_data.get('scraping', {}))

# No-file branch:
self.scraping = ScrapingSettings()
```

### 2. Update `backend/app/scheduler.py` — replace hardcoded locals

```python
from app.config import settings  # add at top

# Inside scheduled_scrape(), replace lines 13-19:
subreddits     = settings.scraping.subreddits
min_score_floor = settings.scraping.min_score_floor
min_composite  = settings.scraping.min_composite
min_words      = settings.scraping.min_words

# Update the fetch_top_posts call (line 29):
posts = scraper.fetch_top_posts(
    time_filter=settings.scraping.time_filter,
    limit=settings.scraping.limit,
)
```

### 3. Add `scraping:` section to `backend/config/automation.yaml`

```yaml
scraping:
  subreddits:
    - "shortscarystories"
    - "scarystories"
  min_score_floor: 200
  min_composite: 800
  min_words: 150
```

### 4. Replace `docker-compose.yml` with multi-service YAML anchor pattern

```yaml
# Run nightly pipeline manually:
#   docker exec narrify_scary python scripts/run_nightly.py --count 10
# View logs:
#   docker logs narrify_scary -f

x-narrify-base: &narrify-base
  build:
    context: ./backend
  restart: unless-stopped
  env_file: .env
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]

services:
  narrify_scary:
    <<: *narrify-base
    container_name: narrify_scary
    ports:
      - "8001:8000"
    volumes:
      - ./instances/scary/config:/app/config
      - ./instances/scary/stories.db:/app/stories.db
      - ./instances/scary/media:/app/app/video/media
      - ./instances/scary/logs:/app/logs

  narrify_aita:
    <<: *narrify-base
    container_name: narrify_aita
    ports:
      - "8002:8000"
    volumes:
      - ./instances/aita/config:/app/config
      - ./instances/aita/stories.db:/app/stories.db
      - ./instances/aita/media:/app/app/video/media
      - ./instances/aita/logs:/app/logs
```

---

## Instance Directory Structure

```
instances/
├── scary/
│   ├── config/
│   │   ├── automation.yaml           # scary-specific config
│   │   ├── youtube_credentials.json  # OAuth client secrets (from Google Cloud)
│   │   └── youtube_token.json        # Generated on first auth run
│   ├── stories.db                    # touch this before first docker compose up
│   ├── media/
│   └── logs/
└── aita/
    ├── config/
    │   ├── automation.yaml
    │   ├── youtube_credentials.json
    │   └── youtube_token.json
    ├── stories.db
    ├── media/
    └── logs/
```

### Example `instances/aita/config/automation.yaml`

```yaml
automation:
  schedule_times: ["07:00"]
  timezone: "America/Los_Angeles"
  videos_per_batch: 3

scraping:
  subreddits:
    - "AmItheAsshole"
    - "AITAH"
  min_score_floor: 500
  min_composite: 1500

youtube:
  privacy: "private"
  publish_hour: 18
  title_suffix: " #shorts"
  default_tags: ["shorts", "reddit", "aita"]
```

---

## YouTube OAuth Bootstrap (per new instance)

Each instance needs its own `youtube_credentials.json` bound to a separate YouTube channel's Google Cloud OAuth app.

1. Go to Google Cloud Console → create or select an OAuth 2.0 client ID for the target channel
2. Download `youtube_credentials.json` → place in `instances/<name>/config/`
3. Create an empty database file:
   ```bash
   touch instances/<name>/stories.db
   ```
4. Start the container temporarily to trigger the OAuth browser flow:
   ```bash
   docker compose run --rm --service-ports narrify_<name>
   ```
   Complete the browser auth → `youtube_token.json` is written to the mounted config directory
5. Start normally:
   ```bash
   docker compose up -d narrify_<name>
   ```

---

## Adding a Third Channel (Zero Code Changes)

Once the code changes above are in place, adding any new channel is:

1. Create `instances/<name>/config/automation.yaml` with target subreddits + schedule
2. Place `youtube_credentials.json` for the new YouTube channel
3. `touch instances/<name>/stories.db`
4. Add a 9-line service block to `docker-compose.yml` (copy an existing one, change name/port/paths)
5. Bootstrap YouTube OAuth (one-time)
6. `docker compose up -d narrify_<name>`

---

## GPU Contention Note

Both containers reserve the same physical GPU (`count: 1`). If batch jobs overlap (e.g., both triggered at the same time), they will compete for VRAM and likely OOM.

**Mitigation:** Stagger `schedule_times` in each instance's `automation.yaml` by at least 1-2 hours (e.g., scary at `05:00`, aita at `07:00`). Manual runs should not be triggered on both instances simultaneously.

A proper mutex or job queue is out of scope for now.

---

## Verification & Testing

### 1. Config loading
```bash
docker compose run --rm narrify_scary python -c "
from app.config import settings
print('subreddits:', settings.scraping.subreddits)
print('schedule:', settings.automation.schedule_times)
print('youtube tags:', settings.youtube.default_tags)
"
```
Repeat for `narrify_aita` — should show different values.

### 2. Database isolation
```bash
# After a scrape run on each:
docker exec narrify_scary sqlite3 /app/stories.db "SELECT COUNT(*) FROM posts;"
docker exec narrify_aita  sqlite3 /app/stories.db "SELECT COUNT(*) FROM posts;"
# Each should have posts from their respective subreddits only
```

### 3. Manual nightly run (small batch)
```bash
docker exec narrify_scary python scripts/run_nightly.py --count 2
docker exec narrify_aita  python scripts/run_nightly.py --count 2
# Run sequentially, not simultaneously, to avoid GPU contention
```

### 4. Log verification
```bash
docker logs narrify_scary --tail 50
# Should show: "Scraping r/shortscarystories..." and "Scraping r/scarystories..."

docker logs narrify_aita --tail 50
# Should show: "Scraping r/AmItheAsshole..." and "Scraping r/AITAH..."
```

### 5. YouTube upload check
After a successful batch, verify each container uploaded to the correct channel by checking the YouTube Studio for each account.

---

## Critical Files Reference

| File | Change Required |
|------|----------------|
| `backend/app/config.py` | Add `ScrapingSettings` class, wire into `Settings` |
| `backend/app/scheduler.py` | Replace 5 hardcoded values with `settings.scraping.*` |
| `backend/config/automation.yaml` | Add `scraping:` section (becomes instance template) |
| `docker-compose.yml` | Replace with YAML anchor multi-service pattern |

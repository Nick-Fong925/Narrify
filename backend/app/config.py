from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List, Optional
import yaml
from pathlib import Path


class VideoSettings(BaseSettings):
    # Subtitle grouping
    words_per_subtitle_min: int = 2
    words_per_subtitle_max: int = 3
    subtitle_gap_seconds: float = 0.7
    min_subtitle_duration: float = 2.1
    break_punctuation: str = ".!?,;:"

    # Whisper (faster-whisper)
    whisper_model: str = "large-v3"
    whisper_device: str = "cuda"
    whisper_compute_type: str = "int8"

    # Video speed / encoding
    video_speed_multiplier: float = 1.8
    use_nvenc: bool = True
    video_crf: int = 20
    video_preset: str = "fast"
    video_bitrate_max: str = "8M"

    # Title narration
    narrate_title: bool = True
    title_pause_after: float = 0.5

    # Audio
    audio_enhancement_level: str = "extreme"
    audio_bitrate: str = "192k"

    # Kokoro TTS
    kokoro_voice: str = "am_onyx"
    kokoro_sample_rate: int = 24000
    kokoro_speed: float = 0.85


class AutomationSettings(BaseSettings):
    videos_per_day: int = 5
    schedule_times: List[str] = Field(default=["05:00"])
    timezone: str = "America/New_York"
    videos_per_batch: int = 5
    analytics_time: str = "08:00"


class YouTubeSettings(BaseSettings):
    privacy: str = "private"
    title_suffix: str = " #shorts"
    category_id: str = "24"
    default_tags: List[str] = Field(default=["shorts", "reddit", "story"])
    publish_hour: int = 20
    publish_minute: int = 0
    publish_days_ahead: int = 1


class DatabaseSettings(BaseSettings):
    after_posting: str = "mark_posted"
    min_score_threshold: int = 200
    min_word_count: int = 150
    retention_days: int = 90


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    database_url: str = Field(default="sqlite:///./stories.db")
    youtube_client_secrets_file: str = Field(default="config/youtube_credentials.json")
    youtube_token_file: str = Field(default="config/youtube_token.json")
    automation_config_file: str = Field(default="config/automation.yaml")
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="logs/narrify.log")
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    reddit_user_agent: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    ntfy_topic: Optional[str] = Field(default=None)
    automation: Optional[AutomationSettings] = None
    youtube: Optional[YouTubeSettings] = None
    database: Optional[DatabaseSettings] = None
    video: Optional[VideoSettings] = None

    def load_automation_config(self) -> None:
        config_path = Path(self.automation_config_file)
        if not config_path.exists():
            self.automation = AutomationSettings()
            self.youtube = YouTubeSettings()
            self.database = DatabaseSettings()
            self.video = VideoSettings()
            return
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        self.automation = AutomationSettings(**config_data.get('automation', {}))
        self.youtube = YouTubeSettings(**config_data.get('youtube', {}))
        self.database = DatabaseSettings(**config_data.get('database', {}))
        self.video = VideoSettings(**config_data.get('video', {}))

    def model_post_init(self, __context) -> None:
        self.load_automation_config()


settings = Settings()

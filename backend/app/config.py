"""
Centralized configuration management for Narrify automation system.
Uses pydantic-settings for environment variable handling and YAML config loading.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List, Optional
import yaml
from pathlib import Path


class AutomationSettings(BaseSettings):
    """Automation-related settings from YAML config"""
    videos_per_day: int = 10
    schedule_times: List[str] = Field(default=["17:00", "21:00"])  # 5 PM and 9 PM EST
    timezone: str = "America/New_York"
    videos_per_batch: int = 5  # Videos to generate per scheduled time


class YouTubeSettings(BaseSettings):
    """YouTube upload settings"""
    privacy: str = "public"
    title_suffix: str = " #shorts"
    category_id: str = "24"  # Entertainment category
    default_tags: List[str] = Field(default=["shorts", "reddit", "story"])


class DatabaseSettings(BaseSettings):
    """Database settings"""
    after_posting: str = "mark_posted"  # Options: mark_posted, delete
    min_score_threshold: int = 500  # Minimum score for video generation
    min_word_count: int = 150  # Minimum word count for stories
    retention_days: int = 90  # Days to keep posted records


class Settings(BaseSettings):
    """Main application settings"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database
    database_url: str = Field(default="sqlite:///./stories.db")
    
    # YouTube OAuth
    youtube_client_secrets_file: str = Field(default="config/youtube_credentials.json")
    youtube_token_file: str = Field(default="config/youtube_token.json")
    
    # Automation config file
    automation_config_file: str = Field(default="config/automation.yaml")
    
    # Logging
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="logs/narrify.log")
    
    # Reddit API (existing)
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    reddit_user_agent: Optional[str] = None
    
    # Sub-settings (loaded from YAML)
    automation: Optional[AutomationSettings] = None
    youtube: Optional[YouTubeSettings] = None
    database: Optional[DatabaseSettings] = None
    
    def load_automation_config(self) -> None:
        """Load automation settings from YAML file"""
        config_path = Path(self.automation_config_file)
        
        if not config_path.exists():
            # Use defaults if config file doesn't exist
            self.automation = AutomationSettings()
            self.youtube = YouTubeSettings()
            self.database = DatabaseSettings()
            return
        
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Load sub-settings from YAML
        self.automation = AutomationSettings(**config_data.get('automation', {}))
        self.youtube = YouTubeSettings(**config_data.get('youtube', {}))
        self.database = DatabaseSettings(**config_data.get('database', {}))
    
    def model_post_init(self, __context) -> None:
        """Called after model initialization"""
        self.load_automation_config()


# Global settings instance
settings = Settings()

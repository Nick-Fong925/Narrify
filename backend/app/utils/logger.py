"""
Centralized logging utility for Narrify automation system.
Provides structured logging with file rotation and optional Slack notifications.
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional


class NarrifyLogger:
    """Centralized logger with file rotation and structured output"""
    
    def __init__(
        self,
        name: str = "narrify",
        log_file: str = "logs/narrify.log",
        log_level: str = "INFO",
        max_bytes: int = 10_485_760,  # 10MB
        backup_count: int = 5
    ):
        self.name = name
        self.log_file = Path(log_file)
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        
        # Ensure logs directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.log_level)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(self.log_level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        extra_info = " | ".join(f"{k}={v}" for k, v in kwargs.items())
        full_message = f"{message} | {extra_info}" if extra_info else message
        self.logger.info(full_message)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log error message with optional exception"""
        extra_info = " | ".join(f"{k}={v}" for k, v in kwargs.items())
        full_message = f"{message} | {extra_info}" if extra_info else message
        
        if exception:
            self.logger.error(f"{full_message} | Exception: {str(exception)}", exc_info=True)
        else:
            self.logger.error(full_message)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        extra_info = " | ".join(f"{k}={v}" for k, v in kwargs.items())
        full_message = f"{message} | {extra_info}" if extra_info else message
        self.logger.warning(full_message)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        extra_info = " | ".join(f"{k}={v}" for k, v in kwargs.items())
        full_message = f"{message} | {extra_info}" if extra_info else message
        self.logger.debug(full_message)
    
    def video_generation_start(self, post_id: int, reddit_id: str, title: str):
        """Log video generation start"""
        self.info(
            "Video generation started",
            post_id=post_id,
            reddit_id=reddit_id,
            title=title[:50]
        )
    
    def video_generation_success(self, post_id: int, reddit_id: str, duration_seconds: float):
        """Log successful video generation"""
        self.info(
            "Video generation completed",
            post_id=post_id,
            reddit_id=reddit_id,
            duration_seconds=round(duration_seconds, 2)
        )
    
    def video_generation_error(self, post_id: int, reddit_id: str, error: Exception):
        """Log video generation error"""
        self.error(
            "Video generation failed",
            exception=error,
            post_id=post_id,
            reddit_id=reddit_id
        )
    
    def youtube_upload_start(self, post_id: int, reddit_id: str):
        """Log YouTube upload start"""
        self.info(
            "YouTube upload started",
            post_id=post_id,
            reddit_id=reddit_id
        )
    
    def youtube_upload_success(self, post_id: int, reddit_id: str, youtube_video_id: str):
        """Log successful YouTube upload"""
        self.info(
            "YouTube upload completed",
            post_id=post_id,
            reddit_id=reddit_id,
            youtube_video_id=youtube_video_id,
            youtube_url=f"https://youtube.com/shorts/{youtube_video_id}"
        )
    
    def youtube_upload_error(self, post_id: int, reddit_id: str, error: Exception):
        """Log YouTube upload error"""
        self.error(
            "YouTube upload failed",
            exception=error,
            post_id=post_id,
            reddit_id=reddit_id
        )
    
    def automation_batch_start(self, batch_time: str, video_count: int):
        """Log automation batch start"""
        self.info(
            "Automation batch started",
            batch_time=batch_time,
            video_count=video_count
        )
    
    def automation_batch_complete(self, batch_time: str, successful: int, failed: int):
        """Log automation batch completion"""
        self.info(
            "Automation batch completed",
            batch_time=batch_time,
            successful=successful,
            failed=failed
        )


# Global logger instance
logger = NarrifyLogger()


def get_logger(
    name: str = "narrify",
    log_file: str = "logs/narrify.log",
    log_level: str = "INFO"
) -> NarrifyLogger:
    """Get or create a logger instance"""
    return NarrifyLogger(name=name, log_file=log_file, log_level=log_level)

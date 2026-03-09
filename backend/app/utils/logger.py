import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


class NarrifyLogger:
    def __init__(
        self,
        name: str = "narrify",
        log_file: str = "logs/narrify.log",
        log_level: str = "INFO",
        max_bytes: int = 10_485_760,
        backup_count: int = 5
    ):
        self.name = name
        self.log_file = Path(log_file)
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)

        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.log_level)
        self.logger.handlers.clear()

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        self.logger.addHandler(console_handler)

        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        self.logger.addHandler(file_handler)

    def _fmt(self, message: str, **kwargs) -> str:
        extra = " | ".join(f"{k}={v}" for k, v in kwargs.items())
        return f"{message} | {extra}" if extra else message

    def info(self, message: str, **kwargs):
        self.logger.info(self._fmt(message, **kwargs))

    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        msg = self._fmt(message, **kwargs)
        if exception:
            self.logger.error(f"{msg} | Exception: {str(exception)}", exc_info=True)
        else:
            self.logger.error(msg)

    def warning(self, message: str, **kwargs):
        self.logger.warning(self._fmt(message, **kwargs))

    def debug(self, message: str, **kwargs):
        self.logger.debug(self._fmt(message, **kwargs))

    def video_generation_start(self, post_id: int, reddit_id: str, title: str):
        self.info("Video generation started", post_id=post_id, reddit_id=reddit_id, title=title[:50])

    def video_generation_success(self, post_id: int, reddit_id: str, duration_seconds: float):
        self.info("Video generation completed", post_id=post_id, reddit_id=reddit_id, duration_seconds=round(duration_seconds, 2))

    def video_generation_error(self, post_id: int, reddit_id: str, error: Exception):
        self.error("Video generation failed", exception=error, post_id=post_id, reddit_id=reddit_id)

    def youtube_upload_start(self, post_id: int, reddit_id: str):
        self.info("YouTube upload started", post_id=post_id, reddit_id=reddit_id)

    def youtube_upload_success(self, post_id: int, reddit_id: str, youtube_video_id: str):
        self.info("YouTube upload completed", post_id=post_id, reddit_id=reddit_id,
                  youtube_video_id=youtube_video_id, youtube_url=f"https://youtube.com/shorts/{youtube_video_id}")

    def youtube_upload_error(self, post_id: int, reddit_id: str, error: Exception):
        self.error("YouTube upload failed", exception=error, post_id=post_id, reddit_id=reddit_id)

    def automation_batch_start(self, batch_time: str, video_count: int):
        self.info("Automation batch started", batch_time=batch_time, video_count=video_count)

    def automation_batch_complete(self, batch_time: str, successful: int, failed: int):
        self.info("Automation batch completed", batch_time=batch_time, successful=successful, failed=failed)


logger = NarrifyLogger()

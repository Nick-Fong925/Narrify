import time
from pathlib import Path
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.post import Post, GenerationStatus
from app.video.generator import generate_video_from_text
from app.utils.logger import logger


class VideoService:
    """Generates video files from posts."""

    def generate_video(
        self,
        post: Post,
        db: Session,
        base_video: str = "minecraft_parkour_base.mp4",
    ) -> Optional[str]:
        """Run the full TTS → subtitle → encode pipeline for a post.

        Updates the post's generation_status in the database.
        Returns the path to the generated MP4, or None on failure.
        """
        start_time = time.time()

        try:
            post.generation_status = GenerationStatus.PROCESSING.value
            db.commit()

            logger.video_generation_start(
                post_id=post.id,
                reddit_id=post.reddit_id,
                title=post.title,
            )

            video_path = generate_video_from_text(
                text=post.story,
                base_video_name=base_video,
                job_id=post.reddit_id,
                story_title=post.title,
                subreddit=post.subreddit,
            )

            if not video_path or not Path(video_path).exists():
                raise Exception("Video generation returned no file")

            duration = time.time() - start_time
            post.generation_status = GenerationStatus.COMPLETED.value
            post.generated_at = datetime.utcnow()
            post.generation_error = None
            db.commit()

            logger.video_generation_success(
                post_id=post.id,
                reddit_id=post.reddit_id,
                duration_seconds=duration,
            )

            return video_path

        except Exception as e:
            post.generation_status = GenerationStatus.FAILED.value
            post.generation_error = str(e)
            db.commit()

            logger.video_generation_error(
                post_id=post.id,
                reddit_id=post.reddit_id,
                error=e,
            )
            return None


video_service = VideoService()

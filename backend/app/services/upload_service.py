import os
import shutil
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import pytz

from app.db import SessionLocal
from app.models.post import Post
from app.services.youtube_service import youtube_service
from app.services.post_selector import post_selector
from app.services.video_service import video_service
from app.config import settings
from app.utils.logger import logger

# Videos generated but not yet uploaded are staged here.
# Each batch run flushes this queue before starting any new GPU work.
PENDING_UPLOADS_DIR = Path(__file__).resolve().parent.parent / "video" / "media" / "pending_uploads"


class UploadService:
    """Manages YouTube upload workflow, the pending-upload queue, and batch processing."""

    def upload_to_youtube(
        self,
        post: Post,
        video_path: str,
        db: Session,
    ) -> Optional[str]:
        """Upload a video file to YouTube and update the post record.

        Returns the YouTube video ID on success, None on failure.
        """
        try:
            logger.youtube_upload_start(post_id=post.id, reddit_id=post.reddit_id)

            description = (
                f"{post.story[:500]}...\n\n"
                f"From r/{post.subreddit}\n"
                f"Original: {post.url}\n\n"
                "#RedditStories #Shorts #Storytelling"
            )
            tags = ["reddit", "stories", "shorts", post.subreddit.lower(), "reddit stories"]

            tz = pytz.timezone(settings.automation.timezone)
            now = datetime.now(tz)
            next_day = now + timedelta(days=settings.youtube.publish_days_ahead)
            publish_at_local = tz.localize(datetime(
                next_day.year, next_day.month, next_day.day,
                settings.youtube.publish_hour, settings.youtube.publish_minute, 0
            ))
            publish_at_utc = publish_at_local.astimezone(pytz.utc)

            video_id = youtube_service.upload_video(
                video_path=video_path,
                title=post.title,
                description=description,
                tags=tags,
                category_id=settings.youtube.category_id,
                privacy_status=settings.youtube.privacy,
                publish_at=publish_at_utc,
            )

            if not video_id:
                raise Exception("YouTube upload returned no video ID")

            post.posted = True
            post.posted_at = datetime.utcnow()
            post.youtube_video_id = video_id
            post.upload_error = None
            db.commit()

            logger.youtube_upload_success(
                post_id=post.id,
                reddit_id=post.reddit_id,
                youtube_video_id=video_id,
            )
            return video_id

        except Exception as e:
            post.upload_error = str(e)
            db.commit()

            logger.youtube_upload_error(
                post_id=post.id,
                reddit_id=post.reddit_id,
                error=e,
            )
            return None

    def _upload_pending_videos(self, db: Session) -> Tuple[int, int]:
        """Attempt to upload every video in the pending_uploads folder.

        Returns (successful, failed) counts.
        Successfully uploaded files are deleted; failed files remain for retry.
        """
        PENDING_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        pending_files = sorted(PENDING_UPLOADS_DIR.glob("*.mp4"))

        if not pending_files:
            return 0, 0

        logger.info(f"Pending uploads queue: {len(pending_files)} video(s) waiting")
        successful = 0
        failed = 0

        for video_file in pending_files:
            reddit_id = video_file.stem
            post = db.query(Post).filter(Post.reddit_id == reddit_id).first()

            if post is None:
                logger.warning(f"No DB record for pending video '{video_file.name}' — skipping")
                continue

            if post.posted:
                logger.info(f"Post {reddit_id} already posted; removing orphaned file")
                video_file.unlink(missing_ok=True)
                continue

            video_id = self.upload_to_youtube(post, str(video_file), db)

            if video_id:
                successful += 1
                video_file.unlink(missing_ok=True)
            else:
                failed += 1
                logger.warning(f"Upload failed for '{video_file.name}' — will retry next batch")

        return successful, failed

    def process_batch(self, count: int = 5) -> Tuple[int, int]:
        """Generate and upload up to `count` new videos.

        Phase 1: Flush any videos sitting in the pending queue.
        Phase 2: Generate new videos and attempt immediate upload.

        Returns (total_successful, total_failed).
        """
        db = SessionLocal()
        total_successful = 0
        total_failed = 0

        try:
            # ── Phase 1: Flush pending uploads ────────────────────────────────
            pending_success, pending_failed = self._upload_pending_videos(db)
            total_successful += pending_success
            total_failed += pending_failed

            # If videos are still stuck, YouTube is likely rate-limiting us.
            # Skip GPU generation to avoid wasting resources.
            remaining = list(PENDING_UPLOADS_DIR.glob("*.mp4"))
            if remaining:
                logger.warning(
                    f"{len(remaining)} video(s) still pending after flush "
                    f"— skipping generation. Will retry uploads next batch."
                )
                return total_successful, total_failed

            # ── Phase 2: Generate new videos ──────────────────────────────────
            posts = post_selector.select_posts_for_generation(db, count)

            if not posts:
                logger.warning("No posts available for video generation")
                return total_successful, total_failed

            for post in posts:
                generated_path = None
                pending_path = PENDING_UPLOADS_DIR / f"{post.reddit_id}.mp4"

                try:
                    generated_path = video_service.generate_video(post, db)

                    if not generated_path:
                        total_failed += 1
                        continue

                    PENDING_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
                    shutil.move(generated_path, str(pending_path))
                    logger.info(f"Saved to pending uploads: {pending_path.name}")

                    video_id = self.upload_to_youtube(post, str(pending_path), db)

                    if video_id:
                        total_successful += 1
                        pending_path.unlink(missing_ok=True)
                    else:
                        total_failed += 1
                        logger.warning(
                            f"Upload failed — '{pending_path.name}' queued for next batch"
                        )

                except Exception as e:
                    logger.error(
                        f"Error processing post {post.id}",
                        exception=e,
                        post_id=post.id,
                        reddit_id=post.reddit_id,
                    )
                    total_failed += 1
                    if generated_path and os.path.exists(generated_path):
                        try:
                            os.remove(generated_path)
                        except Exception:
                            pass

            return total_successful, total_failed

        finally:
            db.close()


upload_service = UploadService()

from typing import List
from sqlalchemy.orm import Session

from app.models.post import Post, GenerationStatus
from app.config import settings
from app.utils.logger import logger


class PostSelector:
    """Selects posts from the database for video generation."""

    def select_posts_for_generation(
        self,
        db: Session,
        count: int = 5,
        min_duration_seconds: int = 30,
    ) -> List[Post]:
        """Return up to `count` posts that are ready for video generation.

        Filters by score threshold, excludes already-posted and already-processing
        posts, and drops stories too short to fill the minimum video duration.
        """
        candidate_posts = db.query(Post).filter(
            Post.posted == False,
            Post.generation_status.in_([
                GenerationStatus.PENDING.value,
                GenerationStatus.FAILED.value,
            ]),
            Post.score >= settings.database.min_score_threshold,
        ).order_by(Post.score.desc()).all()

        # Estimate duration at ~2.5 words/second with 1.3x speed multiplier.
        posts_with_duration = []
        skipped_short = 0

        for post in candidate_posts:
            story_words = len(post.story.split())
            title_words = len(post.title.split()) if post.title else 0
            total_words = story_words + title_words
            estimated_duration = (total_words / 2.5) / 1.3

            if estimated_duration >= min_duration_seconds:
                posts_with_duration.append((post, estimated_duration))
            else:
                skipped_short += 1

        posts_with_duration.sort(
            key=lambda x: x[0].score + (x[0].num_comments * 3),
            reverse=True,
        )
        selected = [post for post, _ in posts_with_duration[:count]]

        if skipped_short:
            logger.info(f"Skipped {skipped_short} posts too short (<{min_duration_seconds}s estimated)")

        logger.info(f"Selected {len(selected)} posts for video generation")
        return selected


post_selector = PostSelector()

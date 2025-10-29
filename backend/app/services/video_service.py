"""
Video service for orchestrating video generation and YouTube upload.
Handles post selection, video generation, upload, and cleanup.
"""
import os
import time
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.db import get_db, SessionLocal
from app.models.post import Post, GenerationStatus
from app.video.generator import generate_video_from_text
from app.services.youtube_service import youtube_service
from app.config import settings
from app.utils.logger import logger


class VideoService:
    """Service for managing video generation and upload workflow"""
    
    def __init__(self):
        self.youtube = youtube_service
    
    def select_posts_for_generation(
        self,
        db: Session,
        count: int = 5,
        max_duration_seconds: int = 90  # Maximum video duration to prevent RAM issues
    ) -> List[Post]:
        """
        Select top posts for video generation.
        
        Prioritizes shorter videos (≤90s) to prevent RAM exhaustion, but keeps
        longer posts in database for when you have a better computer.
        
        Selection strategy:
        1. Get all unposted posts with score >= threshold
        2. Calculate estimated duration for each
        3. Prioritize posts ≤ max_duration_seconds
        4. Sort by: duration_within_limit (yes/no), then score (desc)
        5. Select top N that are within duration limit
        
        Args:
            db: Database session
            count: Number of posts to select
            max_duration_seconds: Maximum estimated video duration (default: 90s = 1.5 min)
        
        Returns:
            List of Post objects (only posts within duration limit)
        """
        # Get all candidate posts
        candidate_posts = db.query(Post).filter(
            Post.posted == False,
            Post.generation_status.in_([
                GenerationStatus.PENDING.value,
                GenerationStatus.FAILED.value
            ]),
            Post.score >= settings.database.min_score_threshold
        ).order_by(
            Post.score.desc()
        ).all()
        
        # Calculate estimated duration for each post and filter to only short ones
        # Speaking rate: ~2.5 words/second (150 words/min)
        # Also account for title narration and 1.3x speed multiplier
        posts_with_duration = []
        long_posts_count = 0
        
        for post in candidate_posts:
            # Calculate word count (story + title if narrated)
            story_words = len(post.story.split())
            title_words = len(post.title.split()) if post.title else 0
            total_words = story_words + title_words  # Title is narrated by default
            
            # Estimate base duration (before speed multiplier)
            base_duration = total_words / 2.5  # 2.5 words per second
            
            # Account for 1.3x speed multiplier (video is sped up)
            estimated_duration = base_duration / 1.3
            
            # Only include posts within duration limit (save long ones for better computer)
            if estimated_duration <= max_duration_seconds:
                posts_with_duration.append((post, estimated_duration))
            else:
                long_posts_count += 1
        
        # Sort by score (already sorted from query, but make it explicit)
        # Higher score = better post = process first
        posts_with_duration.sort(key=lambda x: x[0].score, reverse=True)
        
        # Select top N posts
        selected_posts = [post for post, duration in posts_with_duration[:count]]
        
        # Log selection summary
        if long_posts_count > 0:
            logger.info(
                f"📊 Selection: {len(selected_posts)} posts selected, "
                f"{long_posts_count} long posts saved for later (>{max_duration_seconds}s)"
            )
        
        logger.info(f"Selected {len(selected_posts)} posts for video generation")
        return selected_posts
    
    def generate_video(
        self,
        post: Post,
        db: Session,
        base_video: str = "minecraft_parkour_base.mp4"
    ) -> Optional[str]:
        """
        Generate video for a post.
        
        Args:
            post: Post object
            db: Database session
            base_video: Base video filename
        
        Returns:
            Path to generated video file, or None if failed
        """
        start_time = time.time()
        
        try:
            # Update status to PROCESSING
            post.generation_status = GenerationStatus.PROCESSING.value
            db.commit()
            
            logger.video_generation_start(
                post_id=post.id,
                reddit_id=post.reddit_id,
                title=post.title
            )
            
            # Generate video
            video_path = generate_video_from_text(
                text=post.story,
                base_video_name=base_video,
                job_id=post.reddit_id,
                voice_type="cloned",
                story_title=post.title,
                subreddit=post.subreddit
            )
            
            if not video_path or not Path(video_path).exists():
                raise Exception("Video generation returned no file")
            
            # Update status to COMPLETED
            duration = time.time() - start_time
            post.generation_status = GenerationStatus.COMPLETED.value
            post.generated_at = datetime.utcnow()
            post.generation_error = None
            db.commit()
            
            logger.video_generation_success(
                post_id=post.id,
                reddit_id=post.reddit_id,
                duration_seconds=duration
            )
            
            return video_path
            
        except Exception as e:
            # Update status to FAILED
            post.generation_status = GenerationStatus.FAILED.value
            post.generation_error = str(e)
            db.commit()
            
            logger.video_generation_error(
                post_id=post.id,
                reddit_id=post.reddit_id,
                error=e
            )
            return None
    
    def upload_to_youtube(
        self,
        post: Post,
        video_path: str,
        db: Session
    ) -> Optional[str]:
        """
        Upload video to YouTube.
        Video already has metadata embedded from generation.
        
        Args:
            post: Post object
            video_path: Path to video file
            db: Database session
        
        Returns:
            YouTube video ID if successful, None otherwise
        """
        try:
            logger.youtube_upload_start(
                post_id=post.id,
                reddit_id=post.reddit_id
            )
            
            # Create YouTube metadata (metadata is already embedded in video)
            description = f"{post.story[:500]}...\n\nFrom r/{post.subreddit}\nOriginal: {post.url}\n\n#RedditStories #Shorts #Storytelling"
            tags = ['reddit', 'stories', 'shorts', post.subreddit.lower(), 'reddit stories']
            
            # Upload to YouTube
            video_id = self.youtube.upload_video(
                video_path=video_path,
                title=post.title,
                description=description,
                tags=tags,
                category_id=settings.youtube.category_id,
                privacy_status=settings.youtube.privacy
            )
            
            if not video_id:
                raise Exception("YouTube upload returned no video ID")
            
            # Update post with YouTube info
            post.posted = True
            post.posted_at = datetime.utcnow()
            post.youtube_video_id = video_id
            post.upload_error = None
            db.commit()
            
            logger.youtube_upload_success(
                post_id=post.id,
                reddit_id=post.reddit_id,
                youtube_video_id=video_id
            )
            
            return video_id
            
        except Exception as e:
            # Update error
            post.upload_error = str(e)
            db.commit()
            
            logger.youtube_upload_error(
                post_id=post.id,
                reddit_id=post.reddit_id,
                error=e
            )
            return None
    
    def process_batch(
        self,
        count: int = 5,
        delete_after_upload: bool = True
    ) -> Tuple[int, int]:
        """
        Process a batch of videos: generate and upload.
        
        Args:
            count: Number of videos to process
            delete_after_upload: Delete video files after successful upload
        
        Returns:
            Tuple of (successful_count, failed_count)
        """
        db = SessionLocal()
        successful = 0
        failed = 0
        
        try:
            # Select posts
            posts = self.select_posts_for_generation(db, count)
            
            if not posts:
                logger.warning("No posts available for video generation")
                return 0, 0
            
            # Process each post
            for post in posts:
                video_path = None
                
                try:
                    # Generate video
                    video_path = self.generate_video(post, db)
                    
                    if not video_path:
                        failed += 1
                        continue
                    
                    # Upload to YouTube
                    video_id = self.upload_to_youtube(post, video_path, db)
                    
                    if video_id:
                        successful += 1
                        
                        # Delete video file to conserve space
                        if delete_after_upload:
                            try:
                                os.remove(video_path)
                                logger.info(f"Deleted video file: {video_path}")
                            except Exception as e:
                                logger.warning(
                                    f"Failed to delete video file: {video_path}",
                                    exception=e
                                )
                    else:
                        failed += 1
                
                except Exception as e:
                    logger.error(
                        f"Error processing post {post.id}",
                        exception=e,
                        post_id=post.id,
                        reddit_id=post.reddit_id
                    )
                    failed += 1
                    
                    # Cleanup video file if exists
                    if video_path and os.path.exists(video_path):
                        try:
                            os.remove(video_path)
                        except:
                            pass
            
            return successful, failed
            
        finally:
            db.close()


# Global video service instance
video_service = VideoService()

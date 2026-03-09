#!/usr/bin/env python3
"""
Generate and upload a single video to YouTube.
Picks the highest-scoring unposted post from the DB, generates a video,
and uploads it. Use this to test the full pipeline with one video.

Usage:
    python scripts/generate_and_upload_one.py
    python scripts/generate_and_upload_one.py --post-id 42
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app.models.post import Post, GenerationStatus
from app.services.video_service import video_service
from app.services.upload_service import upload_service
from app.utils.logger import logger


def main():
    parser = argparse.ArgumentParser(
        description="Generate and upload ONE video to YouTube"
    )
    parser.add_argument(
        "--post-id",
        type=int,
        help="Specific post ID to use (default: highest-scoring unposted)",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        # Select post
        if args.post_id:
            post = db.query(Post).filter_by(id=args.post_id).first()
            if not post:
                print(f"Post {args.post_id} not found.")
                sys.exit(1)
        else:
            post = (
                db.query(Post)
                .filter(
                    Post.posted == False,
                    Post.generation_status.in_([
                        GenerationStatus.PENDING.value,
                        GenerationStatus.FAILED.value,
                    ]),
                )
                .order_by(Post.score.desc())
                .first()
            )
            if not post:
                print("No unposted posts available.")
                sys.exit(1)

        print(f"\nSelected post: [{post.id}] {post.title}")
        print(f"  r/{post.subreddit}  |  score={post.score}  |  {len(post.story.split())} words\n")

        # Generate
        print("Generating video...")
        video_path = video_service.generate_video(post=post, db=db)

        if not video_path or not Path(video_path).exists():
            print("Video generation failed — check logs.")
            sys.exit(1)

        print(f"Video ready: {video_path}  ({Path(video_path).stat().st_size / 1024 / 1024:.1f} MB)\n")

        # Upload
        print("Uploading to YouTube...")
        video_id = upload_service.upload_to_youtube(post=post, video_path=video_path, db=db)

        if video_id:
            print(f"\nUploaded successfully!")
            print(f"  YouTube Shorts URL: https://youtube.com/shorts/{video_id}")
            Path(video_path).unlink(missing_ok=True)
        else:
            print("\nUpload failed — video kept at path above. Check logs.")
            sys.exit(1)

    except Exception as e:
        print(f"\nError: {e}")
        logger.error("generate_and_upload_one failed", exception=e)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()

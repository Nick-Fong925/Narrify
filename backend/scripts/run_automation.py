#!/usr/bin/env python3
"""
Manual automation trigger script.
Run this to test the automation system without waiting for scheduled times.
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from automation.scheduler import automation_scheduler
from app.utils.logger import logger


def main():
    parser = argparse.ArgumentParser(
        description='Manually trigger video generation and YouTube upload'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=None,
        help='Number of videos to generate (default: from config)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually doing it'
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        from app.config import settings
        from app.db import SessionLocal
        from app.services.video_service import video_service
        
        db = SessionLocal()
        try:
            video_count = args.count or settings.automation.videos_per_batch
            posts = video_service.select_posts_for_generation(db, video_count)
            
            print(f"\n=== DRY RUN ===")
            print(f"Would generate {len(posts)} videos:")
            for i, post in enumerate(posts, 1):
                print(f"\n{i}. Post ID: {post.id}")
                print(f"   Reddit ID: {post.reddit_id}")
                print(f"   Subreddit: r/{post.subreddit}")
                print(f"   Title: {post.title}")
                print(f"   Score: {post.score}")
                print(f"   Status: {post.generation_status}")
        finally:
            db.close()
    else:
        logger.info("Starting manual automation run")
        successful, failed = automation_scheduler.run_now(args.count)
        
        print(f"\n=== AUTOMATION COMPLETE ===")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Total: {successful + failed}")


if __name__ == '__main__':
    main()

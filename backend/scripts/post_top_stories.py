#!/usr/bin/env python3
"""
Post Top Stories Script
========================
Generates videos and posts the top 10 stories from the database to YouTube as unlisted.
Updates the database status for each post.

Usage:
    python scripts/post_top_stories.py [--count N] [--privacy unlisted|public|private]
"""
import sys
import argparse
from pathlib import Path
import time
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app.models.post import Post, GenerationStatus
from app.services.video_service import video_service
from app.utils.logger import logger


def cleanup_generated_videos_folder():
    """Remove all files from generated_videos folder to free up disk space"""
    generated_videos_dir = Path(__file__).parent.parent / "app" / "video" / "media" / "generated_videos"
    
    if not generated_videos_dir.exists():
        return
    
    print("🗑️  Cleaning up generated_videos folder...")
    
    file_count = 0
    freed_space = 0
    
    for file_path in generated_videos_dir.iterdir():
        if file_path.is_file():
            try:
                file_size = file_path.stat().st_size
                file_path.unlink()
                file_count += 1
                freed_space += file_size
            except Exception as e:
                print(f"   Warning: Could not delete {file_path.name}: {e}")
    
    if file_count > 0:
        freed_mb = freed_space / (1024 * 1024)
        print(f"   ✅ Deleted {file_count} files, freed {freed_mb:.1f} MB")
    else:
        print(f"   ✅ Folder already clean")
    print()


def get_top_unposted_stories(db, count: int = 10):
    """Get top N unposted stories ordered by score"""
    posts = db.query(Post).filter(
        Post.posted == False,
        Post.generation_status.in_([
            GenerationStatus.PENDING.value,
            GenerationStatus.FAILED.value
        ])
    ).order_by(
        Post.score.desc()
    ).limit(count).all()
    
    return posts


def main():
    parser = argparse.ArgumentParser(
        description='Post top stories from database to YouTube'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=10,
        help='Number of stories to post (default: 10)'
    )
    parser.add_argument(
        '--privacy',
        choices=['unlisted', 'public', 'private'],
        default='unlisted',
        help='YouTube privacy status (default: unlisted)'
    )
    parser.add_argument(
        '--keep-videos',
        action='store_true',
        help='Keep video files after upload (default: delete)'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("📹 POST TOP STORIES TO YOUTUBE")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Stories to post: {args.count}")
    print(f"  Privacy status: {args.privacy}")
    print(f"  Delete videos after upload: {not args.keep_videos}")
    print()
    
    # Clean up old files before starting
    cleanup_generated_videos_folder()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Get top stories
        print(f"🔍 Fetching top {args.count} unposted stories...")
        posts = get_top_unposted_stories(db, args.count)
        
        if not posts:
            print("\n⚠️  No unposted stories found in database!")
            print("\nTips:")
            print("  - Run the Reddit scraper to collect stories")
            print("  - Check that stories meet minimum score threshold")
            return
        
        print(f"✅ Found {len(posts)} stories to process\n")
        
        # Display stories
        print("-" * 80)
        print("Stories to be posted:")
        print("-" * 80)
        for i, post in enumerate(posts, 1):
            print(f"{i}. [{post.score:4d} ⬆️] r/{post.subreddit} - {post.title[:60]}...")
        print("-" * 80)
        print()
        
        # Confirm
        response = input("Continue with video generation and upload? [y/N]: ")
        if response.lower() != 'y':
            print("❌ Cancelled by user")
            return
        
        print()
        
        # Temporarily override privacy setting
        from app.config import settings
        original_privacy = settings.youtube.privacy
        settings.youtube.privacy = args.privacy
        
        # Process each post
        successful = 0
        failed = 0
        
        for i, post in enumerate(posts, 1):
            print(f"\n{'='*80}")
            print(f"Processing {i}/{len(posts)}: {post.title[:60]}...")
            print(f"{'='*80}")
            
            video_path = None
            
            try:
                # Step 1: Generate video
                print(f"\n🎬 Generating video...")
                print(f"   Story: {post.story[:100]}...")
                print(f"   Score: {post.score} | Subreddit: r/{post.subreddit}")
                
                video_path = video_service.generate_video(post, db)
                
                if not video_path:
                    print(f"❌ Video generation failed: {post.generation_error}")
                    failed += 1
                    continue
                
                print(f"✅ Video generated: {video_path}")
                
                # Step 2: Upload to YouTube
                print(f"\n📤 Uploading to YouTube ({args.privacy})...")
                
                video_id = video_service.upload_to_youtube(post, video_path, db)
                
                if video_id:
                    print(f"✅ Upload successful!")
                    print(f"   Video ID: {video_id}")
                    print(f"   URL: https://youtube.com/shorts/{video_id}")
                    print(f"   Status: {args.privacy}")
                    successful += 1
                    
                    # Delete video file if requested
                    if not args.keep_videos:
                        try:
                            import os
                            os.remove(video_path)
                            print(f"🗑️  Deleted local video file")
                        except Exception as e:
                            print(f"⚠️  Could not delete video: {e}")
                else:
                    print(f"❌ Upload failed: {post.upload_error}")
                    failed += 1
                
            except Exception as e:
                print(f"❌ Error processing post: {e}")
                logger.error(f"Error in batch script", exception=e, post_id=post.id)
                failed += 1
                
                # Cleanup on error
                if video_path:
                    try:
                        import os
                        if os.path.exists(video_path):
                            os.remove(video_path)
                    except:
                        pass
            
            # Add delay between uploads to avoid rate limits
            if i < len(posts):
                print(f"\n⏸️  Waiting 5 seconds before next video...")
                time.sleep(5)
        
        # Restore original privacy setting
        settings.youtube.privacy = original_privacy
        
        # Summary
        print(f"\n{'='*80}")
        print("📊 BATCH COMPLETE")
        print(f"{'='*80}")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Total: {len(posts)}")
        print(f"{'='*80}\n")
        
        if successful > 0:
            print(f"🎉 {successful} videos posted to YouTube as {args.privacy}!")
            print(f"\nView your videos at: https://studio.youtube.com")
        
    finally:
        db.close()


if __name__ == '__main__':
    main()

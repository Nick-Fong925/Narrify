#!/usr/bin/env python3
"""
Batch Upload Script (Subprocess Strategy)
==========================================
Generates and uploads multiple videos by running each one as a SEPARATE subprocess.
This ensures complete memory cleanup between videos, preventing OOM kills.

Each subprocess:
1. Loads models fresh
2. Generates 1 video
3. Uploads to YouTube
4. Terminates completely (frees ALL memory)

Usage:
    python scripts/batch_upload_subprocess.py --count 10 --privacy unlisted
"""
import sys
import argparse
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app.models.post import Post, GenerationStatus


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


def run_single_video_subprocess(post_id: int, privacy: str, keep_video: bool):
    """
    Run test_video_upload.py as a subprocess for a single post.
    This ensures complete process termination and memory cleanup.
    
    Returns: (success: bool, error_msg: str)
    """
    try:
        # Get Python from virtual environment
        backend_dir = Path(__file__).parent.parent
        venv_python = backend_dir / "venv" / "bin" / "python"
        
        # Use venv python if it exists, otherwise use system python
        python_cmd = str(venv_python) if venv_python.exists() else sys.executable
        
        # Build command
        cmd = [
            python_cmd,  # Use venv Python interpreter
            "scripts/test_video_upload.py",
            "--post-id", str(post_id),
            "--privacy", privacy
        ]
        
        if keep_video:
            cmd.append("--keep-video")
        
        print(f"🚀 Running subprocess: {' '.join(cmd)}")
        
        # Run as subprocess with output streaming
        result = subprocess.run(
            cmd,
            cwd=backend_dir,  # Run from backend directory
            capture_output=False,  # Stream output to terminal
            text=True
        )
        
        if result.returncode == 0:
            # Clean up generated video after successful upload (unless --keep-videos)
            if not keep_video:
                cleanup_post_video_files(post_id, backend_dir)
            return True, None
        else:
            # Even on failure, clean up any partial files
            cleanup_post_video_files(post_id, backend_dir)
            return False, f"Subprocess exited with code {result.returncode}"
            
    except Exception as e:
        # Clean up on exception too
        try:
            cleanup_post_video_files(post_id, backend_dir)
        except:
            pass
        return False, str(e)


def cleanup_post_video_files(post_id: int, backend_dir: Path):
    """
    Clean up video files for a specific post ID after upload.
    This removes the final .mp4 file to free disk space.
    """
    generated_videos_dir = backend_dir / "app" / "video" / "media" / "generated_videos"
    
    # The video file is named with the post's reddit_id (e.g., "1g25xbv.mp4")
    # We need to find it by querying the database
    from app.db import SessionLocal
    from app.models.post import Post
    
    db = SessionLocal()
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if post and post.reddit_id:
            video_file = generated_videos_dir / f"{post.reddit_id}.mp4"
            if video_file.exists():
                try:
                    file_size = video_file.stat().st_size
                    video_file.unlink()
                    print(f"🗑️  Cleaned up final video: {video_file.name} ({file_size / (1024*1024):.1f} MB)")
                except Exception as e:
                    print(f"   Warning: Could not delete {video_file.name}: {e}")
    finally:
        db.close()



def main():
    parser = argparse.ArgumentParser(
        description='Batch upload videos using subprocess strategy (prevents OOM)'
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
    print("📹 BATCH UPLOAD - SUBPROCESS STRATEGY")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Stories to post: {args.count}")
    print(f"  Privacy status: {args.privacy}")
    print(f"  Delete videos after upload: {not args.keep_videos}")
    print(f"  Strategy: Each video runs in separate subprocess")
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
        response = input("Continue with batch processing? [y/N]: ")
        if response.lower() != 'y':
            print("❌ Cancelled by user")
            return
        
        print()
        
        # Process each post as SEPARATE subprocess
        successful = 0
        failed = 0
        
        for i, post in enumerate(posts, 1):
            print(f"\n{'='*80}")
            print(f"Processing {i}/{len(posts)}: {post.title[:60]}...")
            print(f"Post ID: {post.id} | Score: {post.score} | r/{post.subreddit}")
            print(f"{'='*80}\n")
            
            # Run as subprocess - this will completely terminate and free memory
            success, error = run_single_video_subprocess(
                post.id,
                args.privacy,
                args.keep_videos
            )
            
            if success:
                print(f"\n✅ Successfully processed post {post.id}")
                successful += 1
            else:
                print(f"\n❌ Failed to process post {post.id}: {error}")
                failed += 1
            
            print(f"\n📊 Progress: {i}/{len(posts)} complete ({successful} ✅, {failed} ❌)")
        
        # Final summary
        print("\n" + "=" * 80)
        print("📊 BATCH PROCESSING COMPLETE")
        print("=" * 80)
        print(f"  Total processed: {len(posts)}")
        print(f"  ✅ Successful: {successful}")
        print(f"  ❌ Failed: {failed}")
        print(f"  Success rate: {(successful/len(posts)*100):.1f}%")
        print("=" * 80)
        
    finally:
        db.close()


if __name__ == "__main__":
    main()

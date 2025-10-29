#!/usr/bin/env python3
"""
Test script to generate ONE video WITHOUT uploading to YouTube.
Use this to test video generation, voice cloning, and subtitles.
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app.models.post import Post, GenerationStatus
from app.services.video_service import video_service
from app.utils.logger import logger


def main():
    parser = argparse.ArgumentParser(
        description='Test video generation for ONE video (no YouTube upload)'
    )
    parser.add_argument(
        '--post-id',
        type=int,
        help='Specific post ID to generate video for'
    )
    parser.add_argument(
        '--keep-video',
        action='store_true',
        default=True,
        help='Keep the video file (default: True)'
    )
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        # Get post
        if args.post_id:
            post = db.query(Post).filter_by(id=args.post_id).first()
            if not post:
                print(f"❌ Error: Post with ID {args.post_id} not found")
                sys.exit(1)
        else:
            # Get highest scoring unpublished post
            post = db.query(Post).filter(
                Post.posted == False,
                Post.generation_status.in_([
                    GenerationStatus.PENDING.value,
                    GenerationStatus.FAILED.value
                ])
            ).order_by(Post.score.desc()).first()
            
            if not post:
                print("❌ Error: No unpublished posts available")
                sys.exit(1)
        
        print("\n" + "="*70)
        print("🧪 TEST VIDEO GENERATION (No Upload)")
        print("="*70)
        print(f"\nPost Details:")
        print(f"  ID: {post.id}")
        print(f"  Reddit ID: {post.reddit_id}")
        print(f"  Subreddit: r/{post.subreddit}")
        print(f"  Title: {post.title}")
        print(f"  Score: {post.score}")
        print(f"  Words: {len(post.story.split())}")
        print(f"  URL: {post.url}")
        print("\n" + "-"*70)
        
        # Generate video
        print("\n📹 Generating video...")
        print("   (This may take 2-5 minutes depending on story length)")
        
        video_path = video_service.generate_video(
            post=post,
            db=db
        )
        
        if not video_path or not Path(video_path).exists():
            print("❌ Video generation failed. Check logs for details.")
            sys.exit(1)
        
        print(f"\n✅ Video generated successfully!")
        print(f"   Path: {video_path}")
        print(f"   Size: {Path(video_path).stat().st_size / (1024*1024):.2f} MB")
        
        print("\n" + "="*70)
        print("✅ TEST COMPLETED SUCCESSFULLY!")
        print("="*70)
        print(f"\n📊 Summary:")
        print(f"   Post ID: {post.id}")
        print(f"   Video saved at: {video_path}")
        print(f"   Generation status: {post.generation_status}")
        print(f"\n💡 Next Steps:")
        print(f"   • Watch the video: open \"{video_path}\"")
        print(f"   • Test upload: python scripts/test_video_upload.py --post-id {post.id}")
        print(f"   • Run full automation: python scripts/run_automation.py")
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error("Test video generation failed", exception=e)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        db.close()


if __name__ == '__main__':
    main()

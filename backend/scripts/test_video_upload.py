#!/usr/bin/env python3
"""
Test script to generate and upload ONE video to YouTube.
Posts the video as 'unlisted' (pending) instead of public for testing.
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
import os


def main():
    parser = argparse.ArgumentParser(
        description='Test video generation and upload for ONE video (unlisted/pending)'
    )
    parser.add_argument(
        '--post-id',
        type=int,
        help='Specific post ID to generate video for'
    )
    parser.add_argument(
        '--privacy',
        choices=['unlisted', 'private', 'public'],
        default='unlisted',
        help='Privacy status for the test upload (default: unlisted)'
    )
    parser.add_argument(
        '--keep-video',
        action='store_true',
        help='Keep the video file after upload (don\'t delete)'
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
        print("🧪 TEST VIDEO GENERATION & UPLOAD")
        print("="*70)
        print(f"\nPost Details:")
        print(f"  ID: {post.id}")
        print(f"  Reddit ID: {post.reddit_id}")
        print(f"  Subreddit: r/{post.subreddit}")
        print(f"  Title: {post.title}")
        print(f"  Score: {post.score}")
        print(f"  Words: {len(post.story.split())}")
        print(f"  URL: {post.url}")
        print(f"\nUpload Settings:")
        print(f"  Privacy: {args.privacy.upper()}")
        print(f"  Keep video file: {args.keep_video}")
        print("\n" + "-"*70)
        
        # Step 1: Generate video
        print("\n📹 Step 1/2: Generating video...")
        print("   (This may take 2-5 minutes depending on story length)")
        
        video_path = video_service.generate_video(
            post=post,
            db=db
        )
        
        if not video_path or not Path(video_path).exists():
            print("❌ Video generation failed. Check logs for details.")
            sys.exit(1)
        
        print(f"✅ Video generated successfully!")
        print(f"   Path: {video_path}")
        print(f"   Size: {Path(video_path).stat().st_size / (1024*1024):.2f} MB")
        
        # Step 2: Upload to YouTube
        print(f"\n📤 Step 2/2: Uploading to YouTube ({args.privacy})...")
        
        # Temporarily override privacy setting for this test
        from app.config import settings
        original_privacy = settings.youtube.privacy
        settings.youtube.privacy = args.privacy
        
        try:
            video_id = video_service.upload_to_youtube(
                post=post,
                video_path=video_path,
                db=db
            )
            
            if not video_id:
                print("❌ YouTube upload failed. Check logs for details.")
                sys.exit(1)
            
            print(f"✅ Upload successful!")
            print(f"   Video ID: {video_id}")
            print(f"   URL: https://youtube.com/watch?v={video_id}")
            if args.privacy == 'unlisted':
                print(f"   📋 Status: UNLISTED (pending - only visible with link)")
            elif args.privacy == 'private':
                print(f"   🔒 Status: PRIVATE (only visible to you)")
            
        finally:
            # Restore original privacy setting
            settings.youtube.privacy = original_privacy
        
        # Step 3: Cleanup
        if not args.keep_video and os.path.exists(video_path):
            print(f"\n🗑️  Cleaning up...")
            try:
                os.remove(video_path)
                print(f"   Deleted video file: {video_path}")
            except Exception as e:
                print(f"   ⚠️  Failed to delete video file: {e}")
        elif args.keep_video:
            print(f"\n💾 Video file saved at: {video_path}")
        
        print("\n" + "="*70)
        print("✅ TEST COMPLETED SUCCESSFULLY!")
        print("="*70)
        print(f"\n📊 Summary:")
        print(f"   Post marked as: {'POSTED' if post.posted else 'NOT POSTED'}")
        print(f"   YouTube Video ID: {video_id}")
        print(f"   Privacy: {args.privacy.upper()}")
        print(f"\n💡 Next Steps:")
        if args.privacy == 'unlisted':
            print(f"   • View your video: https://youtube.com/watch?v={video_id}")
            print(f"   • Change to public in YouTube Studio if satisfied")
        elif args.privacy == 'private':
            print(f"   • View in YouTube Studio: https://studio.youtube.com/")
            print(f"   • Change to public when ready")
        print(f"   • Run automation: python scripts/run_automation.py")
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error("Test video upload failed", exception=e)
        sys.exit(1)
    
    finally:
        db.close()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Test script to generate video from highest scoring reddit story
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db import SessionLocal
from app.models.post import Post
from app.utils.text_cleaning import clean_story, word_count
from app.video.generator import generate_video_from_text

def main():
    print("🎬 Testing video generation from highest scoring reddit story...")
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Find highest scoring post
        post = db.query(Post).filter(Post.score >= 500).order_by(Post.score.desc()).first()
        
        if not post:
            print("❌ No high-scoring posts found in database")
            return
        
        print(f"📊 Found highest scoring post:")
        print(f"   Score: {post.score}")
        print(f"   Subreddit: r/{post.subreddit}")
        print(f"   Title: {post.title[:100]}...")
        
        # Clean and validate story
        text = clean_story(post.story)
        
        # For testing with ASS subtitles, let's use first 10 sentences (manageable length)
        sentences = text.split('.')
        test_text = '. '.join(sentences[:10]) + '.'
        words = word_count(test_text)
        
        print(f"   Original word count: {word_count(text)}")
        print(f"   Test word count: {words}")
        
        if words < 80:
            test_text = '. '.join(sentences[:15]) + '.'  # Use more sentences if needed
            words = word_count(test_text)
        
        if words < 50:
            print("❌ Test story too short for video generation")
            return
        
        print("🎥 Generating video...")
        print("   - Creating TTS audio...")
        print("   - Selecting random minecraft parkour segment...")
        print("   - Adding white text overlays...")
        print("   - Adding YouTube Shorts optimized metadata...")
        
        # Generate video with metadata
        video_path = generate_video_from_text(
            text=test_text,
            base_video_name="minecraft_parkour_base.mp4",
            story_title=post.title,
            subreddit=post.subreddit
        )
        
        print(f"✅ Video generated successfully!")
        print(f"   Path: {video_path}")
        print(f"   You can play it with: open '{video_path}'")
        
    except Exception as e:
        print(f"❌ Error generating video: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    main()
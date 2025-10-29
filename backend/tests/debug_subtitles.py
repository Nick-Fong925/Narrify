#!/usr/bin/env python3
"""Debug subtitle generation and rendering."""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path
backend_dir = Path(__file__).parent
app_dir = backend_dir / "app"
sys.path.insert(0, str(backend_dir))

from app.video.srt import generate_srt_from_audio_and_text
from app.video.ffmpeg_utils import burn_text_overlay

def debug_subtitle_pipeline():
    """Debug the subtitle generation and rendering pipeline."""
    
    # Get the latest generated video
    video_dir = Path("app/video/media/generated_videos")
    video_files = list(video_dir.glob("*.mp4"))
    
    if not video_files:
        print("No generated videos found!")
        return
    
    # Use the most recent video
    latest_video = max(video_files, key=lambda x: x.stat().st_mtime)
    print(f"Using video: {latest_video}")
    
    # Extract the job ID
    job_id = latest_video.stem
    print(f"Job ID: {job_id}")
    
    # Check if corresponding audio exists
    audio_file = video_dir / f"{job_id}.mp3"
    if not audio_file.exists():
        print(f"Audio file not found: {audio_file}")
        print("Let's create a test SRT from the video itself...")
        
        # Use a sample text for testing
        test_text = "This is a test story about Reddit. The words should appear one by one with a nice glow effect. Each word should be perfectly timed to the audio."
        
        # Create test audio file path (we'll use video for timing)
        test_srt_file = video_dir / f"{job_id}_debug.srt"
        
        try:
            # Generate SRT using the video file as audio source
            print("Generating SRT from video...")
            srt_content = generate_srt_from_audio_and_text(str(latest_video), test_text)
            
            # Save the SRT file
            with open(test_srt_file, 'w') as f:
                f.write(srt_content)
            
            print(f"SRT file created: {test_srt_file}")
            print("SRT Content Preview:")
            print("-" * 50)
            print(srt_content[:500] + "..." if len(srt_content) > 500 else srt_content)
            print("-" * 50)
            
            # Test subtitle rendering
            debug_video = video_dir / f"{job_id}_debug_subtitles.mp4"
            print(f"Creating debug video with subtitles: {debug_video}")
            
            burn_text_overlay(str(latest_video), str(test_srt_file), str(debug_video))
            
            print(f"Debug video created: {debug_video}")
            print("Check the debug video to see if subtitles are working!")
            
        except Exception as e:
            print(f"Error in subtitle pipeline: {e}")
            import traceback
            traceback.print_exc()
    
    else:
        print(f"Audio file found: {audio_file}")

if __name__ == "__main__":
    debug_subtitle_pipeline()
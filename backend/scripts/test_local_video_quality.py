#!/usr/bin/env python3
"""
Local video quality testing script.
Generates a video from a test script without uploading to YouTube.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.video.generator import generate_video_from_text
import os

# Test script - you can modify this
TEST_SCRIPT = """
AITA for refusing to attend my sister's wedding after she uninvited my husband?

So this whole situation started three months ago when my sister got engaged. 
I was thrilled for her and immediately assumed my husband would be invited since we've been married for five years.

Last week, she called me and dropped a bomb. She said that to "keep the peace" with our conservative grandmother, 
she's decided to make it a "no plus ones" wedding for cousins. The thing is, my husband isn't a plus one, he's my spouse.

I told her this was ridiculous and that I wouldn't come without him. She got defensive and said I was being selfish 
and making her wedding about me. But here's the kicker - her fiancé's siblings are all bringing their spouses.

When I pointed this out, she said that's different because they're "his family." I'm so hurt and confused. 
My husband has been nothing but kind to everyone in our family.

So I told her if he's not invited, I won't be there either. Now my whole family is calling me dramatic 
and saying I'm ruining her special day. Am I the asshole here?
"""

# Configuration
BASE_VIDEO = "minecraft_parkour_base.mp4"  # Base video file
OUTPUT_DIR = Path(__file__).parent.parent / "app" / "video" / "media" / "test_videos"

def main():
    print("=" * 80)
    print("🎬 LOCAL VIDEO QUALITY TEST")
    print("=" * 80)
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("\n📝 Test Script:")
    print("-" * 80)
    print(TEST_SCRIPT.strip())
    print("-" * 80)
    
    print("\n🎥 Generating video...")
    print(f"   Base video: {BASE_VIDEO}")
    print(f"   Output directory: {OUTPUT_DIR}")
    
    try:
        # Generate video
        video_path = generate_video_from_text(
            text=TEST_SCRIPT.strip(),
            base_video_name=BASE_VIDEO,
            job_id="quality_test",
            voice_type="male",
            story_title="AITA for refusing to attend my sister's wedding?",
            subreddit="r/AmItheAsshole"
        )
        
        print("\n✅ Video generated successfully!")
        print(f"📍 Location: {video_path}")
        
        # Get file size
        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        print(f"📦 File size: {file_size_mb:.2f} MB")
        
        # Get video info
        import subprocess
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', video_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            import json
            info = json.loads(result.stdout)
            
            print("\n📊 Video Information:")
            for stream in info.get('streams', []):
                if stream.get('codec_type') == 'video':
                    print(f"   Video codec: {stream.get('codec_name')}")
                    print(f"   Resolution: {stream.get('width')}x{stream.get('height')}")
                    print(f"   Frame rate: {stream.get('r_frame_rate')}")
                    print(f"   Bitrate: {int(stream.get('bit_rate', 0)) // 1000} kbps")
                elif stream.get('codec_type') == 'audio':
                    print(f"   Audio codec: {stream.get('codec_name')}")
                    print(f"   Sample rate: {stream.get('sample_rate')} Hz")
                    print(f"   Channels: {stream.get('channels')}")
                    print(f"   Audio bitrate: {int(stream.get('bit_rate', 0)) // 1000} kbps")
            
            duration = float(info.get('format', {}).get('duration', 0))
            print(f"   Duration: {duration:.2f} seconds")
        
        print("\n" + "=" * 80)
        print("🎯 Next Steps:")
        print("1. Open the video and check:")
        print("   - Audio quality (volume, clarity, depth)")
        print("   - Video quality (resolution, clarity)")
        print("   - Subtitle timing and readability")
        print("2. If quality is good, this is what YouTube will receive")
        print("3. Adjust settings in subtitle_config.py if needed:")
        print("   - AUDIO_ENHANCEMENT_LEVEL (off/low/medium/high/extreme)")
        print("   - AUDIO_BITRATE (128k/192k for better quality)")
        print("   - VIDEO_SPEED_MULTIPLIER (1.0 = normal speed)")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error generating video: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

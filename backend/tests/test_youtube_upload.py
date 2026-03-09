#!/usr/bin/env python3
"""
One-shot YouTube upload test.
Uploads the most recent generated video as a private Short.
Run from the backend/ directory:
    python -m tests.test_youtube_upload
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.youtube_service import YouTubeService

VIDEO_DIR = BACKEND_DIR / "app" / "video" / "media" / "generated_videos"

def main():
    # Find the most recent .mp4
    videos = sorted(VIDEO_DIR.glob("*.mp4"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not videos:
        print("No videos found in generated_videos/. Run the test script first.")
        sys.exit(1)

    video_path = videos[0]
    print(f"Uploading: {video_path.name}")

    svc = YouTubeService()
    svc.authenticate()  # opens browser for consent on first run

    video_id = svc.upload_video(
        video_path=str(video_path),
        title="The Open Door",
        description="Something was behind the mirror.\n\n#shorts #horror #reddit #scarystory",
        tags=["horror", "scary", "reddit story", "creepy"],
        privacy_status="private",  # safe first test — change to public when ready
    )

    if video_id:
        print(f"\nDONE")
        print(f"Video ID : {video_id}")
        print(f"URL      : https://youtube.com/shorts/{video_id}")
    else:
        print("\nUpload failed — check logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()

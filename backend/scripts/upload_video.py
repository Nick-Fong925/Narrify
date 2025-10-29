#!/usr/bin/env python3
"""
Manual YouTube upload script.
Upload a single video file to YouTube with metadata.
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.youtube_service import youtube_service
from app.utils.logger import logger


def main():
    parser = argparse.ArgumentParser(
        description='Upload a video file to YouTube'
    )
    parser.add_argument(
        'video_path',
        help='Path to video file'
    )
    parser.add_argument(
        '--title',
        required=True,
        help='Video title'
    )
    parser.add_argument(
        '--description',
        default='',
        help='Video description'
    )
    parser.add_argument(
        '--tags',
        nargs='+',
        default=[],
        help='Video tags (space-separated)'
    )
    parser.add_argument(
        '--privacy',
        choices=['public', 'unlisted', 'private'],
        default='public',
        help='Privacy status'
    )
    
    args = parser.parse_args()
    
    # Check if file exists
    video_file = Path(args.video_path)
    if not video_file.exists():
        print(f"Error: Video file not found: {args.video_path}")
        sys.exit(1)
    
    print(f"\nUploading video to YouTube...")
    print(f"File: {args.video_path}")
    print(f"Title: {args.title}")
    print(f"Privacy: {args.privacy}")
    
    # Upload
    video_id = youtube_service.upload_video(
        video_path=str(video_file),
        title=args.title,
        description=args.description,
        tags=args.tags,
        privacy_status=args.privacy
    )
    
    if video_id:
        print(f"\n✅ Upload successful!")
        print(f"Video ID: {video_id}")
        print(f"URL: https://youtube.com/shorts/{video_id}")
    else:
        print(f"\n❌ Upload failed. Check logs for details.")
        sys.exit(1)


if __name__ == '__main__':
    main()

import subprocess
from pathlib import Path
import json
import random


def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        video_path
    ]
    result = subprocess.check_output(cmd)
    data = json.loads(result)
    return float(data["format"]["duration"])


def get_video_dimensions(video_path: str) -> tuple:
    """Get video width and height using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        video_path
    ]
    result = subprocess.check_output(cmd)
    data = json.loads(result)
    stream = data["streams"][0]
    return int(stream["width"]), int(stream["height"])


def merge_audio_with_video(base_video: str, audio_file: str, out_video: str, start_time: float = None, duration: float = None):
    """Mute base video and overlay audio track, writing to out_video.
    Automatically detects horizontal videos and applies 9:16 center crop for vertical format.
    
    Args:
        start_time: Optional start time in seconds to begin video segment
        duration: Optional duration in seconds for video segment
    """
    out = Path(out_video)
    out.parent.mkdir(parents=True, exist_ok=True)
    
    # Get video dimensions to determine if cropping is needed
    width, height = get_video_dimensions(base_video)
    aspect_ratio = width / height
    
    # Target aspect ratio for vertical video (9:16)
    target_aspect = 9 / 16  # 0.5625
    
    # Determine if we need to crop (horizontal or square video)
    needs_crop = aspect_ratio > target_aspect
    
    cmd = ["ffmpeg", "-y"]
    
    # Add start time if specified
    if start_time is not None:
        cmd.extend(["-ss", str(start_time)])
    
    cmd.extend(["-i", base_video, "-i", audio_file])
    
    # Add duration if specified
    if duration is not None:
        cmd.extend(["-t", str(duration)])
    
    if needs_crop:
        # Calculate crop dimensions for 9:16 aspect ratio (center crop)
        # out_width:out_height = 9:16
        # We want the maximum height, then calculate width
        crop_height = height
        crop_width = int(crop_height * target_aspect)
        
        # If calculated width exceeds source width, use width as constraint
        if crop_width > width:
            crop_width = width
            crop_height = int(crop_width / target_aspect)
        
        # Center crop position
        crop_x = (width - crop_width) // 2
        crop_y = (height - crop_height) // 2
        
        print(f"🎬 Auto-cropping {width}x{height} → {crop_width}x{crop_height} (center crop for 9:16)")
        
        from app.video.subtitle_config import VIDEO_CRF, VIDEO_PRESET
        
        cmd.extend([
            "-vf", f"crop={crop_width}:{crop_height}:{crop_x}:{crop_y}",
            "-c:v", "libx264",
            "-preset", VIDEO_PRESET,  # Use config preset (now "veryfast")
            "-crf", str(VIDEO_CRF),   # Use config CRF (now 23)
            "-r", "30",  # Reduce to 30fps for lower processing requirements
            "-c:a", "aac",
            "-b:a", "128k",  # Reduced audio bitrate
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            # Strip all metadata from source video
            "-map_metadata", "-1",
            "-fflags", "+bitexact",
            str(out),
        ])
    else:
        # Video is already vertical, just merge audio
        print(f"✓ Video is already vertical {width}x{height}, merging audio only")
        cmd.extend([
            # Copy video stream, encode audio stream
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            # Strip all metadata from source video
            "-map_metadata", "-1",
            "-fflags", "+bitexact",
            str(out),
        ])
    
    subprocess.check_call(cmd)
    return str(out)


import subprocess
import os
from pathlib import Path

def format_ass_time(seconds):
    """Convert seconds to ASS time format (H:MM:SS.CC)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:05.2f}"

def parse_srt_for_drawtext(srt_path):
    """Parse SRT file and return list of words with timing"""
    words_with_timing = []
    
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    # Split into subtitle blocks
    blocks = content.split('\n\n')
    
    for block in blocks:
        if not block.strip():
            continue
            
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        
        # Parse timing line (format: 00:00:01,000 --> 00:00:02,500)
        timing_line = lines[1]
        start_str, end_str = timing_line.split(' --> ')
        
        # Convert to seconds
        start_time = srt_time_to_seconds(start_str)
        end_time = srt_time_to_seconds(end_str)
        
        # Get text (everything after timing line)
        text = ' '.join(lines[2:])
        
        # Store word with timing
        words_with_timing.append({
            'word': text,
            'start': start_time,
            'end': end_time
        })
    
    return words_with_timing

def srt_time_to_seconds(time_str):
    """Convert SRT time format to seconds"""
    # Format: 00:00:01,000
    time_part, ms_part = time_str.split(',')
    h, m, s = map(int, time_part.split(':'))
    ms = int(ms_part)
    return h * 3600 + m * 60 + s + ms / 1000.0

def generate_ass_subtitles(words_with_timing, output_path, video_width=810, video_height=1440):
    """Generate ASS subtitle file respecting the phrase groupings from SRT"""
    
    # Calculate font size based on video height (proportional scaling)
    # Base: 36pt for 854px height → ~60pt for 1440px height
    # Formula: (video_height / 854) * 36 ≈ 60 for 1440px
    base_font_size = 36
    base_height = 854
    scaled_font_size = int((video_height / base_height) * base_font_size)
    
    # Scale outline and shadow proportionally too
    base_outline = 3
    base_shadow = 2
    scaled_outline = int((video_height / base_height) * base_outline)
    scaled_shadow = int((video_height / base_height) * base_shadow)
    
    # ASS header with bold white text, black outline, and shadow - no background box
    # Color format: &HAABBGGRR (Alpha, Blue, Green, Red in hex)
    # &H00FFFFFF = white text, &H00000000 = black outline
    # BorderStyle=1 with Outline creates a strong black border around text
    # Shadow adds depth
    ass_content = f"""[Script Info]
Title: Generated Subtitles
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{scaled_font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,105,100,0,0,1,{scaled_outline},{scaled_shadow},5,10,10,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    # Use the phrases exactly as they come from the SRT file
    # Each item in words_with_timing already represents a complete phrase
    phrases = []
    for word_data in words_with_timing:
        phrases.append({
            'start': word_data['start'],
            'end': word_data['end'],
            'text': word_data['word']  # This is actually the full phrase text from SRT
        })
    
    # Add each phrase with timing
    # Each phrase replaces the previous one by having consecutive timing
    for i, phrase in enumerate(phrases):
        start_time = format_ass_time(phrase['start'])
        # Make each phrase last until the next one starts (no gaps)
        if i < len(phrases) - 1:
            end_time = format_ass_time(phrases[i + 1]['start'])
        else:
            end_time = format_ass_time(phrase['end'])
        
        text = phrase['text']
        
        # White text with bold styling
        ass_content += f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n"
    
    # Write ASS file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)

def burn_text_overlay(video_path, srt_path, output_path, speed_multiplier=1.0):
    """
    Burn text overlay onto video using ASS subtitles with word-level timing.
    Uses high quality encoding settings to preserve video quality.
    Optionally applies video speed-up in the same pass to avoid double re-encoding.
    
    Args:
        video_path: Input video path
        srt_path: SRT subtitle file path
        output_path: Output video path
        speed_multiplier: If > 1.0, speeds up video in the same encoding pass
    """
    # Parse SRT file to get timing and text
    words_with_timing = parse_srt_for_drawtext(srt_path)
    
    # Generate ASS subtitle file
    ass_path = output_path.replace('.mp4', '.ass')
    generate_ass_subtitles(words_with_timing, ass_path)
    
    # Build video and audio filters
    video_filters = [f"ass='{ass_path}'"]
    audio_filters = []
    
    # Add speed-up filters if needed (combine in single pass)
    if speed_multiplier != 1.0:
        video_filters.append(f"setpts=PTS/{speed_multiplier}")
        
        # Handle audio tempo (chain if > 2.0)
        remaining_speed = speed_multiplier
        while remaining_speed > 2.0:
            audio_filters.append("atempo=2.0")
            remaining_speed /= 2.0
        while remaining_speed < 0.5:
            audio_filters.append("atempo=0.5")
            remaining_speed /= 0.5
        audio_filters.append(f"atempo={remaining_speed}")
    
    # Build ffmpeg command with high quality encoding
    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-vf', ','.join(video_filters),
    ]
    
    # Add audio filter if needed
    if audio_filters:
        cmd.extend(['-af', ','.join(audio_filters)])
    else:
        cmd.extend(['-c:a', 'copy'])  # Copy audio if no speed change
    
    # High quality video encoding settings
    from app.video.subtitle_config import VIDEO_CRF, VIDEO_PRESET, VIDEO_BITRATE_MAX
    
    cmd.extend([
        '-c:v', 'libx264',
        '-preset', VIDEO_PRESET,  # Use config preset (now "veryfast" for low RAM)
        '-crf', str(VIDEO_CRF),   # Use config CRF (now 23 for smaller files)
        '-maxrate', VIDEO_BITRATE_MAX,  # Use config max bitrate (now 4M)
        '-bufsize', '4M',  # Reduced from 16M → 8M → 4M for minimal RAM usage
        '-r', '30',  # Reduce framerate from 60fps to 30fps (50% less data to process)
        '-pix_fmt', 'yuv420p',
        '-profile:v', 'high',  # H.264 High profile for better compression
        '-level', '4.0',
        # Audio settings (if re-encoding)
        '-c:a', 'aac' if audio_filters else 'copy',
        '-b:a', '128k' if audio_filters else None,  # Reduced from 192k to 128k
        # Remove metadata
        '-map_metadata', '-1',
        '-fflags', '+bitexact',
        output_path
    ])
    
    # Remove None values
    cmd = [c for c in cmd if c is not None]
    
    subprocess.check_call(cmd)

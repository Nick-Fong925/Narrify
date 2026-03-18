import subprocess
from pathlib import Path
import json
from app.config import settings


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


def merge_audio_with_video(base_video: str, audio_file: str, output_path: str, start_time: float = None, duration: float = None):
    """Mute base video and overlay audio track, writing to output_path.
    Automatically detects horizontal videos and applies 9:16 center crop for vertical format.

    Args:
        start_time: Optional start time in seconds to begin video segment
        duration: Optional duration in seconds for video segment
    """
    out = Path(output_path)
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
        
        print(f"Auto-cropping {width}x{height} -> {crop_width}x{crop_height} (center crop for 9:16)")
        
        if settings.video.use_nvenc:
            encode_args = ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "23"]
        else:
            encode_args = ["-c:v", "libx264", "-preset", settings.video.video_preset, "-crf", str(settings.video.video_crf)]

        cmd.extend([
            "-vf", f"crop={crop_width}:{crop_height}:{crop_x}:{crop_y}",
            *encode_args,
            "-r", "30",
            "-c:a", "aac",
            "-b:a", "192k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            "-map_metadata", "-1",
            "-fflags", "+bitexact",
            str(out),
        ])
    else:
        # Video is already vertical, just merge audio
        print(f"Video is already vertical {width}x{height}, merging audio only")
        cmd.extend([
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            "-map_metadata", "-1",
            "-fflags", "+bitexact",
            str(out),
        ])
    
    subprocess.check_call(cmd)
    return output_path


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

def generate_ass_subtitles(words_with_timing, output_path, video_width=1080, video_height=1920):
    """Generate ASS subtitle file with karaoke-style word highlighting.

    Words are grouped into display phrases (per subtitle settings). For each word
    in a phrase, one Dialogue line is emitted showing the full phrase with the
    active word highlighted in yellow and surrounding words in white.
    """
    base_font_size = 36
    base_height = 854
    scaled_font_size = int((video_height / base_height) * base_font_size)
    scaled_outline = int((video_height / base_height) * 3)
    scaled_shadow = int((video_height / base_height) * 2)

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

    # Group individual words into display phrases
    words_min = settings.video.words_per_subtitle_min
    words_max = settings.video.words_per_subtitle_max
    break_punct = settings.video.break_punctuation

    phrases = []
    i = 0
    while i < len(words_with_timing):
        phrase = []
        while i < len(words_with_timing) and len(phrase) < words_max:
            phrase.append(words_with_timing[i])
            i += 1
            if len(phrase) >= words_min and phrase[-1]['word'] and phrase[-1]['word'][-1] in break_punct:
                break
        if phrase:
            phrases.append(phrase)

    # Emit one Dialogue line per word — active word yellow, rest white
    for phrase in phrases:
        for w_idx, word_data in enumerate(phrase):
            start_time = format_ass_time(word_data['start'])
            if w_idx < len(phrase) - 1:
                end_time = format_ass_time(phrase[w_idx + 1]['start'])
            else:
                end_time = format_ass_time(word_data['end'])

            parts = []
            for j, w in enumerate(phrase):
                if j == w_idx:
                    parts.append(f"{{\\c&H0000FFFF&}}{w['word']}{{\\c&HFFFFFF&}}")
                else:
                    parts.append(w['word'])
            text = ' '.join(parts)

            ass_content += f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)

def encode_final_video(
    base_video: str,
    audio_file: str,
    ass_file: str,
    output_path: str,
    start_time: float = None,
    duration: float = None,
    speed_multiplier: float = 1.0,
    metadata: dict = None,
):
    """Single-pass encode: crop base video, mux audio, burn ASS subtitles, apply speed-up,
    and write metadata — all in one ffmpeg call.

    Replaces the old two-pass merge_audio_with_video → burn_text_overlay pipeline.
    Decodes the source only once, eliminating one full lossy re-encode.

    Args:
        base_video:      Path to the (possibly horizontal) source video.
        audio_file:      Path to the enhanced TTS audio (MP3).
        ass_file:        Path to the ASS subtitle file.
        output_path:     Path for the final MP4.
        start_time:      Seconds into base_video to start the clip.
        duration:        Length of the clip in seconds (None = until audio ends).
        speed_multiplier: Playback speed (1.3 = 30% faster, applied via setpts + atempo).
        metadata:        Optional dict of ffmpeg -metadata key=value pairs.
    """
    width, height = get_video_dimensions(base_video)
    aspect_ratio = width / height
    target_aspect = 9 / 16

    # Calculate crop dimensions for 9:16 (center crop)
    if aspect_ratio > target_aspect:
        crop_height = height
        crop_width = int(crop_height * target_aspect)
        if crop_width > width:
            crop_width = width
            crop_height = int(crop_width / target_aspect)
        crop_x = (width - crop_width) // 2
        crop_y = (height - crop_height) // 2
        print(f"Single-pass encode: crop {width}x{height} -> {crop_width}x{crop_height}, "
              f"speed={speed_multiplier}x")
    else:
        crop_width, crop_height, crop_x, crop_y = width, height, 0, 0
        print(f"Single-pass encode: no crop ({width}x{height}), speed={speed_multiplier}x")

    # ASS path needs forward slashes and escaped colons for ffmpeg on Windows
    ass_ffmpeg = ass_file.replace('\\', '/').replace(':', '\\:')

    # Build video filter chain: crop → scale to 1080x1920 → subtitles
    # Video plays at natural speed; only audio is sped up via atempo
    vf_parts = [f"crop={crop_width}:{crop_height}:{crop_x}:{crop_y}", "scale=1080:1920", f"ass='{ass_ffmpeg}'"]

    # Build audio filter chain: speed (chain atempo if > 2.0)
    af_parts = []
    if speed_multiplier != 1.0:
        remaining = speed_multiplier
        while remaining > 2.0:
            af_parts.append("atempo=2.0")
            remaining /= 2.0
        while remaining < 0.5:
            af_parts.append("atempo=0.5")
            remaining /= 0.5
        af_parts.append(f"atempo={remaining}")

    cmd = ["ffmpeg", "-y"]
    if start_time is not None:
        cmd.extend(["-ss", str(start_time)])
    if duration is not None:
        cmd.extend(["-t", str(duration)])  # Input duration for base video (before -i)
    cmd.extend(["-i", base_video, "-i", audio_file])

    cmd.extend([
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-vf", ",".join(vf_parts),
        "-r", "30",
        "-pix_fmt", "yuv420p",
        "-profile:v", "high",
        "-level", "4.0",
    ])

    if af_parts:
        cmd.extend(["-af", ",".join(af_parts)])

    # Video encoder: NVENC (GPU) with quality equivalent to CRF 20, fallback to libx264
    if settings.video.use_nvenc:
        cmd.extend(["-c:v", "h264_nvenc", "-preset", "p4", "-cq", str(settings.video.video_crf),
                    "-maxrate", settings.video.video_bitrate_max, "-bufsize", "8M"])
    else:
        cmd.extend(["-c:v", "libx264", "-preset", settings.video.video_preset, "-crf", str(settings.video.video_crf),
                    "-maxrate", settings.video.video_bitrate_max, "-bufsize", "8M"])

    # Audio encoder: always re-encode (atempo or not, we're muxing new audio)
    cmd.extend(["-c:a", "aac", "-b:a", settings.video.audio_bitrate])

    cmd.extend(["-shortest"])

    if metadata:
        for key, value in metadata.items():
            safe_value = str(value).replace('\\', '\\\\').replace('"', '\\"')
            cmd.extend(["-metadata", f"{key}={safe_value}"])
        cmd.extend(["-movflags", "+faststart"])
    else:
        cmd.extend(["-map_metadata", "-1", "-fflags", "+bitexact"])

    cmd.append(output_path)
    subprocess.check_call(cmd)


def burn_text_overlay(video_path, srt_path, output_path, speed_multiplier=1.0, metadata=None):
    """Burn ASS subtitles onto video, optionally speeding up and writing metadata in the same pass.

    Args:
        metadata: Optional dict of ffmpeg -metadata key=value pairs. When provided,
                  metadata is written directly into the output file and -movflags +faststart
                  is added for streaming optimisation. When None, metadata is stripped.
    """
    words_with_timing = parse_srt_for_drawtext(srt_path)
    ass_path = output_path.replace('.mp4', '.ass')
    generate_ass_subtitles(words_with_timing, ass_path)

    # On Windows, ffmpeg's ass filter requires forward slashes and escaped colons
    ass_path_ffmpeg = ass_path.replace('\\', '/').replace(':', '\\:')
    video_filters = [f"ass='{ass_path_ffmpeg}'"]
    audio_filters = []

    if speed_multiplier != 1.0:
        video_filters.append(f"setpts=PTS/{speed_multiplier}")
        remaining_speed = speed_multiplier
        while remaining_speed > 2.0:
            audio_filters.append("atempo=2.0")
            remaining_speed /= 2.0
        while remaining_speed < 0.5:
            audio_filters.append("atempo=0.5")
            remaining_speed /= 0.5
        audio_filters.append(f"atempo={remaining_speed}")

    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-vf', ','.join(video_filters),
    ]

    if audio_filters:
        cmd.extend(['-af', ','.join(audio_filters)])

    cmd.extend([
        '-c:v', 'libx264',
        '-preset', settings.video.video_preset,
        '-crf', str(settings.video.video_crf),
        '-maxrate', settings.video.video_bitrate_max,
        '-bufsize', '4M',
        '-r', '30',
        '-pix_fmt', 'yuv420p',
        '-profile:v', 'high',
        '-level', '4.0',
    ])

    if audio_filters:
        cmd.extend(['-c:a', 'aac', '-b:a', '192k'])
    else:
        cmd.extend(['-c:a', 'copy'])

    if metadata:
        for key, value in metadata.items():
            safe_value = str(value).replace('\\', '\\\\').replace('"', '\\"')
            cmd.extend(['-metadata', f'{key}={safe_value}'])
        cmd.extend(['-movflags', '+faststart'])
    else:
        cmd.extend(['-map_metadata', '-1', '-fflags', '+bitexact'])

    cmd.append(output_path)

    subprocess.check_call(cmd)

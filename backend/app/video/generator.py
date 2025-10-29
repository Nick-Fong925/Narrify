from pathlib import Path
import uuid
import random
import subprocess
from app.video.tts import text_to_speech
from app.video.ffmpeg_utils import merge_audio_with_video, burn_text_overlay, get_video_duration
from app.video.srt import generate_srt_from_audio_and_text
from app.video.subtitle_config import (
    VIDEO_SPEED_MULTIPLIER,
    NARRATE_TITLE,
    VIDEO_CRF,
    VIDEO_PRESET,
    VIDEO_BITRATE_MAX
)

BASE_DIR = Path(__file__).resolve().parent / "media"
BASE_VIDEOS = BASE_DIR / "base_videos"
OUT_DIR = BASE_DIR / "generated_videos"


def estimate_audio_duration(text: str, words_per_second: float = 2.5) -> float:
    """Estimate audio duration based on word count and speaking rate."""
    word_count = len(text.split())
    return word_count / words_per_second


def speed_up_video(input_path: str, output_path: str, speed: float = 1.25):
    """
    Speed up video and audio by a given multiplier.
    
    Args:
        input_path: Input video path
        output_path: Output video path
        speed: Speed multiplier (1.0 = normal, 1.25 = 25% faster, 1.5 = 50% faster)
    """
    print(f"⚡ Speeding up video to {speed}x...")
    
    # Calculate audio tempo and video speed
    # For speed 1.25: video plays 1.25x faster, audio tempo increases by 1.25x
    video_speed = speed
    audio_tempo = speed
    
    # Use ffmpeg to speed up both video and audio
    # -filter:v "setpts=PTS/speed" speeds up video
    # -filter:a "atempo=speed" speeds up audio (preserves pitch)
    # atempo only supports 0.5-2.0, so we may need to chain multiple filters
    
    audio_filters = []
    remaining_speed = audio_tempo
    
    # Chain atempo filters if speed > 2.0
    while remaining_speed > 2.0:
        audio_filters.append("atempo=2.0")
        remaining_speed /= 2.0
    
    while remaining_speed < 0.5:
        audio_filters.append("atempo=0.5")
        remaining_speed /= 0.5
    
    audio_filters.append(f"atempo={remaining_speed}")
    
    audio_filter_str = ",".join(audio_filters)
    
    cmd = [
        'ffmpeg', '-y',
        '-i', input_path,
        '-filter:v', f'setpts=PTS/{video_speed}',  # Speed up video
        '-filter:a', audio_filter_str,  # Speed up audio
        '-c:v', 'libx264',  # Re-encode video
        '-preset', VIDEO_PRESET,  # Encoding quality preset
        '-crf', str(VIDEO_CRF),  # Quality (lower = better)
        '-maxrate', VIDEO_BITRATE_MAX,  # Max bitrate for quality
        '-bufsize', '10M',  # Buffer size for bitrate control
        '-pix_fmt', 'yuv420p',  # Pixel format for compatibility
        '-c:a', 'aac',  # Audio codec
        '-b:a', '192k',  # High audio bitrate for YouTube
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Video speed adjustment failed: {result.stderr}")
    
    print(f"✅ Video sped up to {speed}x successfully!")
    return output_path


def generate_video_from_text(text: str, base_video_name: str, job_id: str = None, voice_type: str = "male", 
                            story_title: str = None, subreddit: str = None):
    """Create an mp4 by generating audio from text, selecting a random portion of base video, overlaying audio and burning SRT captions.

    Args:
        text: Story text to convert to speech (original text with contractions for subtitles)
        base_video_name: Base video filename
        job_id: Unique job identifier
        voice_type: Voice type for TTS
        story_title: Original story title (for narration and metadata)
        subreddit: Source subreddit (for metadata)

    Returns: path to generated video
    """
    job_id = job_id or str(uuid.uuid4())
    base_video = BASE_VIDEOS / base_video_name
    if not base_video.exists():
        raise FileNotFoundError(f"Base video not found: {base_video}")

    out_audio = OUT_DIR / f"{job_id}.mp3"
    out_srt = OUT_DIR / f"{job_id}.srt"
    out_temp = OUT_DIR / f"{job_id}.temp.mp4"
    out_temp_final = OUT_DIR / f"{job_id}.temp_final.mp4"
    out_temp_sped = OUT_DIR / f"{job_id}.temp_sped.mp4"
    out_final = OUT_DIR / f"{job_id}.mp4"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Track all intermediate files for cleanup (even on error)
    intermediate_files = [out_audio, out_srt, out_temp, out_temp_final, out_temp_sped]
    
    try:
        # 1) Prepend title to text if configured
        full_text = text
        if NARRATE_TITLE and story_title:
            # Add title at the beginning with a pause
            full_text = f"{story_title}. {text}"
            print(f"🎙️ Will narrate title: '{story_title}'")

        # 2) Generate audio using TTS-optimized text (expanded contractions)
        # text_to_speech() will preprocess text internally (expand contractions, etc.)
        # We need to get the SAME preprocessed text for subtitles to match audio perfectly
        from app.utils.text_cleaning import prepare_text_for_tts
        tts_text = prepare_text_for_tts(full_text)  # This is what will be spoken
        
        text_to_speech(full_text, str(out_audio), voice_type=voice_type)
        
        # Free up TTS memory immediately after generation
        from app.video.tts import cleanup_tts_memory
        cleanup_tts_memory()

        # 3) Generate SRT with perfect timing based on actual audio duration
        # Use TTS-PREPROCESSED text (expanded contractions) for subtitles
        # This ensures Whisper timing matches subtitle text 1:1 (no complex mapping needed)
        # Example: Audio says "he is" → Whisper detects "he is" → Subtitles show "he is" ✅
        srt_content = generate_srt_from_audio_and_text(
            str(out_audio), 
            tts_text,  # Use expanded text to match what Whisper hears in the audio
            speed_multiplier=VIDEO_SPEED_MULTIPLIER  # Adjust timing for speed-up
        )
        with open(out_srt, 'w') as f:
            f.write(srt_content)

        # 3) Calculate random start time for base video
        estimated_duration = estimate_audio_duration(text)
        video_duration = get_video_duration(str(base_video))
        
        # Add some buffer to ensure we have enough video
        needed_duration = estimated_duration + 5  # 5 second buffer
        
        if video_duration <= needed_duration:
            # Use entire video if it's not much longer than needed
            start_time = 0
            segment_duration = None
        else:
            # Pick random start time ensuring we have enough video left
            max_start = video_duration - needed_duration
            start_time = random.uniform(0, max_start)
            segment_duration = needed_duration

        # 4) Merge audio with random segment of base video
        merge_audio_with_video(str(base_video), str(out_audio), str(out_temp), start_time, segment_duration)

        # 5) Burn in text captions AND speed up video in single pass (avoids double re-encoding)
        # This preserves video quality by only re-encoding once
        if VIDEO_SPEED_MULTIPLIER != 1.0:
            print(f"🎬 Burning subtitles and speeding up to {VIDEO_SPEED_MULTIPLIER}x in single pass...")
            burn_text_overlay(str(out_temp), str(out_srt), str(out_temp_final), speed_multiplier=VIDEO_SPEED_MULTIPLIER)
            video_to_finalize = out_temp_final
        else:
            burn_text_overlay(str(out_temp), str(out_srt), str(out_temp_final))
            video_to_finalize = out_temp_final

        # 6) Clean up large intermediate file BEFORE metadata step to free disk space
        # The temp.mp4 is the largest file and no longer needed
        try:
            out_temp.unlink()  # Remove 154 MB temp video before metadata writing
            
            # Also clean up TTS chunk files if they exist
            chunk_files = list(OUT_DIR.glob(f"{job_id}_chunk_*.wav"))
            for chunk_file in chunk_files:
                chunk_file.unlink()
            
            if chunk_files:
                print(f"🗑️ Cleaned up temp file and {len(chunk_files)} TTS chunks to free disk space")
            else:
                print(f"🗑️ Cleaned up large temp file to free disk space")
        except Exception as e:
            print(f"Warning: Could not remove temp files: {e}")

        # 7) Add YouTube Shorts optimized metadata
        from app.video.metadata_utils import add_youtube_shorts_metadata
        add_youtube_shorts_metadata(
            str(video_to_finalize),
            str(out_final),
            title=story_title,
            subreddit=subreddit,
            text_snippet=text[:100]  # First 100 chars for description
        )

        return str(out_final)
    
    finally:
        # ALWAYS cleanup intermediate files, even if generation failed
        # This ensures disk space is freed even when errors occur
        print(f"🗑️ Cleaning up intermediate files for job {job_id}...")
        cleaned_count = 0
        
        # Clean up all tracked intermediate files
        for file_path in intermediate_files:
            if file_path.exists():
                try:
                    file_path.unlink()
                    cleaned_count += 1
                except Exception as e:
                    print(f"   Warning: Could not delete {file_path.name}: {e}")
        
        # Clean up TTS chunk files
        chunk_files = list(OUT_DIR.glob(f"{job_id}_chunk_*.wav"))
        for chunk_file in chunk_files:
            try:
                chunk_file.unlink()
                cleaned_count += 1
            except Exception as e:
                print(f"   Warning: Could not delete {chunk_file.name}: {e}")
        
        # Clean up ASS subtitle files
        ass_file = OUT_DIR / f"{job_id}.temp_final.ass"
        if ass_file.exists():
            try:
                ass_file.unlink()
                cleaned_count += 1
            except Exception as e:
                print(f"   Warning: Could not delete ASS file: {e}")
        
        if cleaned_count > 0:
            print(f"   ✅ Cleaned up {cleaned_count} intermediate files")


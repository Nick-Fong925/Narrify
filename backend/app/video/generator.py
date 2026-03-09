from pathlib import Path
import uuid
import random
from datetime import datetime
from app.video.tts import text_to_speech
from app.video.ffmpeg_utils import encode_final_video, get_video_duration
from app.video.srt import generate_srt_from_audio_and_text
from app.config import settings

BASE_DIR = Path(__file__).resolve().parent / "media"
BASE_VIDEOS = BASE_DIR / "base_videos"
OUT_DIR = BASE_DIR / "generated_videos"


def estimate_audio_duration(text: str, words_per_second: float = 2.5) -> float:
    """Estimate audio duration based on word count and speaking rate."""
    word_count = len(text.split())
    return word_count / words_per_second


def generate_video_from_text(text: str, base_video_name: str, job_id: str = None,
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
    out_ass = OUT_DIR / f"{job_id}.ass"
    out_final = OUT_DIR / f"{job_id}.mp4"

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Track all intermediate files for cleanup (even on error)
    intermediate_files = [out_audio, out_srt, out_ass]

    try:
        # 1) Prepend title to text if configured
        full_text = text
        if settings.video.narrate_title and story_title:
            # Add title at the beginning with a pause
            full_text = f"{story_title}. {text}"
            print(f"Narrating title: '{story_title}'")

        # 2) Clean text and split into TTS chunks via LLM (falls back to hard rules)
        from app.utils.text_cleaning import prepare_story_with_llm
        tts_text, chunks = prepare_story_with_llm(full_text)

        text_to_speech(full_text, str(out_audio), chunks=chunks)

        # 3) Generate SRT with perfect timing based on actual audio duration
        # Use TTS-PREPROCESSED text (expanded contractions) for subtitles
        # This ensures Whisper timing matches subtitle text 1:1 (no complex mapping needed)
        # Example: Audio says "he is" -> Whisper detects "he is" -> Subtitles show "he is" (OK)

        srt_content = generate_srt_from_audio_and_text(
            str(out_audio),
            tts_text,  # Use expanded text to match what Whisper hears in the audio
            speed_multiplier=settings.video.video_speed_multiplier
        )
        with open(out_srt, 'w') as f:
            f.write(srt_content)

        # 3) Calculate random start time for base video
        estimated_duration = estimate_audio_duration(text)
        video_duration = get_video_duration(str(base_video))

        # needed_duration is INPUT seconds for the base video (before speed-up).
        # Both video and audio scale by speed_multiplier equally, so we just need
        # the segment to cover the full audio duration (before atempo).
        needed_duration = estimated_duration + 5

        if video_duration <= needed_duration:
            start_time = 0
            segment_duration = None
        else:
            max_start = video_duration - needed_duration
            start_time = random.uniform(0, max_start)
            segment_duration = needed_duration

        # 4) Convert SRT → ASS (needed before single-pass encode)
        from app.video.ffmpeg_utils import parse_srt_for_drawtext, generate_ass_subtitles, get_video_dimensions
        # Get crop dimensions to pass correct resolution to ASS generator
        width, height = get_video_dimensions(str(base_video))
        target_aspect = 9 / 16
        if width / height > target_aspect:
            crop_height = height
            crop_width = int(crop_height * target_aspect)
            if crop_width > width:
                crop_width = width
                crop_height = int(crop_width / target_aspect)
        else:
            crop_width, crop_height = width, height
        words_with_timing = parse_srt_for_drawtext(str(out_srt))
        generate_ass_subtitles(words_with_timing, str(out_ass), video_width=crop_width, video_height=crop_height)

        # 5) Build YouTube Shorts metadata dict
        now = datetime.now()
        meta_title = (story_title[:100].strip() if story_title else 'Reddit Story')
        description_parts = []
        if text[:100]:
            description_parts.append(text[:100].strip() + '...')
        if subreddit:
            description_parts.append(f'\nFrom r/{subreddit}')
        description_parts.extend(['\n\n#RedditStories #Shorts #Storytelling', '\n\nSubscribe for more stories!'])
        keywords = ['reddit', 'stories', 'shorts'] + ([subreddit.lower()] if subreddit else [])
        video_metadata = {
            'title': meta_title,
            'description': ''.join(description_parts),
            'comment': ''.join(description_parts),
            'genre': 'Entertainment',
            'artist': 'Narrify',
            'album': 'Reddit Stories',
            'date': now.strftime('%Y%m%d'),
            'year': now.strftime('%Y'),
            'copyright': f'© {now.year} Narrify',
            'keywords': ', '.join(keywords),
        }

        # 6) Single-pass encode: crop + subtitles + speed-up + metadata → final output
        print(f"Single-pass encode: crop, burn subtitles, speed up {settings.video.video_speed_multiplier}x, write metadata...")
        encode_final_video(
            base_video=str(base_video),
            audio_file=str(out_audio),
            ass_file=str(out_ass),
            output_path=str(out_final),
            start_time=start_time,
            duration=segment_duration,
            speed_multiplier=settings.video.video_speed_multiplier,
            metadata=video_metadata,
        )

        return str(out_final)

    finally:
        # ALWAYS cleanup intermediate files, even if generation failed
        # This ensures disk space is freed even when errors occur
        print(f"Cleaning up intermediate files for job {job_id}...")
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

        if cleaned_count > 0:
            print(f"   Cleaned up {cleaned_count} intermediate files")

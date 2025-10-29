from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.reddit_scraper import RedditScraper
from app.models.post import Post
from app.db import SessionLocal
from app.utils.text_cleaning import clean_story, word_count
from app.video.generator import generate_video_from_text
from typing import Optional
from pydantic import BaseModel
import uuid
from pathlib import Path

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

DEFAULT_SUBREDDIT = "AmItheAsshole"
EXAMPLE_SUBREDDITS = [
    "AmItheAsshole",
    "relationships",
    "TrueOffMyChest",
    "relationship_advice",
    "tifu"
]

class ScrapeRequest(BaseModel):
    """
    subreddit: str = subreddit to scrape from (e.g. "AmItheAsshole", "relationships", "TrueOffMyChest", "relationship_advice", "tifu")
    min_score: int = minimum score (default 500)
    """
    subreddit: Optional[str] = None
    min_score: Optional[int] = 500

class VideoRequest(BaseModel):
    """
    post_id: int = ID of post to generate video from
    base_video: str = filename of base video (optional, defaults to minecraft_parkour_base.mp4)
    voice_type: str = 'male' or 'female' voice preference
    """
    post_id: Optional[int] = None
    raw_text: Optional[str] = None
    base_video: Optional[str] = "minecraft_parkour_base.mp4"
    voice_type: Optional[str] = "male"

@router.post("/scrape/")
def scrape_and_store(
    req: ScrapeRequest,
    db: Session = Depends(get_db)
):
    subreddit = req.subreddit or DEFAULT_SUBREDDIT
    min_score = req.min_score or 500
    stored_posts = []
    min_words = 150  # ~1 minute at 2.5 words/sec
    scraper = RedditScraper(subreddit)
    posts = scraper.fetch_top_posts()
    for p in posts:
        if p["score"] >= min_score and p["story"]:
            cleaned_story = clean_story(p["story"])
            if word_count(cleaned_story) < min_words:
                continue
            exists = db.query(Post).filter_by(reddit_id=p["reddit_id"]).first()
            if not exists:
                post_obj = Post(**{**p, "story": cleaned_story})
                db.add(post_obj)
                db.flush()  # Assigns an ID
                post_dict = post_obj.__dict__.copy()
                post_dict["story"] = cleaned_story
                post_dict.pop('_sa_instance_state', None)
                stored_posts.append(post_dict)
    db.commit()
    return {"stored": len(stored_posts), "posts": stored_posts}

@router.get("/posts/")
def get_posts(
    subreddit: Optional[str] = None,
    min_score: int = 500,
    db: Session = Depends(get_db)
):
    q = db.query(Post)
    if subreddit:
        q = q.filter(Post.subreddit == subreddit)
    posts = q.filter(Post.score >= min_score).order_by(Post.score.desc()).all()
    result = []
    min_words = 150
    for post in posts:
        cleaned = clean_story(post.story)
        if word_count(cleaned) >= min_words:
            post_dict = post.__dict__.copy()
            post_dict["story"] = cleaned
            post_dict.pop('_sa_instance_state', None)
            result.append(post_dict)
    return result

@router.delete("/posts/")
def delete_all_posts(db: Session = Depends(get_db)):
    num_deleted = db.query(Post).delete()
    db.commit()
    return {"deleted": num_deleted}


@router.get("/counts/")
def get_counts(
    subreddit: Optional[str] = None,
    min_score: int = 500,
    min_words: int = 150,
    db: Session = Depends(get_db)
):
    """Return counts of posts grouped by subreddit with optional filters.

    Query params:
    - subreddit: optional single subreddit to filter to
    - min_score: minimum score to include
    - min_words: minimum cleaned-word-count to include
    """
    q = db.query(Post)
    if subreddit:
        q = q.filter(Post.subreddit == subreddit)
    q = q.filter(Post.score >= min_score)
    posts = q.all()

    by_sub = {}
    total = 0
    for post in posts:
        cleaned = clean_story(post.story)
        if word_count(cleaned) < min_words:
            continue
        total += 1
        by_sub[post.subreddit] = by_sub.get(post.subreddit, 0) + 1

    return {"total": total, "by_subreddit": by_sub}


@router.post("/video/")
def generate_video(
    req: VideoRequest,
    db: Session = Depends(get_db)
):
    """Generate a video from a reddit post or raw text."""
    if not req.post_id and not req.raw_text:
        raise HTTPException(status_code=400, detail="Either post_id or raw_text must be provided")
    
    if req.post_id:
        post = db.query(Post).filter(Post.id == req.post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        text = clean_story(post.story)
        if word_count(text) < 150:
            raise HTTPException(status_code=400, detail="Story too short for video generation")
        story_title = post.title
        subreddit = post.subreddit
    else:
        text = req.raw_text
        story_title = None
        subreddit = None
    
    job_id = str(uuid.uuid4())
    
    try:
        video_path = generate_video_from_text(
            text, 
            req.base_video, 
            job_id, 
            req.voice_type,
            story_title=story_title,
            subreddit=subreddit
        )
        return {
            "job_id": job_id,
            "status": "completed",
            "video_path": video_path,
            "message": "Video generated successfully with YouTube Shorts metadata"
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video generation failed: {str(e)}")


@router.get("/video/highest-score/")
def generate_video_from_highest_score(
    base_video: str = "minecraft_parkour_base.mp4",
    voice_type: str = "male",
    min_words: int = 150,
    db: Session = Depends(get_db)
):
    """Generate a video from the highest scoring reddit post."""
    post = db.query(Post).filter(Post.score >= 500).order_by(Post.score.desc()).first()
    if not post:
        raise HTTPException(status_code=404, detail="No high-scoring posts found")
    
    text = clean_story(post.story)
    if word_count(text) < min_words:
        raise HTTPException(status_code=400, detail="Highest scoring story too short for video generation")
    
    job_id = str(uuid.uuid4())
    
    try:
        video_path = generate_video_from_text(
            text, 
            base_video, 
            job_id, 
            voice_type,
            story_title=post.title,
            subreddit=post.subreddit
        )
        return {
            "job_id": job_id,
            "status": "completed",
            "video_path": video_path,
            "post_info": {
                "id": post.id,
                "title": post.title,
                "score": post.score,
                "subreddit": post.subreddit,
                "word_count": word_count(text)
            },
            "message": "Video generated from highest scoring post with YouTube Shorts metadata"
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video generation failed: {str(e)}")


@router.get("/video/bases/")
def list_base_videos():
    """List available base videos."""
    base_dir = Path(__file__).resolve().parent.parent.parent / "media" / "base_videos"
    if not base_dir.exists():
        return {"base_videos": []}
    
    videos = [f.name for f in base_dir.iterdir() if f.suffix.lower() in ['.mp4', '.mov', '.avi']]
    return {"base_videos": videos}

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.reddit_scraper import RedditScraper
from app.models.post import Post
from app.db import SessionLocal
from app.utils.text_cleaning import clean_story, word_count
from typing import Optional
from pydantic import BaseModel

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

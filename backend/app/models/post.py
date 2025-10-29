from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum
from datetime import datetime
from app.db import Base
import enum

class GenerationStatus(str, enum.Enum):
    """Video generation status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    reddit_id = Column(String, unique=True, index=True)
    subreddit = Column(String, index=True)
    title = Column(String)
    story = Column(Text)
    score = Column(Integer, index=True)  # Added index for sorting
    num_comments = Column(Integer)
    url = Column(String)
    
    # Video generation tracking
    generation_status = Column(String, default=GenerationStatus.PENDING.value)
    generation_error = Column(Text, nullable=True)
    generated_at = Column(DateTime, nullable=True)
    
    # YouTube posting tracking
    posted = Column(Boolean, default=False, index=True)
    posted_at = Column(DateTime, nullable=True)
    youtube_video_id = Column(String, nullable=True)
    upload_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
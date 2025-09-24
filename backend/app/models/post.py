from sqlalchemy import Column, Integer, String, Text, DateTime
from app.db import Base

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    reddit_id = Column(String, unique=True, index=True)
    subreddit = Column(String, index=True)
    title = Column(String)
    story = Column(Text)
    score = Column(Integer)
    num_comments = Column(Integer)
    url = Column(String)
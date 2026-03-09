from sqlalchemy import Column, Integer, String, Date
from app.db import Base


class ViewSnapshot(Base):
    __tablename__ = "view_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    snapshot_date = Column(Date, index=True)
    youtube_video_id = Column(String, index=True)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)

from datetime import date, timedelta
from sqlalchemy import func
from app.db import SessionLocal
from app.models.post import Post
from app.models.view_snapshot import ViewSnapshot
from app.services.youtube_service import youtube_service
from app.services.notification_service import send_daily_summary
from app.utils.logger import logger


def collect_and_report() -> None:
    today = date.today()
    yesterday = today - timedelta(days=1)
    db = SessionLocal()
    try:
        posts = db.query(Post).filter(
            Post.posted == True,
            Post.youtube_video_id != None
        ).all()

        if not posts:
            logger.info("Analytics: no live videos yet")
            return

        today_total = 0
        for post in posts:
            info = youtube_service.get_video_info(post.youtube_video_id)
            if not info:
                continue
            stats = info.get("statistics", {})
            views = int(stats.get("viewCount", 0))
            likes = int(stats.get("likeCount", 0))
            today_total += views

            snap = db.query(ViewSnapshot).filter(
                ViewSnapshot.snapshot_date == today,
                ViewSnapshot.youtube_video_id == post.youtube_video_id
            ).first()
            if snap:
                snap.view_count = views
                snap.like_count = likes
            else:
                db.add(ViewSnapshot(
                    snapshot_date=today,
                    youtube_video_id=post.youtube_video_id,
                    view_count=views,
                    like_count=likes
                ))
        db.commit()

        yesterday_total = db.query(func.sum(ViewSnapshot.view_count)).filter(
            ViewSnapshot.snapshot_date == yesterday
        ).scalar() or 0

        delta_pct = None
        if yesterday_total > 0:
            delta_pct = (today_total - yesterday_total) / yesterday_total * 100

        send_daily_summary(today_total, delta_pct, len(posts))
        logger.info(f"Analytics report sent: {today_total} views, delta={delta_pct}")

    except Exception as e:
        logger.error("Analytics collect_and_report failed", exception=e)
    finally:
        db.close()

from apscheduler.schedulers.background import BackgroundScheduler
from app.services.reddit_scraper import RedditScraper
from app.db import SessionLocal
from app.models.post import Post
from app.utils.text_cleaning import clean_story, word_count
import time
import requests

SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/your/webhook/url"  # Replace with your actual webhook

def send_slack_notification(message: str):
    payload = {"text": message}
    try:
        requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"Failed to send Slack notification: {e}")

def scheduled_scrape():
    subreddits = [
        "AmItheAsshole",
        "relationships",
        "TrueOffMyChest",
        "relationship_advice",
        "tifu"
    ]
    min_score = 500
    min_words = 150
    db = SessionLocal()
    total_new = 0
    per_subreddit = {}
    try:
        for subreddit in subreddits:
            scraper = RedditScraper(subreddit)
            # Fetch top posts from the last 6 months (t=year is closest, or t=all)
            posts = scraper.fetch_top_posts(time_filter='year', limit=100)
            new_count = 0
            for p in posts:
                if (
                    p["score"] >= min_score and
                    p["story"] and
                    word_count(clean_story(p["story"])) >= min_words
                ):
                    exists = db.query(Post).filter_by(reddit_id=p["reddit_id"]).first()
                    if not exists:
                        post_obj = Post(**{**p, "story": clean_story(p["story"])})
                        db.add(post_obj)
                        new_count += 1
            per_subreddit[subreddit] = new_count
            total_new += new_count
        db.commit()
        msg = f"Reddit scrape completed. Total new stories added: {total_new}\n" + "\n".join([
            f"{sub}: {count}" for sub, count in per_subreddit.items()
        ])
        send_slack_notification(msg)
    except Exception as e:
        send_slack_notification(f"Reddit scrape failed: {e}")
    finally:
        db.close()

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_scrape, 'interval', days=1)
    scheduler.start()

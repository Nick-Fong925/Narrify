from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.reddit_scraper import RedditScraper
from app.db import SessionLocal
from app.models.post import Post
from app.utils.text_cleaning import clean_story, word_count
from app.utils.logger import logger
from datetime import datetime
import time

def scheduled_scrape():
    """Daily Reddit scraping job"""
    logger.info(f"🔍 Starting Reddit scrape at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
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
            logger.info(f"📱 Scraping r/{subreddit}...")
            try:
                scraper = RedditScraper(subreddit)
                # Fetch top posts from the last year
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
                logger.info(f"✅ Found {new_count} new posts from r/{subreddit}")
                
                # Small delay to avoid rate limiting
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Error scraping r/{subreddit}: {e}")
                per_subreddit[subreddit] = 0
        
        db.commit()
        logger.info(f"✅ Reddit scrape completed! Total new stories: {total_new}")
        for sub, count in per_subreddit.items():
            logger.info(f"- r/{sub}: {count} new posts")

    except Exception as e:
        logger.error(f"❌ Reddit scrape failed: {e}")
        db.rollback()
    finally:
        db.close()

def start_scheduler():
    """Start the Reddit scraping scheduler"""
    scheduler = BackgroundScheduler()
    
    # Run daily at 6 AM (you can change this)
    trigger = CronTrigger(hour=6, minute=0)
    scheduler.add_job(
        scheduled_scrape, 
        trigger=trigger,
        id='reddit_scraper',
        name='Daily Reddit Scraper',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"📅 Reddit scraper scheduled to run daily at 6:00 AM")
    logger.info(f"Next run: {scheduler.get_job('reddit_scraper').next_run_time}")
    
    # Run immediately on startup for testing
    logger.info("🚀 Running initial Reddit scrape...")
    try:
        scheduled_scrape()
    except Exception as e:
        logger.error(f"⚠️ Initial scrape failed: {e}")

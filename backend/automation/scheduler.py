from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from typing import Optional
import pytz

from app.config import settings
from app.services.upload_service import upload_service
from app.services.notification_service import send_batch_complete
from app.services.analytics_service import collect_and_report
from app.scheduler import scheduled_scrape
from app.utils.logger import logger


class AutomationScheduler:
    """Scheduler for automated video generation and posting"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.timezone = pytz.timezone(settings.automation.timezone)
    
    def run_batch_job(self, batch_name: str):
        batch_time = datetime.now(self.timezone).strftime("%Y-%m-%d %H:%M:%S")
        video_count = settings.automation.videos_per_batch

        logger.automation_batch_start(
            batch_time=batch_time,
            video_count=video_count
        )

        try:
            # Step 1: Scrape Reddit fresh before generating
            logger.info("Running Reddit scrape before video generation...")
            scheduled_scrape()
            logger.info("Reddit scrape complete — starting video generation")

            # Step 2: Generate and upload batch
            successful, failed = upload_service.process_batch(
                count=video_count,
            )
            
            logger.automation_batch_complete(
                batch_time=batch_time,
                successful=successful,
                failed=failed
            )
            send_batch_complete(batch_time, successful, failed)

        except Exception as e:
            logger.error(
                f"Automation batch failed: {batch_name}",
                exception=e,
                batch_time=batch_time
            )
    
    def schedule_jobs(self):
        for i, time_str in enumerate(settings.automation.schedule_times):
            # Parse time (HH:MM format)
            hour, minute = map(int, time_str.split(':'))
            
            # Create cron trigger
            trigger = CronTrigger(
                hour=hour,
                minute=minute,
                timezone=self.timezone
            )
            
            # Schedule job
            batch_name = f"batch_{i+1}_{time_str.replace(':', '')}"
            self.scheduler.add_job(
                func=self.run_batch_job,
                trigger=trigger,
                args=[batch_name],
                id=batch_name,
                name=f"Video Generation Batch {i+1} ({time_str} EST)",
                replace_existing=True
            )
            
            logger.info(
                f"Scheduled automation batch: {batch_name}",
                time=time_str,
                timezone=settings.automation.timezone,
                videos_per_batch=settings.automation.videos_per_batch
            )

        analytics_hour, analytics_minute = map(int, settings.automation.analytics_time.split(':'))
        self.scheduler.add_job(
            func=collect_and_report,
            trigger=CronTrigger(hour=analytics_hour, minute=analytics_minute, timezone=self.timezone),
            id="daily_analytics",
            name="Daily YouTube Analytics Report",
            replace_existing=True
        )

    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.schedule_jobs()
            self.scheduler.start()
            logger.info("Automation scheduler started")
            
            # Log scheduled jobs
            jobs = self.scheduler.get_jobs()
            for job in jobs:
                logger.info(f"Scheduled job: {job.name} - Next run: {job.next_run_time}")
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Automation scheduler stopped")
    
    def run_now(self, video_count: Optional[int] = None):
        if video_count is None:
            video_count = settings.automation.videos_per_batch
        
        logger.info(f"Running immediate batch job: {video_count} videos")
        
        successful, failed = upload_service.process_batch(
            count=video_count,
        )
        
        logger.info(
            f"Immediate batch completed: {successful} successful, {failed} failed"
        )
        
        return successful, failed


# Global automation scheduler instance
automation_scheduler = AutomationScheduler()

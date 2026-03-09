#!/usr/bin/env python3
"""
Nightly automation script: scrape Reddit → generate 5 videos → schedule to YouTube.
Intended to be run by Windows Task Scheduler at 5:00 AM.

Usage:
    python scripts/run_nightly.py
    python scripts/run_nightly.py --count 3  # override video count
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.scheduler import scheduled_scrape
from app.services.upload_service import upload_service
from app.services.notification_service import send_batch_complete
from app.config import settings
from app.utils.logger import logger
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description="Nightly Narrify pipeline")
    parser.add_argument("--count", type=int, default=settings.automation.videos_per_batch)
    args = parser.parse_args()

    start = datetime.now()
    logger.info(f"Nightly pipeline started at {start.strftime('%Y-%m-%d %H:%M:%S')}")

    # Step 1: Scrape Reddit
    logger.info("Step 1/2: Scraping Reddit...")
    scheduled_scrape()

    # Step 2: Generate + upload videos
    logger.info(f"Step 2/2: Generating and uploading {args.count} videos...")
    successful, failed = upload_service.process_batch(count=args.count)

    elapsed = (datetime.now() - start).seconds // 60
    logger.info(f"Nightly pipeline complete in {elapsed}m — {successful} uploaded, {failed} failed")
    send_batch_complete(batch_time=f"{elapsed}m", successful=successful, failed=failed)
    print(f"Done: {successful} uploaded, {failed} failed ({elapsed} min)")

if __name__ == "__main__":
    main()

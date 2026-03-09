#!/usr/bin/env python3
"""
Daily analytics script: fetch YouTube view counts, snapshot to DB, send ntfy report.
Intended to be run by Windows Task Scheduler at 8:00 AM.

Usage:
    python scripts/run_analytics.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.analytics_service import collect_and_report
from app.utils.logger import logger
from datetime import datetime


def main():
    start = datetime.now()
    logger.info(f"Analytics pipeline started at {start.strftime('%Y-%m-%d %H:%M:%S')}")
    collect_and_report()
    logger.info("Analytics pipeline complete")


if __name__ == "__main__":
    main()

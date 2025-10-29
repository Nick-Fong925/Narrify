#!/usr/bin/env python3
"""
Test Reddit scraper manually
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.scheduler import scheduled_scrape

if __name__ == "__main__":
    print("🧪 Testing Reddit scraper...\n")
    scheduled_scrape()
    print("\n✅ Test complete!")

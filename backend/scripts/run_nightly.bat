@echo off
docker exec narrify python scripts/run_nightly.py >> C:\Projects\Narrify\backend\logs\nightly.log 2>&1

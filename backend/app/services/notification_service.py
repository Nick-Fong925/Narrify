import requests
from app.config import settings
from app.utils.logger import logger

NTFY_BASE = "https://ntfy.sh"


def _send(title: str, body: str, priority: str = "default") -> None:
    topic = settings.ntfy_topic
    if not topic:
        return
    try:
        requests.post(
            f"{NTFY_BASE}/{topic}",
            data=body.encode("utf-8"),
            headers={"Title": title, "Priority": priority},
            timeout=10
        )
    except Exception as e:
        logger.error("ntfy notification failed", exception=e)


def send_batch_complete(batch_time: str, successful: int, failed: int) -> None:
    total = successful + failed
    body = f"{successful}/{total} videos uploaded successfully in {batch_time}"
    if failed:
        body += f" ({failed} failed)"
    _send("Narrify Batch Complete", body, priority="high" if failed else "default")


def send_daily_summary(total_views: int, delta_pct: float | None, video_count: int) -> None:
    views_fmt = f"{total_views:,}"
    if delta_pct is not None:
        sign = "+" if delta_pct >= 0 else ""
        delta_str = f" ({sign}{delta_pct:.1f}% from yesterday)"
    else:
        delta_str = " (first snapshot — delta available tomorrow)"
    body = f"{views_fmt} total views{delta_str}\n{video_count} videos live"
    _send("Narrify Channel Report", body)

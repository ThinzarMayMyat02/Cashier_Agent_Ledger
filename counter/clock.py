"""Myanmar business dates used by postings, closes and legacy migrations."""

from datetime import datetime
from zoneinfo import ZoneInfo


def business_day(timestamp=None):
    return (
        (
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if timestamp
            else datetime.now(ZoneInfo("Asia/Yangon"))
        )
        .astimezone(ZoneInfo("Asia/Yangon"))
        .date()
        .isoformat()
    )

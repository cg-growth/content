"""Local time zone for timestamps, recaps and card labels.
Set MEMESCAN_TZ to an IANA name (e.g. "Asia/Singapore", "America/New_York"); defaults to the machine's local zone.
MEMESCAN_TZ_LABEL overrides the short label printed on cards/messages (default: the zone abbreviation, e.g. "UTC", "+08")."""
import datetime, os
def _tz():
    name = os.environ.get("MEMESCAN_TZ", "").strip()
    if name:
        try:
            from zoneinfo import ZoneInfo
            return ZoneInfo(name)
        except Exception:
            pass
    return datetime.datetime.now().astimezone().tzinfo
LOCAL_TZ = _tz()
TZ_LABEL = os.environ.get("MEMESCAN_TZ_LABEL") or (datetime.datetime.now(LOCAL_TZ).tzname() or "local")

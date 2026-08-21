#!/usr/bin/env python3
"""Check Inter Miami CF upcoming matches from ESPN API.

Converts all times to Vietnam (UTC+7) and prints a readable schedule.
Designed to run as a cron job — output gets delivered via Hermes.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen

TEAM_ID = 20232  # Inter Miami CF
LEAGUE = "usa.1"  # MLS
API_URL = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{LEAGUE}/teams/{TEAM_ID}/schedule"

VN_TZ = timezone(timedelta(hours=7))


def fetch_schedule() -> list[dict]:
    """Fetch full schedule from ESPN API."""
    with urlopen(API_URL, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    return data.get("events", [])


def upcoming_matches(events: list[dict], days_ahead: int = 14) -> list[dict]:
    """Filter for matches in the next N days (including today)."""
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=days_ahead)

    upcoming = []
    for e in events:
        try:
            match_date = datetime.fromisoformat(e["date"].replace("Z", "+00:00"))
        except (ValueError, KeyError):
            continue

        if now <= match_date <= cutoff:
            upcoming.append(e)

    upcoming.sort(key=lambda e: e["date"])
    return upcoming


def format_match(event: dict) -> str:
    """Format a single match as a readable line with Vietnam time."""
    match_date = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
    vn_time = match_date.astimezone(VN_TZ)

    comp = event.get("competitions", [{}])[0]
    opponents = comp.get("competitors", [])
    names = []
    is_home = False
    for o in opponents:
        t = o.get("team", {})
        names.append(t.get("displayName", "?"))
        if o.get("homeAway") == "home":
            is_home = True

    venue = comp.get("venue", {}).get("fullName", "TBD")
    home_tag = "🏠 HOME" if is_home else "✈️ AWAY"

    day_vn = vn_time.strftime("%d/%m")
    day_en = vn_time.strftime("%A")
    time_str = vn_time.strftime("%H:%M")

    return (
        f"📅 **{day_en} {day_vn}** — {time_str} giờ VN\n"
        f"⚽ Inter Miami vs **{' vs '.join(names)}**  {home_tag}\n"
        f"📍 {venue}\n"
    )


def main():
    print("🔍 Đang kiểm tra lịch Inter Miami CF...\n")

    try:
        events = fetch_schedule()
    except Exception as e:
        print(f"❌ Không lấy được lịch từ ESPN: {e}")
        return 1

    upcoming = upcoming_matches(events, days_ahead=14)

    if not upcoming:
        print("📭 Không có trận nào trong 2 tuần tới.")
        print(f"(Tổng {len(events)} trận trong database — có thể lịch chưa cập nhật)")
        print("Nguồn: MLSsoccer.com/schedule")
        return 0

    # Also check if there are ANY events beyond the cutoff —
    # we want to know if the schedule just hasn't been published yet
    all_past = all(
        datetime.fromisoformat(e["date"].replace("Z", "+00:00"))
        < datetime.now(timezone.utc)
        for e in events
    )

    print(f"⚽ **Lịch Inter Miami CF — {len(upcoming)} trận sắp tới**\n")

    for match in upcoming:
        print(format_match(match))

    if all_past and not upcoming:
        print("\n⚠️ Tất cả các trận trong database đều đã qua.")
        print("MLS có thể chưa công bố lịch phần còn lại của mùa giải.")

    print("\n📺 Xem trên: Apple TV")
    print("📊 Nguồn: ESPN API + MLSsoccer.com")

    return 0


if __name__ == "__main__":
    sys.exit(main())

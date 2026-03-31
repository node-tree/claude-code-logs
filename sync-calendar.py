#!/usr/bin/env python3
"""
sync-calendar.py — Google Calendar iCal → calendar.json
claude-code-logs 레포에 저장 후 GitHub push
"""

import json
import urllib.request
import subprocess
import os
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

ICAL_URL = "https://calendar.google.com/calendar/ical/nodetreemedia%40gmail.com/private-db64723d53859ac48d9f6ce14411d286/basic.ics"
OUTPUT = Path(__file__).parent / "calendar.json"
DAYS_BACK  = 180  # 지난 6개월
DAYS_AHEAD = 90   # 앞으로 90일치 이벤트


def parse_dt(val):
    """DTSTART/DTEND 값을 date로 변환"""
    if hasattr(val, 'dt'):
        val = val.dt
    if isinstance(val, datetime):
        if val.tzinfo:
            val = val.astimezone(timezone(timedelta(hours=9)))  # KST
        return val.date()
    return val  # already date


def fetch_events():
    from icalendar import Calendar

    with urllib.request.urlopen(ICAL_URL) as r:
        cal = Calendar.from_ical(r.read())

    today = date.today()
    cutoff = today + timedelta(days=DAYS_AHEAD)

    events = []
    for comp in cal.walk():
        if comp.name != 'VEVENT':
            continue

        summary = str(comp.get('SUMMARY', '')).strip()
        if not summary:
            continue

        start = parse_dt(comp.get('DTSTART'))
        end_raw = comp.get('DTEND') or comp.get('DTSTART')
        end = parse_dt(end_raw)

        # 범위 필터: 7일 전 ~ 90일 이내
        past_limit = today - timedelta(days=DAYS_BACK)
        if start < past_limit or start > cutoff:
            continue

        description = str(comp.get('DESCRIPTION', '')).strip()
        location = str(comp.get('LOCATION', '')).strip()
        status = str(comp.get('STATUS', 'CONFIRMED')).strip()
        uid = str(comp.get('UID', '')).strip()

        events.append({
            "uid": uid[:40],
            "title": summary,
            "start": start.isoformat(),
            "end": (end - timedelta(days=1)).isoformat() if end > start else start.isoformat(),
            "description": description[:200] if description else None,
            "location": location if location else None,
            "status": status,
            "daysUntil": (start - today).days,
            "isPast": start < today,
        })

    # 날짜순 정렬
    events.sort(key=lambda e: e["start"])
    return events


def main():
    print("Fetching Google Calendar...")
    events = fetch_events()
    print(f"  {len(events)}개 이벤트 (앞으로 {DAYS_AHEAD}일)")

    data = {
        "lastUpdated": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%dT%H:%M:%S+09:00"),
        "calendarId": "nodetreemedia@gmail.com",
        "daysAhead": DAYS_AHEAD,
        "events": events,
    }

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  → {OUTPUT} 저장")

    # Git push
    repo = OUTPUT.parent
    subprocess.run(['git', 'add', 'calendar.json'], cwd=repo, check=True)
    result = subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=repo)
    if result.returncode != 0:
        subprocess.run([
            'git', 'commit', '-m',
            f'chore: calendar sync {date.today().isoformat()}'
        ], cwd=repo, check=True)
        subprocess.run(['git', 'push'], cwd=repo, check=True)
        print("  → GitHub push 완료")
    else:
        print("  → 변경 없음, push 생략")


if __name__ == '__main__':
    main()

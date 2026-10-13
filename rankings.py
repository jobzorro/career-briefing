"""
아카이브(archive/*.json) → 주간·월간 랭킹 집계

세 가지를 만든다.
  1) 기사 랭킹   : 기간 내 모든 기사를 점수순으로 줄 세운 차트
  2) 키워드 랭킹 : 기간 내 키워드 등장 횟수 순위 + 직전 같은 기간 대비 순위 변동(▲▼/NEW)
  3) 키워드 추이 : 상위 키워드 몇 개의 날짜별 등장 횟수 (꺾은선 차트용)

순위 변동은 기사에는 의미가 없다(기사는 매일 새로 나오니까). 같은 이름이 기간을 넘어
반복 등장하는 건 키워드뿐이라, 변동 표시는 키워드 차트에만 붙인다.
"""

import json
import re
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent
ARCHIVE_DIR = BASE_DIR / "archive"

# smooth: 추이 차트를 며칠 이동합계로 그릴지. 하루 등장 횟수는 0~6건이라 30일을
#         일별로 그리면 선이 톱니처럼 엉킨다 → 월간은 7일 합계로 흐름만 보여준다.
PERIODS = [
    {"key": "weekly", "label": "주간", "days": 7, "en": "WEEKLY", "top": 20, "smooth": 1},
    {"key": "monthly", "label": "월간", "days": 30, "en": "MONTHLY", "top": 30, "smooth": 7},
]

KEYWORD_TOP = 10
TREND_TOP = 5      # 추이 차트에 그릴 키워드 수 (색 구분이 확실한 5개까지만)


def load_archive():
    """archive/*.json 을 날짜 오름차순으로 읽어들인다"""
    if not ARCHIVE_DIR.exists():
        return []

    days = []
    for path in sorted(ARCHIVE_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if payload.get("date") and payload.get("sections"):
            days.append(payload)
    days.sort(key=lambda d: d["date"])
    return days


def flatten(day):
    """하루치 지면을 (섹션정보가 붙은) 기사 리스트로 펼친다"""
    out = []
    for sec in day.get("sections", []):
        for a in sec.get("articles", []):
            out.append({**a,
                        "section": sec["key"],
                        "section_name": sec["name"],
                        "date": day["date"]})
    return out


def _parse(d):
    return datetime.strptime(d, "%Y-%m-%d").date()


def window(days, end, length):
    """end(포함)로부터 length일 구간에 속한 지면만"""
    start = end - timedelta(days=length - 1)
    return [d for d in days if start <= _parse(d["date"]) <= end]


def rank_articles(days, limit):
    """
    기간 내 기사를 점수순으로 줄 세운다.
    같은 기사가 여러 날 지면에 오른 경우 최고 점수 1건만 남긴다.
    URL은 수집 경로(언론사 RSS / Google News)에 따라 달라질 수 있어 제목으로 판정한다.
    """
    best = {}
    for day in days:
        for a in flatten(day):
            key = re.sub(r"[^가-힣a-zA-Z0-9]", "", a["title"]).lower()
            prev = best.get(key)
            if prev is None or a["score"] > prev["score"]:
                best[key] = a

    ranked = sorted(best.values(), key=lambda a: (a["score"], a["date"]), reverse=True)
    return [{
        "rank": i,
        "title": a["title"],
        "url": a["url"],
        "source": a["source"],
        "date": a["date"],
        "score": a["score"],
        "section": a["section"],
        "section_name": a["section_name"],
        "lead": a.get("lead", ""),
    } for i, a in enumerate(ranked[:limit], 1)]


def count_keywords(days):
    """기간 내 키워드 등장 횟수"""
    counter = Counter()
    for day in days:
        for a in flatten(day):
            counter.update(a.get("keywords", []))
    return counter


def rank_keywords(current_days, previous_days, limit=KEYWORD_TOP):
    """
    키워드 순위 + 직전 같은 길이 기간 대비 변동.
      change  = 오른 칸 수 (양수면 상승, 음수면 하락)
      state   = up | down | same | new
    """
    now = count_keywords(current_days)
    before = count_keywords(previous_days)

    prev_rank = {kw: i for i, (kw, _) in enumerate(before.most_common(), 1)}

    rows = []
    for i, (kw, count) in enumerate(now.most_common(limit), 1):
        old = prev_rank.get(kw)
        if old is None:
            state, change = ("new", 0) if before else ("same", 0)
        elif old > i:
            state, change = "up", old - i
        elif old < i:
            state, change = "down", i - old
        else:
            state, change = "same", 0
        rows.append({"rank": i, "keyword": kw, "count": count,
                     "state": state, "change": change})
    return rows


def keyword_trend(all_days, end, length, keywords, smooth=1):
    """
    keywords 각각의 날짜별 등장 횟수 (smooth > 1 이면 그날까지 smooth일 이동합계).
    지면이 없는 날도 0으로 채워 x축 간격이 실제 날짜 간격과 같게 한다.
    이동합계는 구간 앞쪽 날짜도 온전히 계산되도록 구간 밖 과거 지면(all_days)까지 본다.
    """
    by_date = {d["date"]: Counter(k for a in flatten(d) for k in a.get("keywords", []))
               for d in all_days}

    def count(day, kw):
        return sum(by_date.get((day - timedelta(days=i)).strftime("%Y-%m-%d"), Counter())[kw]
                   for i in range(smooth))

    days = [end - timedelta(days=i) for i in range(length - 1, -1, -1)]
    return {
        "dates": [d.strftime("%Y-%m-%d") for d in days],
        "smooth": smooth,
        "series": [{"keyword": kw, "counts": [count(d, kw) for d in days]}
                   for kw in keywords],
    }


def build(days=None, today=None):
    """
    build_site.py 가 쓰는 최종 구조.
      { "days": [...날짜 목록...], "periods": { weekly: {...}, monthly: {...} } }
    """
    days = days if days is not None else load_archive()
    if not days:
        return {"days": [], "periods": {}}

    today = today or _parse(days[-1]["date"])
    available = len(days)

    periods = {}
    for spec in PERIODS:
        length = spec["days"]
        current = window(days, today, length)
        previous = window(days, today - timedelta(days=length), length)

        if not current:
            continue

        covered = sorted(d["date"] for d in current)
        keywords = rank_keywords(current, previous)
        periods[spec["key"]] = {
            "key": spec["key"],
            "label": spec["label"],
            "en": spec["en"],
            "days": length,
            # 실제로 데이터가 있는 날만 세어 둔다. 7일치를 요구했지만 3일밖에 없다면
            # 지면에 "3일치 집계"라고 정직하게 적기 위해서다.
            "covered_days": len(covered),
            "range": f"{covered[0]} ~ {covered[-1]}",
            "articles": rank_articles(current, spec["top"]),
            "keywords": keywords,
            "trend": keyword_trend(days, today, length,
                                   [k["keyword"] for k in keywords[:TREND_TOP]],
                                   smooth=spec["smooth"]),
            "compared": bool(previous),
        }

    return {
        "days": [{"date": d["date"],
                  "count": sum(len(s.get("articles", [])) for s in d.get("sections", []))}
                 for d in days],
        "available": available,
        "periods": periods,
    }


if __name__ == "__main__":
    import sys
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    result = build()
    print(f"아카이브 {result['available']}일치")
    for key, p in result["periods"].items():
        print(f"\n[{p['label']}] {p['range']}  ({p['covered_days']}일치 집계)")
        for a in p["articles"][:5]:
            print(f"  {a['rank']:2d}. ({a['score']:>2}점) {a['title'][:46]}")
        marks = {"up": "▲", "down": "▼", "new": "NEW", "same": "-"}
        kws = "  ".join(
            f"{k['keyword']}({k['count']}){marks[k['state']]}{k['change'] or ''}"
            for k in p["keywords"][:8])
        print(f"  키워드: {kws}")

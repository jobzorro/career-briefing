"""
기사 분류 & 점수 산정

3개 섹션으로 분류한다.
  1) 거시경제·고용지표  2) 미래커리어·산업변화  3) 기업채용·이직

점수 = (제목 매칭 x2) + (요약문 매칭 x1) + 통계보너스 - 배제감점
가장 높은 점수를 낸 섹션에 배정하고, MIN_SCORE 미만이면 아예 버린다.
"""

import re

SECTIONS = [
    {
        "key": "macro",
        "name": "거시경제·고용지표",
        "en": "MACRO & JOBS",
        "desc": "고용률·실업률·임금 등 노동시장 전반을 움직이는 지표와 정책",
        # core: 이 섹션의 정체성을 결정하는 강한 신호 (가중치 3)
        "core": [
            "고용동향", "고용률", "실업률", "취업률", "실업자", "구직자",
            "고용지표", "고용시장", "노동시장", "일자리", "고용보험",
            "실업급여", "최저임금", "임금인상", "정규직", "비정규직",
            "청년실업", "고용률", "취업자", "경제활동인구", "구인난",
        ],
        # sub: 맥락 보조 신호 (가중치 1)
        "sub": [
            "경제성장", "GDP", "경기", "물가", "금리", "환율", "수출",
            "내수", "소비", "생산성", "인구", "고령화", "저출산",
            "노동개혁", "근로시간", "주52시간", "정년연장", "노사",
            "기획재정부", "고용노동부", "통계청", "한국은행",
        ],
    },
    {
        "key": "future",
        "name": "미래커리어·산업변화",
        "en": "FUTURE OF WORK",
        "desc": "AI·산업 재편이 직무와 커리어 경로를 바꾸는 흐름",
        "core": [
            "AI 일자리", "인공지능 채용", "직무전환", "커리어전환", "전직",
            "리스킬링", "업스킬링", "재교육", "직업훈련", "미래직업",
            "신직업", "유망직종", "자동화", "일자리 대체", "노동 대체",
            "디지털전환", "긱워커", "프리랜서", "원격근무", "재택근무",
            "주4일제", "하이브리드 근무",
            "인재 양성", "인력 양성", "인재양성", "인력양성", "인재 확보",
            "전문인력", "연구인력", "산업인력", "고급인력", "기술인재",
            "인력난", "인재난", "구인구직", "직업교육", "평생교육",
            "계속고용", "중장년", "시니어 일자리", "경력단절",
        ],
        "sub": [
            "AI", "인공지능", "로봇", "빅데이터", "클라우드", "반도체",
            "바이오", "이차전지", "친환경", "ESG", "메타버스", "블록체인",
            "4차산업", "DX", "스타트업", "생성형", "LLM", "챗GPT",
            "플랫폼", "산업구조", "구조조정", "사업재편",
        ],
    },
    {
        "key": "hiring",
        "name": "기업채용·이직",
        "en": "HIRING & MOVES",
        "desc": "기업이 실제로 사람을 뽑고 옮기는 현장 — 공채·경력·처우",
        "core": [
            "공채", "수시채용", "경력채용", "신입채용", "채용공고", "채용설명회",
            "채용연계", "인턴채용", "채용규모", "채용계획", "채용박람회",
            "이직", "헤드헌팅", "인재영입", "인력채용", "경력직",
            "연봉협상", "성과급", "임금협상", "복리후생", "채용 확대",
        ],
        "sub": [
            "채용", "인턴", "신입", "연봉", "처우", "인사", "임원인사",
            "삼성", "현대차", "LG", "SK", "포스코", "한화", "롯데", "CJ",
            "카카오", "네이버", "쿠팡", "토스", "배달의민족", "당근",
            "대기업", "중견기업", "공기업", "유니콘", "인재", "조직문화",
        ],
    },
]

# 커리어/고용과 무관한 기사 배제 (한 번이라도 걸리면 사실상 탈락)
EXCLUDE = [
    "연예", "아이돌", "드라마", "예능", "가수", "배우", "영화제",
    "야구", "축구", "골프", "프로야구", "올림픽", "월드컵",
    "부고", "별세", "입적", "빈소", "결혼", "이혼", "열애",
    "살인", "성범죄", "음주운전", "마약", "폭행", "사기 혐의",
    "날씨", "폭염", "한파", "태풍", "미세먼지", "로또",
    "운세", "복권", "맛집", "레시피",
]

# 홍보성 보도자료 신호 → 강한 감점.
# (지자체 수상 소식, 협약식, 간담회 같은 기사가 '일자리' 키워드로 상위를 점령하는 걸 막는다)
DEMOTE = [
    "수상", "장관상", "대통령상", "표창", "우수기관", "최우수", "특별상",
    "일자리대상", "협약", "MOU", "업무협약", "간담회", "위촉", "발대식",
    "개소식", "출범식", "기념식", "캠페인", "공모전", "선정돼", "선정됐",
]

# 통계 수치가 들어간 제목은 신뢰도가 높다 → 보너스
NUMBER_PATTERN = re.compile(r"\d+[\.,]?\d*\s*(%|명|만|억|조|건|개|위|배|포인트)")

MIN_SCORE = 10         # 이 점수 미만이면 수집 대상에서 제외
TITLE_WEIGHT = 2       # 제목 매칭 가중
BODY_WEIGHT = 1        # 요약문 매칭 가중
DEMOTE_PENALTY = 8     # DEMOTE 키워드 1건당 감점
NUMBER_BONUS = 3


def _count(text, keywords):
    """텍스트에 등장한 키워드 목록과 매칭 횟수를 돌려준다"""
    hits = []
    for kw in keywords:
        if kw.lower() in text:
            hits.append(kw)
    return hits


def classify(title, body="", source_bonus=0):
    """
    기사 제목/요약을 보고 (섹션key, 점수, 매칭키워드) 를 판정한다.
    어느 섹션에도 못 미치면 section=None.

    source_bonus: 주요 언론사 가산점 (수집기에서 넘겨준다)
    """
    t = title.lower()
    b = (body or "").lower()[:600]   # 요약문은 앞부분만 (RSS 설명문 꼬리 노이즈 차단)

    # 배제 키워드는 제목에서만 검사 (본문엔 우연히 섞이는 경우가 많다)
    for kw in EXCLUDE:
        if kw in title:
            return None, 0, []

    best = (None, 0, [], False)
    for sec in SECTIONS:
        score = 0
        matched = []
        has_core = False

        for kw in _count(t, sec["core"]):
            score += 3 * TITLE_WEIGHT
            matched.append(kw)
            has_core = True
        for kw in _count(b, sec["core"]):
            score += 3 * BODY_WEIGHT
            has_core = True
        for kw in _count(t, sec["sub"]):
            score += 1 * TITLE_WEIGHT
            matched.append(kw)
        for kw in _count(b, sec["sub"]):
            score += 1 * BODY_WEIGHT

        if score > best[1]:
            # 중복 제거하면서 순서 유지
            best = (sec["key"], score, list(dict.fromkeys(matched))[:4], has_core)

    key, score, matched, has_core = best
    if not key:
        return None, 0, []

    # core 키워드가 하나도 없으면 탈락.
    # (회사 이름만 스쳐 지나간 기사 — 예: "삼성길 생길까" — 를 걸러낸다)
    if not has_core:
        return None, score, matched

    if NUMBER_PATTERN.search(title):
        score += NUMBER_BONUS
    for kw in DEMOTE:
        if kw in title:
            score -= DEMOTE_PENALTY
    score += source_bonus

    if score < MIN_SCORE:
        return None, score, matched
    return key, score, matched


def section_by_key(key):
    for s in SECTIONS:
        if s["key"] == key:
            return s
    return None

"""
뉴스 소스 정의
- DIRECT_FEEDS: 언론사 RSS. 기사 원본 URL이 그대로 들어있어 썸네일/본문 요약 추출이 가능하다.
- GOOGLE_QUERIES: Google News RSS 검색. 취업/채용 키워드 커버리지를 보강한다.
  (링크가 news.google.com 리다이렉터라, 지면에 오르는 기사만 gnews.py로 원문 URL을 복원해
   요약·썸네일을 뽑는다. 복원에 실패하면 RSS 설명문을 쓴다)
"""

from urllib.parse import quote

# 2026-08 기준 동작 확인된 피드만 등록 (죽은 피드는 주석으로 남김)
DIRECT_FEEDS = [
    {"name": "연합뉴스",   "url": "https://www.yna.co.kr/rss/economy.xml"},
    {"name": "연합뉴스",   "url": "https://www.yna.co.kr/rss/industry.xml"},
    {"name": "매일경제",   "url": "https://www.mk.co.kr/rss/30100041/"},
    {"name": "매일경제",   "url": "https://www.mk.co.kr/rss/50100032/"},
    {"name": "매일경제",   "url": "https://www.mk.co.kr/rss/50200011/"},
    {"name": "전자신문",   "url": "https://rss.etnews.com/Section901.xml"},
    {"name": "전자신문",   "url": "https://rss.etnews.com/Section902.xml"},
    {"name": "전자신문",   "url": "https://rss.etnews.com/Section903.xml"},
    {"name": "한겨레",     "url": "https://www.hani.co.kr/rss/economy/"},
    {"name": "경향신문",   "url": "https://www.khan.co.kr/rss/rssdata/economy_news.xml"},
    {"name": "서울신문",   "url": "https://www.seoul.co.kr/xml/rss/rss_economy.xml"},
    {"name": "머니투데이", "url": "https://rss.mt.co.kr/mt_news.xml"},
    {"name": "테크M",      "url": "https://www.techm.kr/rss/allArticle.xml"},
    {"name": "아웃스탠딩", "url": "https://outstanding.kr/feed"},
    # DEAD(2026-08): 뉴스앤잡, 한국경제, 이데일리, 디지털타임스, ZDNet, 블로터, IT조선, 잡코리아
]

# 섹션별로 부족한 기사를 Google News 검색으로 보강 (v2: 조로의 5개 섹션 기준)
GOOGLE_QUERIES = [
    # 채용 시즌·공고
    "대기업 공채 OR 수시채용 OR 신입 채용",
    "공채 일정 OR 서류 접수 OR 채용설명회",
    "중견기업 채용 OR 외국계 채용 OR 공기업 채용",
    "경력직 채용 OR 인턴 채용 OR 채용 확대",
    # 이직·연봉·HR
    "이직 OR 헤드헌팅 OR 인재 영입 경쟁",
    "연봉 인상 OR 성과급 OR 임금협상 타결",
    "희망퇴직 OR 구조조정 OR 권고사직",
    "AI 면접 OR 채용 프로세스 OR 자기소개서 AI",
    # 기업·산업 레이더
    "영업이익 OR 적자 전환 OR 사업 철수",
    "공장 신설 OR 증설 OR 인수합병 대기업",
    # 고용지표·정책
    "고용동향 OR 실업률 OR 청년 고용",
    "최저임금 OR 실업급여 OR 노동법 개정",
    # 커리어의 변화
    "AI 일자리 대체 OR 사무직 자동화 OR 직무 변화",
    "40대 희망퇴직 OR 중장년 재취업 OR 중장년 이직",
    "부업 OR N잡 OR 사이드잡 OR 멀티커리어",
    "개발자 채용 시장 OR 판교 OR IT 인력",
]

GOOGLE_RSS = "https://news.google.com/rss/search?q={}&hl=ko&gl=KR&ceid=KR:ko"


def google_feeds():
    """Google News 검색 쿼리를 RSS 피드 목록으로 변환"""
    return [
        {"name": "Google News", "url": GOOGLE_RSS.format(quote(q)), "query": q}
        for q in GOOGLE_QUERIES
    ]


def all_feeds():
    return DIRECT_FEEDS + google_feeds()


# 신뢰도 가산점을 줄 주요 언론사.
# Google News가 물어오는 지역지/해외 교민지 기사가 상위를 차지하는 걸 막는다.
TIER1_SOURCES = {
    "연합뉴스", "연합뉴스TV", "매일경제", "한국경제", "전자신문", "한겨레",
    "경향신문", "서울신문", "머니투데이", "이데일리", "조선일보", "중앙일보",
    "동아일보", "국민일보", "세계일보", "한국일보", "뉴스1", "뉴시스",
    "아시아경제", "파이낸셜뉴스", "헤럴드경제", "디지털타임스", "ZDNet Korea",
    "블로터", "테크M", "아웃스탠딩", "IT조선", "더벨", "비즈니스포스트",
    "KBS", "MBC", "SBS", "YTN", "JTBC", "channelA", "MBN",
}

SOURCE_BONUS = 8      # TIER1 언론사 가산점
UNKNOWN_PENALTY = -5  # 그 외(지역지·해외 교민지 등) 감점


def source_bonus(source_name):
    """
    언론사 신뢰도 가산점. 부분일치를 허용해 '매일경제 =' 같은 변형도 잡는다.
    TIER1이 아니면 감점을 줘서, 키워드만 빽빽한 지역 보도자료가
    주요 언론사 기사를 밀어내지 못하게 한다.
    """
    for s in TIER1_SOURCES:
        if s in source_name:
            return SOURCE_BONUS
    return UNKNOWN_PENALTY

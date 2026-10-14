"""
제안 점수 기준 프로토타입 — 지난 아카이브(이미 지면에 올랐던 기사)에 사후 적용해
무엇이 밀려나고 무엇이 올라오는지 본다. (원시 수집 풀이 아니라 '발행된' 기사만 대상)
"""
import json, glob, re, sys, collections
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\hb038\Desktop\claude-code-study\news-collector")
from sources import source_bonus

# ---------- 제안 섹션 ----------
SECTIONS = [
    {"key": "hiring", "name": "채용 시즌·공고",
     "core": ["공채", "수시채용", "신입채용", "신입 채용", "경력채용", "경력직 채용", "채용공고", "채용 공고",
              "채용연계", "인턴 채용", "인턴채용", "채용 일정", "서류 접수", "서류접수", "채용 시작", "채용 돌입",
              "채용규모", "채용 규모", "채용계획", "채용 계획", "채용 확대", "신입사원", "하반기 채용", "상반기 채용",
              "대졸 신입", "공개채용", "채용설명회"],
     "sub": ["채용", "인턴", "신입", "대기업", "계열사", "중견기업", "외국계", "공기업", "공공기관", "은행", "카드사",
             "삼성", "현대차", "LG", "SK", "포스코", "한화", "롯데", "CJ", "신세계", "GS", "두산", "효성", "LS", "HD현대",
             "카카오", "네이버", "쿠팡", "토스", "농협", "KT", "LIG", "현대백화점", "이마트", "아모레", "코오롱"]},
    {"key": "moves", "name": "이직·연봉·HR",
     "core": ["이직", "경력직", "헤드헌팅", "인재영입", "연봉", "연봉협상", "성과급", "임금협상", "임금인상", "임금 인상",
              "희망퇴직", "구조조정", "권고사직", "명예퇴직", "감원", "정리해고", "해고", "퇴직금", "퇴사",
              "승진", "인사평가", "조직개편", "조직 개편", "주4일", "주 4일", "재택근무", "하이브리드 근무", "유연근무",
              "복리후생", "복지", "AI 면접", "면접", "자기소개서", "자소서", "경력기술서", "채용 프로세스", "채용 과정",
              "채용 트렌드", "HR", "인사팀", "워라밸", "직장인"],
     "sub": ["경력", "인사", "노조", "노사", "임단협", "임협", "근로시간", "주52시간", "정년", "정년연장", "평가", "보상",
             "스톡옵션", "RSU", "인센티브", "조직문화", "MZ", "직장", "회사", "잡코리아", "사람인", "인크루트", "원티드", "리멤버"]},
    {"key": "company", "name": "기업·산업 레이더",
     "core": ["영업이익", "영업손실", "적자", "흑자", "실적", "매출", "사업재편", "사업 재편", "사업 철수", "매각", "인수",
              "합병", "M&A", "공장 신설", "공장 설립", "투자 계획", "증설", "신사업", "상장", "IPO", "기업분할", "분사",
              "자회사 설립", "지주사", "사업부", "점포 폐점", "폐점", "법정관리", "회생", "워크아웃", "유동성"],
     "sub": ["반도체", "이차전지", "2차전지", "배터리", "유통", "백화점", "편의점", "식품", "F&B", "프랜차이즈", "부동산", "건설",
             "신탁", "금융", "은행", "카드", "증권", "보험", "제약", "바이오", "의료기기", "IT서비스", "SI", "클라우드", "자동차",
             "조선", "방산", "화학", "철강", "화장품", "패션", "게임", "플랫폼", "대기업", "중견기업", "외국계", "그룹",
             "삼성", "현대차", "LG", "SK", "포스코", "한화", "롯데", "CJ", "신세계", "카카오", "네이버", "쿠팡"]},
    {"key": "macro", "name": "고용지표·정책",
     "core": ["고용동향", "고용률", "실업률", "취업자", "실업자", "청년실업", "청년 고용", "청년고용", "경제활동인구",
              "고용지표", "노동시장", "고용시장", "쉬었음", "청년 일자리", "청년일자리", "고용 착시", "일자리 창출", "구직단념", "최저임금", "실업급여", "고용보험", "고용노동부",
              "통계청", "노동법", "노란봉투법", "근로기준법", "정년연장", "계속고용", "주52시간", "근로시간"],
     "sub": ["일자리", "고용", "정규직", "비정규직", "임금", "경기", "금리", "물가", "GDP", "경제성장", "저출산", "인구",
             "기획재정부", "한국은행", "정부", "국회", "대책", "정책", "청년"]},
    {"key": "future", "name": "AI·미래커리어",
     "core": ["AI 일자리", "AI가 대체", "일자리 대체", "자동화", "직무 변화", "직무전환", "커리어 전환", "리스킬링", "업스킬링",
              "AI 에이전트", "생성형 AI", "AI 도입", "AI 활용", "개발자 채용", "개발자 시장", "사무직", "화이트칼라",
              "N잡", "부업", "사이드잡", "투잡", "프리랜서", "긱워커", "멀티커리어", "1인 기업", "미래 직업", "미래직업",
              "유망 직무", "유망직종", "신직업"],
     "sub": ["AI", "인공지능", "LLM", "챗GPT", "GPT", "로봇", "디지털전환", "DX", "빅테크", "개발자", "데이터", "판교",
             "스타트업", "플랫폼", "원격", "노코드"]},
]

EXCLUDE = ["연예", "아이돌", "드라마", "예능", "가수", "배우", "영화제", "야구", "축구", "골프", "프로야구", "올림픽", "월드컵",
           "부고", "별세", "빈소", "결혼", "이혼", "열애", "살인", "성범죄", "음주운전", "마약", "폭행", "날씨", "폭염", "한파",
           "태풍", "미세먼지", "로또", "운세", "복권", "맛집", "레시피"]

# 홍보성·행사성 (기존 DEMOTE 유지 + 박람회 추가)
DEMOTE = ["수상", "장관상", "대통령상", "표창", "우수기관", "최우수", "특별상", "일자리대상", "협약", "MOU", "업무협약",
          "간담회", "위촉", "발대식", "개소식", "출범식", "기념식", "캠페인", "공모전", "선정돼", "선정됐", "맞손",
          "박람회", "페스티벌", "명예", "학위", "성료", "개원", "개관", "개최", "홍보의 날", "센터 가동"]

# --- 조로 관심축 (제안의 핵심) ---
JOB_BONUS = ["기획", "전략", "재무", "회계", "자금", "인사", "HR", "총무", "구매", "SCM", "영업", "마케팅", "MD",
             "서비스기획", "PM", "PO", "사무직", "문과", "인문계", "경영지원"]        # +4 (제목)
FIRM_BONUS = ["대기업", "계열사", "중견기업", "중견", "외국계", "공기업", "공공기관", "그룹"]   # +3
READER_BONUS = ["신입", "중고신입", "경력직", "취준생", "구직자", "20대", "30대", "청년", "직장인", "이직"]  # +3
OFF_TARGET = ["중장년", "시니어", "5070", "노인", "60세", "고령자", "장애인", "경력단절", "경단녀", "청소년", "특성화고",
              "전역군인", "외국인 근로자", "이주노동자", "농촌", "어촌", "귀농"]      # -6
LOCAL_PR = re.compile(r"(?:^|[\[\s(])[가-힣]{1,4}(?:시|군|구|도)(?:청|소식|\]|,|\s)|지자체|도의회|시의회|군수|구청장|시장은|[가-힣]{2,6}대(?:학교|학)?(?:,|·|\s)[^,]{0,20}(?:센터|양성|취업률|개원|산학)")  # -8
FOREIGN_STAT = re.compile(r"(?:美|日|中|英|獨|유럽|미국|일본|중국|호주|독일|프랑스|스리랑카|대만|인도)\s*(?:실업률|고용률|일자리|노동시장|취업률)")  # -6
PR_TRAINING = re.compile(r"(?:인재|인력|전문인력)\s*양성")   # 양성 보도자료: 대학/지자체와 함께면 -8
NUMBER = re.compile(r"\d+[\.,]?\d*\s*(%|명|만|억|조|건|개|위|배|포인트)")
MIN_SCORE = 12


def count(text, kws):
    return [k for k in kws if k.lower() in text]


def classify(title, body="", src=0):
    t, b = title.lower(), (body or "").lower()[:600]
    if any(k in title for k in EXCLUDE):
        return None, 0, [], {}
    best = (None, 0, [], False)
    for s in SECTIONS:
        sc, m, core = 0, [], False
        for k in count(t, s["core"]): sc += 6; m.append(k); core = True
        for k in count(b, s["core"]): sc += 3; core = True
        for k in count(t, s["sub"]): sc += 2; m.append(k)
        for k in count(b, s["sub"]): sc += 1
        if sc > best[1]: best = (s["key"], sc, list(dict.fromkeys(m))[:4], core)
    key, sc, m, core = best
    if not key or not core:
        return None, sc, m, {}
    adj = {}
    if NUMBER.search(title): adj["숫자"] = 3
    if count(t, JOB_BONUS): adj["직무"] = 4
    if count(t, FIRM_BONUS): adj["회사유형"] = 3
    if count(t, READER_BONUS): adj["독자"] = 3
    if count(title, OFF_TARGET): adj["비타깃"] = -6
    if LOCAL_PR.search(title): adj["지자체"] = -8
    if FOREIGN_STAT.search(title): adj["해외지표"] = -6
    if PR_TRAINING.search(title) and re.search(r"대학|대학교|군|시|도|연구원|협약", title): adj["양성홍보"] = -8
    d = sum(1 for k in DEMOTE if k in title)
    if d: adj["행사홍보"] = -8 * d
    adj["언론사"] = src
    sc += sum(adj.values())
    if sc < MIN_SCORE:
        return None, sc, m, adj
    return key, sc, m, adj


if __name__ == "__main__":
    days = [json.load(open(f, encoding="utf-8")) for f in sorted(glob.glob(r"C:\Users\hb038\Desktop\claude-code-study\news-collector\archive\*.json"))]
    rows = []
    for d in days:
        for s in d["sections"]:
            for a in s["articles"]:
                key, sc, m, adj = classify(a["title"], a.get("summary") or a.get("lead") or "", source_bonus(a["source"]))
                rows.append({"date": d["date"], "old": s["key"], "old_score": a.get("score", 0), "title": a["title"],
                             "src": a["source"], "new": key, "new_score": sc, "adj": adj})
    n = len(rows)
    dropped = [r for r in rows if r["new"] is None]
    print(f"발행 기사 {n}건 중 새 기준에서 탈락 {len(dropped)}건 ({len(dropped)/n:.0%})")
    print("새 섹션 분포:", collections.Counter(r["new"] for r in rows if r["new"]))
    print("기존→새 이동:", collections.Counter((r["old"], r["new"]) for r in rows).most_common(12))
    why = collections.Counter()
    for r in dropped:
        for k, v in r["adj"].items():
            if v < 0: why[k] += 1
    print("탈락 사유(중복 집계):", why.most_common())
    print("\n--- 탈락 예시 (기존 점수 높은 순)")
    for r in sorted(dropped, key=lambda r: -r["old_score"])[:16]:
        neg = {k: v for k, v in r["adj"].items() if v < 0}
        print(f"  ({r['old_score']}→{r['new_score']}) {r['title'][:60]}  {neg}")
    print("\n--- 상승 예시 (가산 큰 순)")
    gain = [r for r in rows if r["new"] and r["new_score"] - r["old_score"] >= 8]
    for r in sorted(gain, key=lambda r: -(r["new_score"] - r["old_score"]))[:16]:
        pos = {k: v for k, v in r["adj"].items() if v > 0 and k != "언론사"}
        print(f"  ({r['old_score']}→{r['new_score']}) [{r['new']}] {r['title'][:60]}  {pos}")
    json.dump(rows, open("sim_rows.json", "w", encoding="utf-8"), ensure_ascii=False)

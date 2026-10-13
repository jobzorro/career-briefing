# 커리어 브리핑 (news-collector)

매일 아침 고용·커리어 뉴스를 자동 수집해서, ibrief.kr 스타일의 웹 지면으로 만들어 주는 도구입니다.
GitHub Actions가 매일 08:00(KST)에 수집부터 배포까지 하고, 결과는 GitHub Pages에 올라갑니다.

## 흐름

```
RSS 26개  ──►  collect_news.py  ──►  news_data.json      ──►  build_site.py  ──►  site/index.html
(언론사 14 +    · 중복 제거·분류·점수    +  archive/*.json     (일간 지면 +          │
 Google News 12) · 같은 사건 묶기         (날짜별 보관)    ▲    주간·월간 랭킹 +       ▼
                 · 원문 요약·썸네일                       │    키워드 추이 + 검색)   GitHub Pages
                 · AI 브리핑 (Claude)       rankings.py ───┘
```

하루에 원본 1,900건쯤 읽어서 → 중복을 걷어내고 → 커리어 관련 기사만 남긴 뒤 → 같은 사건은 하나로 묶고 → 섹션별 상위 6건을 지면에 올립니다.

## 3개 섹션

| 섹션 | 무엇을 담나 |
|---|---|
| **거시경제·고용지표** | 고용률·실업률·임금 등 노동시장 전반을 움직이는 지표와 정책 |
| **미래커리어·산업변화** | AI·산업 재편이 직무와 커리어 경로를 바꾸는 흐름 |
| **기업채용·이직** | 기업이 실제로 사람을 뽑고 옮기는 현장 — 공채·경력·처우 |

## 보는 방식 4가지

| 탭 | 내용 |
|---|---|
| **일간** | 날짜별 지면. 상단에 AI가 쓴 "오늘의 브리핑 3줄", 기사마다 한 줄 요약 + 커리어 시사점 |
| **주간** | 최근 7일 점수 랭킹 TOP 20 + 이슈 키워드 순위 + 키워드 일별 추이 차트 |
| **월간** | 최근 30일 TOP 30 + 키워드 순위 + 키워드 추이(7일 이동합계) |
| **검색** | 아카이브 전체에서 제목·요약·키워드 검색. 기사 태그나 키워드 순위를 눌러도 검색됨. 주소가 `#q=검색어` 라 그대로 공유 가능 |

오른쪽 위 **테마** 버튼으로 자동/라이트/다크를 바꿀 수 있습니다.

## 웹 배포 (GitHub Actions + Pages)

`.github/workflows/daily.yml` 이 매일 하는 일:

1. `collect_news.py` — 수집 + AI 브리핑
2. `build_site.py` — `site/index.html` 생성
3. `archive/` 를 저장소에 커밋 (랭킹·검색의 원천이라 계속 쌓여야 함)
4. `site/` 를 GitHub Pages에 배포

**처음 한 번 설정**

| 위치 | 할 일 |
|---|---|
| Settings › Pages | Source를 **GitHub Actions** 로 |
| Settings › Secrets and variables › Actions | `ANTHROPIC_API_KEY` 추가 (없으면 AI 문장 없이 지면만 만들어짐) |
| (선택) 같은 곳 | `NOTION_TOKEN`, `NOTION_PAGE_ID` |
| Actions 탭 | `daily-briefing` › **Run workflow** 로 첫 실행 |

**실패하면** 그날은 배포하지 않고(어제 지면이 그대로 남음) 저장소에 "브리핑 생성 실패" 이슈가 열립니다. GitHub도 예약 실행 실패를 메일로 알려 줍니다.

**로컬 PC와의 관계**: 배포 후에는 GitHub이 원본입니다. 로컬에서 코드를 고치기 전에 `git pull` 로 매일 쌓인 archive를 받아오세요.
로컬 작업 스케줄러(`CareerNewsCollector`)는 GitHub 자동 실행이 확인되면 끄는 게 좋습니다 (둘 다 돌면 archive가 엇갈림).

```
schtasks /delete /tn "CareerNewsCollector" /f
```

## 로컬 실행

```bash
pip install -r requirements.txt

python collect_news.py            # 수집 → news_data.json + archive/오늘.json  (3분 내외)
python build_site.py              # → site/index.html
```

옵션:

```bash
python collect_news.py --top 10        # 섹션당 10건 (기본 6)
python collect_news.py --no-ai         # AI 브리핑 생략 (API 비용 없이 테스트할 때)
python collect_news.py --notion        # Notion 데이터베이스에도 저장
python collect_news.py --no-backfill   # 과거 지면 소급 생성 건너뛰기

python rankings.py                     # 주간·월간 집계 결과를 콘솔에서 확인
```

`.env` 에 `ANTHROPIC_API_KEY` 가 있으면 AI 브리핑이, `NOTION_TOKEN` / `NOTION_PAGE_ID` 가 있으면 `--notion` 이 동작합니다.
수집 결과가 0건이면 종료 코드 2로 끝나서 `run_daily.bat`·GitHub Actions 모두 실패로 감지합니다.

## 파일

| 파일 | 역할 |
|---|---|
| `sources.py` | RSS 피드 목록, Google News 검색 쿼리, 언론사 신뢰도 가산점 |
| `classifier.py` | 섹션 정의(키워드), 점수 산정, 배제/감점 규칙 |
| `collect_news.py` | 수집 → 중복 제거 → 분류 → 같은 사건 묶기 → 본문 요약/썸네일 → AI 브리핑 → 저장 |
| `gnews.py` | Google News 리다이렉트 링크를 언론사 원문 URL로 복원 |
| `ai_brief.py` | Claude(`claude-opus-5-5`)로 기사별 한 줄 요약·시사점 + 오늘의 브리핑 3줄 (하루 1회 호출) |
| `rankings.py` | `archive/*.json` → 주간·월간 기사 랭킹, 키워드 순위/변동, 키워드 추이 |
| `build_site.py` | `news_data.json` + 아카이브 → `site/index.html` (단일 파일) |
| `archive/` | 날짜별 지면 보관소 (썸네일 없이 하루 15KB 안팎). 지우면 과거 지면·랭킹·검색이 사라짐 |
| `.github/workflows/daily.yml` | 매일 자동 수집 + Pages 배포 |
| `run_daily.bat` / `setup_scheduler.bat` | (로컬용) 수집 + 사이트 생성 / 작업 스케줄러 등록 |

## 손보고 싶을 때

- **기사가 너무 적다/많다** → `classifier.py` 의 `MIN_SCORE` (낮추면 많아짐)
- **주간/월간 기간을 바꾸고 싶다** → `rankings.py` 의 `PERIODS` (`days`, `top`, `smooth`)
- **키워드 순위·추이 개수** → `rankings.py` 의 `KEYWORD_TOP`, `TREND_TOP`
- **특정 주제가 안 잡힌다** → 해당 섹션의 `core` 키워드에 추가 (`core`는 가중치 3, `sub`는 1)
- **홍보성 기사가 올라온다** → `classifier.py` 의 `DEMOTE` 에 키워드 추가
- **엉뚱한 기사가 섞인다** → `EXCLUDE` 에 추가하면 제목에 걸리는 즉시 탈락
- **소스를 늘리고 싶다** → `sources.py` 의 `DIRECT_FEEDS` 또는 `GOOGLE_QUERIES`
- **다른 사건이 묶인다 / 같은 사건이 안 묶인다** → `collect_news.py` 의 `WORD_THRESHOLD`, `SAME_SUBJECT_WORD_THRESHOLD`
- **AI 문장 말투를 바꾸고 싶다** → `ai_brief.py` 의 `SYSTEM`

## 알아둘 점

- **AI 문장은 제목·요약만 보고 씁니다.** 원문 전체를 읽지 않으므로, 지면에서 `AI` 표시로 구분하고 원문 요약도 함께 보여 줍니다. 비용은 하루 한 번 호출이라 월 몇 달러 수준입니다.
- **Google News 원문 복원은 구글 내부 형식에 기대고 있습니다.** 구글이 형식을 바꾸면 복원이 실패하고, 그때는 예전처럼 RSS 설명문 + 썸네일 없음으로 자동 대체됩니다.
- **RSS 피드는 수시로 죽습니다.** 기사를 하나도 못 가져온 피드는 지면 맨 아래 "수집 점검 필요"에 표시됩니다. 2026-08 기준 뉴스앤잡·한국경제·이데일리·ZDNet·블로터·IT조선·잡코리아 피드는 응답이 없어 제외했습니다.
- **GitHub 서버는 해외에 있습니다.** 일부 국내 언론사가 해외 접속을 막으면 그 언론사의 요약·썸네일만 빠질 수 있습니다.
- **과거 지면은 썸네일 없이 텍스트로만** 보여줍니다. 오늘 지면에만 썸네일을 싣습니다.
- **공개 페이지입니다.** 무료 GitHub Pages는 누구나 볼 수 있습니다. 기사 제목·짧은 요약·썸네일을 원문 링크와 함께 싣는 형태이며, 원문 저작권은 각 언론사에 있습니다.

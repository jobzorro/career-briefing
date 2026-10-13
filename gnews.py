"""
Google News 리다이렉트 링크 -> 언론사 원문 URL 복원

Google News RSS의 링크(news.google.com/rss/articles/CBMi...)는 그대로 열면
구글 페이지가 나올 뿐 원문으로 바로 가지 않는다. 그래서 그동안은 본문 요약·썸네일을
뽑을 수 없었다.

복원 순서 (구글 웹페이지가 내부적으로 하는 것과 같다)
  1) 기사 ID로 구글 페이지를 열어 서명(data-n-a-sg)과 타임스탬프(data-n-a-ts)를 얻고
  2) 그 둘을 batchexecute 엔드포인트에 보내면 원문 URL을 돌려준다

구글이 내부 형식을 바꾸면 깨질 수 있으므로, 실패하면 조용히 None을 돌려주고
수집기는 예전처럼 RSS 설명문으로 대체한다.
"""

import json
import re
from urllib.parse import urlparse

BATCH_URL = "https://news.google.com/_/DotsSplashUi/data/batchexecute"


def is_google_link(url):
    return "news.google.com" in (url or "")


def decode(url, client):
    """Google News 링크를 원문 URL로. 실패하면 None."""
    try:
        article_id = urlparse(url).path.rstrip("/").split("/")[-1]

        # 1) 서명·타임스탬프 얻기
        page = client.get(f"https://news.google.com/rss/articles/{article_id}").text
        sig = re.search(r'data-n-a-sg="([^"]+)"', page)
        ts = re.search(r'data-n-a-ts="([^"]+)"', page)
        if not (sig and ts):
            return None

        # 2) batchexecute 호출 (요청 본문 모양은 구글 웹 클라이언트를 그대로 따른다)
        inner = (
            '["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,'
            'null,null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],'
            f'"{article_id}",{ts.group(1)},"{sig.group(1)}"]'
        )
        resp = client.post(
            BATCH_URL,
            data={"f.req": json.dumps([[["Fbv4je", inner, None, "generic"]]])},
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
        )
        # 응답은 ")]}'" 접두어 + 빈 줄 + JSON 배열
        body = resp.text.split("\n\n", 1)[1]
        decoded = json.loads(json.loads(body)[0][2])[1]
        return decoded if decoded.startswith("http") else None
    except Exception:
        return None

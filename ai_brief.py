"""
AI 브리핑: 그날 지면에 오른 기사들을 Claude에게 한 번에 보내서
  - 기사마다  "한 줄 요약" + "커리어 관점에서 왜 중요한가"
  - 지면 전체  "오늘의 브리핑 3줄"
을 받아 payload에 붙인다.

하루 1회, 기사 18건 내외를 한 번의 API 호출로 처리한다.
ANTHROPIC_API_KEY 가 없거나 호출이 실패하면 아무것도 붙이지 않고 넘어간다
(지면은 AI 문장 없이도 정상적으로 만들어진다).
"""

import os

from pydantic import BaseModel

MODEL = "claude-opus-5-5"

SYSTEM = """당신은 한국 직장인과 취업준비생을 위한 커리어 뉴스 브리핑 편집자입니다.
기사 제목과 요약만 주어집니다. 주어진 내용에 없는 사실(수치, 기업명, 날짜)을 지어내지 마세요.

작성 규칙
- one_line: 기사의 핵심을 40자 안팎 한 문장으로. 제목을 그대로 반복하지 말고 사실을 압축합니다.
- why: 독자의 커리어(구직·이직·직무·연봉)에 어떤 의미인지 60자 안팎 한 문장으로.
  기사 내용만으로 판단하기 어려우면 과장하지 말고 담담하게 씁니다.
- briefing: 오늘 지면 전체를 관통하는 흐름 3문장. 각 문장은 서로 다른 이야기를 다룹니다.
- 모든 문장은 "~다" 로 끝나는 평서문, 이모지와 느낌표는 쓰지 않습니다."""


class ArticleNote(BaseModel):
    id: str
    one_line: str
    why: str


class DailyBrief(BaseModel):
    briefing: list[str]
    articles: list[ArticleNote]


def _format_articles(payload):
    """기사마다 'S1-3' 같은 ID를 붙여 프롬프트용 텍스트로 만든다"""
    lines = []
    for si, sec in enumerate(payload["sections"], 1):
        for a in sec["articles"]:
            body = f"{a.get('lead', '')} {a.get('summary', '')}".strip()[:400]
            lines.append(f"[S{si}-{a['rank']}] ({sec['name']}) {a['title']}\n  {body}")
    return "\n\n".join(lines)


def annotate(payload):
    """payload에 AI 브리핑을 붙인다. 성공하면 True."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("  ANTHROPIC_API_KEY 없음 -> AI 브리핑 건너뜀")
        return False

    import anthropic

    client = anthropic.Anthropic()
    try:
        response = client.messages.parse(
            model=MODEL,
            max_tokens=16000,
            output_config={"effort": "medium"},
            system=SYSTEM,
            messages=[{
                "role": "user",
                "content": f"{payload['date']} 지면 기사입니다. 각 기사 ID를 그대로 써서 답하세요.\n\n"
                           + _format_articles(payload),
            }],
            output_format=DailyBrief,
        )
    except anthropic.AuthenticationError:
        print("  AI 브리핑 실패: API 키가 올바르지 않습니다")
        return False
    except anthropic.APIStatusError as e:
        print(f"  AI 브리핑 실패: HTTP {e.status_code} {e.message}")
        return False
    except anthropic.APIConnectionError:
        print("  AI 브리핑 실패: 네트워크 오류")
        return False

    if response.stop_reason == "refusal" or response.parsed_output is None:
        print(f"  AI 브리핑 건너뜀 (stop_reason={response.stop_reason})")
        return False

    brief = response.parsed_output
    notes = {n.id: n for n in brief.articles}
    for si, sec in enumerate(payload["sections"], 1):
        for a in sec["articles"]:
            n = notes.get(f"S{si}-{a['rank']}")
            if n:
                a["ai_line"] = n.one_line.strip()
                a["ai_why"] = n.why.strip()

    payload["briefing"] = [s.strip() for s in brief.briefing if s.strip()][:3]
    usage = response.usage
    print(f"  AI 브리핑 완료: 기사 {len(notes)}건 "
          f"(입력 {usage.input_tokens:,} / 출력 {usage.output_tokens:,} 토큰)")
    return True

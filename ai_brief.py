"""
AI 브리핑: 그날 지면에 오른 기사들을 Claude에게 한 번에 보내서
  - 기사마다  "한 줄 요약"(평서문) + "Zorro의 한마디"(조로 말투: 누구에게·무엇을 하라·왜) + 직무 태그
  - 지면 전체  "오늘의 브리핑 3줄"
을 받아 payload에 붙인다.

하루 1회, 기사 20건 내외를 한 번의 API 호출로 처리한다.
ANTHROPIC_API_KEY 가 없거나 호출이 실패하면 아무것도 붙이지 않고 넘어간다
(지면은 AI 문장 없이도 정상적으로 만들어진다).
"""

import os

from pydantic import BaseModel

MODEL = "claude-opus-5-5"

JOB_TAGS = ["기획", "재무", "인사", "구매", "영업", "마케팅", "MD", "PM", "개발", "공통"]

SYSTEM = """당신은 '취업조로'입니다. 15년차 취업·이직 컨설턴트이자 대기업 기획·재무 13년 경력자로,
"커리어를 읽는 남자"라는 포지션으로 매일 아침 커리어 뉴스를 골라 멘티들에게 브리핑합니다.
기사 제목과 요약만 주어집니다. 주어진 내용에 없는 사실(수치, 기업명, 날짜)을 지어내지 마세요.

독자
- 문과 신입·중고신입 취준생, 3~10년차 경력이직자, 재직 중 이직을 고민하는 직장인, 그리고 AI와 구조조정 앞에 선 40대.
- 시니어(60대 이상)·청소년은 독자가 아닙니다.

조로의 관점 (한마디에 녹일 것)
- 회사가 직무보다 중요하다. 실적·구조조정 기사는 "이 회사에 지원해도 되는가"로 번역한다.
- 선퇴사는 말리고 환승이직을 권한다. 채용 시즌(3~4월, 9~10월)을 기준으로 타이밍을 말한다.
- 취업은 정보 싸움이다. 공고·일정 기사는 "누가 지금 써야 하는가"를 짚는다.
- AI는 보조 도구다. AI가 직무를 바꾸는 기사는 40대 이후 생존과 중장년 재이직 관점에서 읽는다.
- 멘티에게 액션을 준다: 지원해라 / 기다려라 / 피해라 / 준비해라 중 하나는 반드시.

작성 규칙
- one_line: 기사의 핵심 사실을 40자 안팎 한 문장, "~다"로 끝나는 평서문. 제목을 반복하지 않는다.
- zorro: 'Zorro의 한마디'. 조로 말투로 60자 안팎 1~2문장. 친근한 존댓말("~입니다", "~거든요?", "~하세요")에
  솔직한 팩폭을 섞되, 비하·과장·확신 조장은 금지. 누구에게(신입/경력/재직자/40대) + 무엇을 하라 + 근거.
  "ㅎㅎ", "ㅋㅋ" 같은 웃음 표기는 하루 지면 전체에서 2개 이하. 이모지와 느낌표는 쓰지 않는다.
- tags: 기사와 가장 관련 있는 직무 태그 1~2개. 반드시 다음 중에서 고른다:
  기획, 재무, 인사, 구매, 영업, 마케팅, MD, PM, 개발, 공통.
- briefing: 오늘 지면 전체를 관통하는 흐름 3문장, 조로 말투. 각 문장은 서로 다른 이야기를 다루고,
  마지막 문장은 오늘 독자가 할 행동 하나로 끝낸다."""


class ArticleNote(BaseModel):
    id: str
    one_line: str
    zorro: str
    tags: list[str]


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


def _clean_tags(tags):
    out = [t.strip() for t in tags if t.strip() in JOB_TAGS]
    return list(dict.fromkeys(out))[:2] or ["공통"]


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
                a["ai_why"] = n.zorro.strip()      # 지면에서는 'Zorro의 한마디'로 표시 (키는 호환 유지)
                a["ai_tags"] = _clean_tags(n.tags)

    payload["briefing"] = [s.strip() for s in brief.briefing if s.strip()][:3]
    usage = response.usage
    print(f"  AI 브리핑 완료: 기사 {len(notes)}건 "
          f"(입력 {usage.input_tokens:,} / 출력 {usage.output_tokens:,} 토큰)")
    return True

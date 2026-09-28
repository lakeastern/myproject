"""Image Sensor 사업 인텔리전스 에이전트 - CLI

  python app.py ask "Sony와 OmniVision의 최근 차량용 센서 전략 비교해줘"
  python app.py                  # 대화형 모드
  python app.py collect --days 7 # LLM 없이 필수 추적 요소 수집만 (DB 적재)
  python app.py weekly           # 수집 + 주간 리포트 생성 (스케줄러용)
  python app.py stats            # DB 현황
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
sys.stdout.reconfigure(encoding="utf-8")  # Windows 콘솔 한글 출력
sys.stderr.reconfigure(encoding="utf-8")

import openai  # noqa: E402

from cis_agent import db  # noqa: E402
from cis_agent.collect import collect  # noqa: E402
from cis_agent.agent import run_agent  # noqa: E402
from cis_agent.prompts import WEEKLY_REPORT_REQUEST  # noqa: E402
from cis_agent.report import save_report  # noqa: E402


async def cmd_ask(request: str, kind: str = "adhoc") -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("✗ OPENAI_API_KEY 가 없습니다. .env.example 을 .env 로 복사해 키를 입력하세요.")
    print(f"\n▶ 요청: {request}\n")
    try:
        res = await run_agent(request)
    except openai.AuthenticationError:
        sys.exit("✗ OpenAI 인증 실패: .env 의 OPENAI_API_KEY 를 확인하세요.")
    except openai.RateLimitError as e:
        sys.exit(f"✗ 요청 한도 초과(429) 또는 크레딧 부족: {e}")
    except openai.APIStatusError as e:
        sys.exit(f"✗ API 오류 {e.status_code}: {e.message}")
    except openai.APIConnectionError as e:
        sys.exit(f"✗ API 연결 실패: {e}")

    saved = save_report(res.report_md, request, kind)
    print("\n" + "═" * 80 + "\n" + res.report_md + "\n" + "═" * 80)
    print(f"도구 호출 {len(res.tool_calls)}회 · 토큰 in {res.input_tokens:,} / out {res.output_tokens:,}")
    print(f"📄 보고서 저장: {saved['html']}\n             {saved['md']}")


async def cmd_collect(days: int) -> dict:
    return await collect(days, log=lambda m: print(f"  {m}"))


def cmd_stats() -> None:
    t = db.rows("""SELECT (SELECT COUNT(*) FROM articles) articles, (SELECT COUNT(*) FROM papers) papers,
                   (SELECT COUNT(DISTINCT ticker) FROM market_snapshots) tickers,
                   (SELECT COUNT(*) FROM insights) insights, (SELECT COUNT(*) FROM reports) reports,
                   (SELECT COUNT(*) FROM agent_runs) runs""")[0]
    print(json.dumps(t, ensure_ascii=False, indent=2))
    for r in db.rows("SELECT category, COUNT(*) n FROM articles GROUP BY category ORDER BY n DESC"):
        print(f"  {r['category']:<14} {r['n']}")


async def interactive() -> None:
    print("Image Sensor 사업 인텔리전스 에이전트 (종료: exit)")
    while True:
        try:
            q = input("\n요청> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in {"exit", "quit", "q"}:
            break
        if q:
            await cmd_ask(q)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")
    a = sub.add_parser("ask"); a.add_argument("request", nargs="+")
    c = sub.add_parser("collect"); c.add_argument("--days", type=int, default=7)
    sub.add_parser("weekly")
    sub.add_parser("stats")
    args = p.parse_args()

    if args.cmd == "ask":
        asyncio.run(cmd_ask(" ".join(args.request)))
    elif args.cmd == "collect":
        asyncio.run(cmd_collect(args.days))
    elif args.cmd == "weekly":
        print("① 필수 추적 요소 수집"); asyncio.run(cmd_collect(7))
        print("② 주간 리포트 작성"); asyncio.run(cmd_ask(WEEKLY_REPORT_REQUEST, kind="weekly"))
    elif args.cmd == "stats":
        cmd_stats()
    else:
        asyncio.run(interactive())


if __name__ == "__main__":
    main()

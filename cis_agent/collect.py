"""LLM 없이 MCP 도구를 직접 호출해 필수 추적 요소를 수집 (저비용 일일 배치). CLI·웹 공용."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

ROOT = Path(__file__).resolve().parent.parent


async def collect(days: int = 7, log: Callable[[str], None] = print) -> dict:
    transport = StdioTransport(sys.executable, ["mcp_servers/cis_intel_server.py"], cwd=str(ROOT))
    async with Client(transport) as c:
        log(f"뉴스 수집 중 (최근 {days}일, 필수 추적 요소 전체)...")
        news = await c.call_tool("collect_watchlist", {"days": days})
        summary = json.loads(news.content[0].text)["collected"]
        for s in summary.values():
            log(f"  {s['label']}: 수집 {s['found']}건 / 신규 {s['newly_saved']}건")
        log("주가 수집 중...")
        market = await c.call_tool("get_market_data", {"period": "3mo"})
        quotes = json.loads(market.content[0].text)["quotes"]
        log(f"  주가 스냅샷 {sum(1 for q in quotes if 'error' not in q)}/{len(quotes)}개 티커 저장")
        cfg = json.loads((ROOT / "config" / "tracking.json").read_text(encoding="utf-8"))
        log("논문 수집 중 (arXiv)...")
        for q in cfg["paper_queries"]:
            await c.call_tool("search_papers", {"query": q, "max_results": 5})
        log(f"  논문 쿼리 {len(cfg['paper_queries'])}개 완료")
    return summary

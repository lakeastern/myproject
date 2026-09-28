"""CIS 인텔리전스 에이전트: MCP 호스트 + OpenAI 에이전트 루프 (Responses API function calling).

사용자 요청 → LLM이 필요한 도구 판단 → MCP 서버의 도구 실행(실제 데이터) → 결과를 보고 다시 판단 → 최종 보고서.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import time
from contextlib import AsyncExitStack
from contextvars import ContextVar
from typing import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import openai
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from . import db
from .prompts import SYSTEM_PROMPT

ROOT = Path(__file__).resolve().parent.parent
MODEL = os.environ.get("CIS_MODEL") or "gpt-5.5"
EFFORT = os.environ.get("CIS_EFFORT") or "high"  # reasoning_effort: low / medium / high
MAX_TURNS = int(os.environ.get("CIS_MAX_TURNS", "40"))
MAX_TOOL_RESULT_CHARS = 40_000


@dataclass
class RunResult:
    report_md: str
    tool_calls: list[dict] = field(default_factory=list)
    stop_reason: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


# 웹 UI 등에서 진행 로그를 받아볼 수 있도록 실행 컨텍스트별 콜백을 둔다
LOG_SINK: ContextVar[Callable[[str], None] | None] = ContextVar("LOG_SINK", default=None)


def _log(msg: str) -> None:
    line = f"{datetime.now():%H:%M:%S} │ {msg}"
    print(f"  {line}", flush=True)
    if sink := LOG_SINK.get():
        sink(line)


class McpHub:
    """config/mcp_servers.json의 MCP 서버들에 연결하고 도구를 LLM function 정의로 노출한다."""

    def __init__(self, config_path: Path = ROOT / "config" / "mcp_servers.json"):
        self.config = json.loads(config_path.read_text(encoding="utf-8"))["servers"]
        self.stack = AsyncExitStack()
        self.routes: dict[str, tuple[Client, str]] = {}  # LLM tool name -> (client, mcp tool name)
        self.tools: list[dict] = []

    async def __aenter__(self) -> "McpHub":
        for name, spec in self.config.items():
            if not spec.get("enabled", True):
                continue
            cmd = sys.executable if spec["command"] == "{python}" else (shutil.which(spec["command"]) or spec["command"])
            client = Client(StdioTransport(cmd, spec.get("args", []), cwd=str(ROOT),
                                           env={**os.environ, "PYTHONIOENCODING": "utf-8"}))
            try:
                await self.stack.enter_async_context(client)
                listed = await client.list_tools()
            except Exception as e:
                _log(f"⚠ MCP 서버 '{name}' 연결 실패 → 제외: {e}")
                continue
            allowed = spec.get("allowed_tools")
            for t in listed:
                if allowed and t.name not in allowed:
                    continue
                tool_name = f"{name}_{t.name}"
                self.routes[tool_name] = (client, t.name)
                self.tools.append({"type": "function", "name": tool_name,
                                   "description": (t.description or "")[:1024],
                                   "parameters": t.input_schema, "strict": False})
            _log(f"MCP 서버 연결: {name} ({sum(1 for k in self.routes if k.startswith(name + '_'))}개 도구)")
        return self

    async def __aexit__(self, *exc) -> None:
        await self.stack.aclose()

    async def call(self, tool_name: str, args: dict) -> tuple[str, bool]:
        if tool_name not in self.routes:
            return f"알 수 없는 도구: {tool_name}", True
        client, mcp_name = self.routes[tool_name]
        try:
            res = await client.call_tool(mcp_name, args, raise_on_error=False)
        except Exception as e:
            return f"{type(e).__name__}: {e}", True
        text = "\n".join(getattr(c, "text", "") for c in res.content) or json.dumps(res.structured_content, ensure_ascii=False)
        if len(text) > MAX_TOOL_RESULT_CHARS:
            text = text[:MAX_TOOL_RESULT_CHARS] + f"\n...[결과가 길어 {len(text) - MAX_TOOL_RESULT_CHARS}자 생략됨. 범위를 좁혀 다시 조회하세요]"
        return text, res.is_error


def _summarize_args(args: dict) -> str:
    s = json.dumps(args, ensure_ascii=False)
    return s if len(s) <= 110 else s[:107] + "..."


async def run_agent(request: str) -> RunResult:
    client = openai.AsyncOpenAI()
    started = db.now_iso()
    result = RunResult(report_md="")
    today = datetime.now().strftime("%Y-%m-%d (%a)")
    items: list = [{"role": "user", "content": f"[오늘 날짜: {today}]\n\n{request}"}]

    async with McpHub() as hub:
        _log(f"모델 {MODEL} (reasoning effort={EFFORT}) · 사용 가능 도구 {len(hub.tools)}개")

        for turn in range(1, MAX_TURNS + 1):
            _log(f"[{turn}] LLM 판단 중...")
            resp = await client.responses.create(
                model=MODEL,
                instructions=SYSTEM_PROMPT,
                input=items,
                tools=hub.tools,
                parallel_tool_calls=True,
                reasoning={"effort": EFFORT},
                max_output_tokens=32000,
            )
            if resp.usage:
                result.input_tokens += resp.usage.input_tokens
                result.output_tokens += resp.usage.output_tokens
            result.stop_reason = resp.status or ""
            items += [o.model_dump(exclude_none=True) for o in resp.output]

            calls = []
            for c in (o for o in resp.output if o.type == "function_call"):
                try:
                    args = json.loads(c.arguments or "{}")
                except json.JSONDecodeError as e:
                    args = {"_invalid_json": str(e)}
                calls.append((c, args))
                _log(f"  🔧 {c.name} {_summarize_args(args)}")

            if calls:
                t0 = time.perf_counter()

                async def _run(c, args):
                    if "_invalid_json" in args:
                        return f"도구 인자 JSON 파싱 실패: {args['_invalid_json']}. 올바른 JSON으로 다시 호출하세요.", True
                    return await hub.call(c.name, args)

                outputs = await asyncio.gather(*(_run(c, a) for c, a in calls))
                for (c, args), (text, is_err) in zip(calls, outputs):
                    result.tool_calls.append({"tool": c.name, "input": args, "error": is_err, "chars": len(text)})
                    _log(f"  {'✗' if is_err else '✓'} {c.name} → {len(text):,}자")
                    items.append({"type": "function_call_output", "call_id": c.call_id,
                                  "output": f"[도구 오류] {text}" if is_err else text})
                _log(f"  도구 {len(calls)}개 실행 완료 ({time.perf_counter() - t0:.1f}s)")
                continue

            text = resp.output_text.strip()
            if resp.status == "incomplete":
                reason = resp.incomplete_details.reason if resp.incomplete_details else "unknown"
                text += f"\n\n> ⚠ 응답이 중간에 끊겼습니다 ({reason}). 보고서가 잘렸을 수 있습니다."
            result.report_md = text or "> ⚠ 모델이 빈 응답을 반환했습니다."
            break
        else:
            result.report_md = f"> ⚠ 최대 {MAX_TURNS}턴 내에 완료하지 못했습니다."
            result.stop_reason = "max_turns"

    db.execute("""INSERT INTO agent_runs (request,model,tool_calls,status,input_tokens,output_tokens,started_at,finished_at)
                  VALUES (?,?,?,?,?,?,?,?)""",
               (request, MODEL, json.dumps(result.tool_calls, ensure_ascii=False), result.stop_reason,
                result.input_tokens, result.output_tokens, started, db.now_iso()))
    return result

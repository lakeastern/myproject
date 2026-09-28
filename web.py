"""Image Sensor 인텔리전스 - 웹 UI (간단 버전)

    python web.py               # http://127.0.0.1:8000
    python web.py --host 0.0.0.0 --port 8000   # 사내망 공유 (인증 없음 주의)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import traceback
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import openai  # noqa: E402
import uvicorn  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse, HTMLResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from sse_starlette.sse import EventSourceResponse  # noqa: E402

from cis_agent import db  # noqa: E402
from cis_agent.agent import LOG_SINK, MODEL, run_agent  # noqa: E402
from cis_agent.collect import collect  # noqa: E402
from cis_agent.prompts import WEEKLY_REPORT_REQUEST  # noqa: E402
from cis_agent.report import save_report  # noqa: E402

app = FastAPI(title="CIS Intel")


@dataclass
class Job:
    id: str
    kind: str
    request: str
    logs: list[str] = field(default_factory=list)
    status: str = "running"  # running / done / error
    report_id: int | None = None
    error: str | None = None
    event: asyncio.Event = field(default_factory=asyncio.Event)

    def log(self, line: str) -> None:
        self.logs.append(line)
        self.event.set()


JOBS: dict[str, Job] = {}


async def _run_job(job: Job) -> None:
    LOG_SINK.set(job.log)  # 이 태스크 안의 에이전트 로그를 job으로 전달
    try:
        if job.kind in ("collect", "weekly"):
            await collect(7, log=job.log)
        if job.kind in ("ask", "weekly"):
            if not os.environ.get("OPENAI_API_KEY"):
                raise RuntimeError("OPENAI_API_KEY 가 설정되지 않았습니다 (.env 확인)")
            res = await run_agent(job.request)
            saved = save_report(res.report_md, job.request, "weekly" if job.kind == "weekly" else "adhoc")
            job.report_id = saved["id"]
            job.log(f"완료 · 도구 호출 {len(res.tool_calls)}회 · 토큰 in {res.input_tokens:,} / out {res.output_tokens:,}")
        job.status = "done"
    except openai.AuthenticationError:
        job.status, job.error = "error", "OpenAI 인증 실패: OPENAI_API_KEY 를 확인하세요."
    except openai.RateLimitError as e:
        job.status, job.error = "error", f"요청 한도 초과 또는 크레딧 부족: {e}"
    except openai.APIStatusError as e:
        job.status, job.error = "error", f"API 오류 {e.status_code}: {e.message}"
    except Exception as e:
        traceback.print_exc()
        job.status, job.error = "error", f"{type(e).__name__}: {e}"
    job.event.set()


class AskBody(BaseModel):
    request: str = ""
    kind: str = "ask"  # ask / weekly / collect


@app.post("/api/jobs")
async def create_job(body: AskBody):
    if body.kind not in ("ask", "weekly", "collect"):
        raise HTTPException(400, "kind 는 ask/weekly/collect 중 하나")
    if body.kind == "ask" and not body.request.strip():
        raise HTTPException(400, "요청 내용을 입력하세요")
    req = WEEKLY_REPORT_REQUEST if body.kind == "weekly" else body.request.strip()
    job = Job(id=uuid.uuid4().hex[:12], kind=body.kind, request=req)
    JOBS[job.id] = job
    asyncio.create_task(_run_job(job))
    return {"job_id": job.id}


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "job 없음")

    async def gen():
        sent = 0
        while True:
            job.event.clear()
            while sent < len(job.logs):
                yield {"event": "log", "data": job.logs[sent]}
                sent += 1
            if job.status != "running":
                yield {"event": "end", "data": json.dumps(
                    {"status": job.status, "report_id": job.report_id, "error": job.error}, ensure_ascii=False)}
                return
            try:
                await asyncio.wait_for(job.event.wait(), timeout=15)
            except asyncio.TimeoutError:
                pass  # sse-starlette가 keep-alive ping 전송

    return EventSourceResponse(gen())


@app.get("/api/reports")
def list_reports():
    return db.rows("SELECT id, title, kind, request, created_at FROM reports ORDER BY id DESC LIMIT 50")


@app.get("/reports/{report_id}")
def view_report(report_id: int):
    r = db.rows("SELECT path_html FROM reports WHERE id=?", (report_id,))
    if not r or not r[0]["path_html"] or not Path(r[0]["path_html"]).exists():
        raise HTTPException(404, "보고서 없음")
    return FileResponse(r[0]["path_html"], media_type="text/html; charset=utf-8")


@app.get("/reports/{report_id}/md")
def download_md(report_id: int):
    r = db.rows("SELECT path_md FROM reports WHERE id=?", (report_id,))
    if not r or not Path(r[0]["path_md"]).exists():
        raise HTTPException(404, "보고서 없음")
    return FileResponse(r[0]["path_md"], filename=Path(r[0]["path_md"]).name, media_type="text/markdown")


@app.get("/api/stats")
def stats():
    t = db.rows("""SELECT (SELECT COUNT(*) FROM articles) articles, (SELECT COUNT(*) FROM papers) papers,
                   (SELECT COUNT(DISTINCT ticker) FROM market_snapshots) tickers,
                   (SELECT COUNT(*) FROM insights) insights, (SELECT COUNT(*) FROM reports) reports,
                   (SELECT MAX(collected_at) FROM articles) last_collected""")[0]
    t["model"] = MODEL
    t["recent_articles"] = db.rows("""SELECT title, source, published_at, category, url FROM articles
                                      ORDER BY published_at DESC LIMIT 12""")
    return t


@app.get("/", response_class=HTMLResponse)
def index():
    return (ROOT / "static" / "index.html").read_text(encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    a = ap.parse_args()
    print(f"▶ http://{'localhost' if a.host in ('127.0.0.1', '0.0.0.0') else a.host}:{a.port}")
    uvicorn.run(app, host=a.host, port=a.port, log_level="warning")

"""CIS Intel MCP 서버 — 이미지센서 사업 인텔리전스용 도구 모음.

stdio MCP 서버로 동작하므로 이 앱의 에이전트뿐 아니라 Claude Desktop / Claude Code 등
다른 MCP 호스트에서도 그대로 붙여 쓸 수 있다.
    python mcp_servers/cis_intel_server.py
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os  # noqa: E402

os.environ.setdefault("FASTMCP_LOG_LEVEL", "WARNING")

from fastmcp import FastMCP  # noqa: E402

from cis_agent import db, sources  # noqa: E402

mcp = FastMCP("cis-intel")

# 제목에 반드시 포함돼야 하는 센서 관련 키워드 (단순 '카메라' 리뷰·쇼핑 기사 배제)
RELEVANCE = ["센서", "sensor", "cis", "isocell", "아이소셀", "imaging", "픽셀", "pixel", "spad", "lidar", "라이다",
             "tof", "machine vision", "머신비전", "global shutter", "글로벌 셔터"]


def _relevant(title: str) -> bool:
    t = title.lower()
    return any(k in t for k in RELEVANCE)


def _recent(published_at: str | None, days: int) -> bool:
    if not published_at:
        return True
    return published_at >= db.days_ago_iso(days)


def _collect_news(query: str, category: str, days: int, limit: int) -> list[dict]:
    entities = sources.load_tracking()["entities"]
    items: list[dict] = []
    for fetch in (lambda: sources.google_news(query, days=days, limit=limit),
                  lambda: sources.bing_news(query, limit=limit)):
        try:
            items.extend(fetch())
        except Exception as e:  # 한 소스 실패가 전체 수집을 막지 않도록
            items.append({"_error": f"{type(e).__name__}: {e}"})
    out = []
    for it in items:
        if "_error" in it or not _relevant(it["title"]) or not _recent(it.get("published_at"), days):
            continue
        it.update(category=category, query=query,
                  companies=sources.tag_companies(f"{it['title']} {it.get('snippet', '')}", entities))
        out.append(it)
    return out


# ============================================================== 수집 도구
@mcp.tool
def search_news(query: str, category: str = "adhoc", days: int = 14, max_results: int = 15) -> dict:
    """뉴스를 실시간 검색(Google News + Bing News)하고 결과를 DB에 자동 저장한다.

    Args:
        query: 검색어. 한글이면 국내 뉴스, 영문이면 해외 뉴스를 검색한다. 해외 동향은 영문 검색이 훨씬 풍부하다.
        category: DB 분류 태그 (samsung/competitor/customer/technology/application/market/supply_chain/adhoc).
        days: 최근 N일 이내 기사만.
        max_results: 소스별 최대 결과 수.
    """
    items = _collect_news(query, category, days, max_results)
    new, ids = db.upsert_articles(items)
    for it, i in zip(items, ids):
        it["id"] = i
    items.sort(key=lambda x: x.get("published_at") or "", reverse=True)
    return {"query": query, "found": len(items), "newly_saved": new,
            "articles": [{k: it.get(k) for k in ("id", "title", "source", "published_at", "url", "companies", "snippet")}
                         for it in items]}


@mcp.tool
def collect_watchlist(days: int = 7, categories: list[str] | None = None) -> dict:
    """config/tracking.json의 필수 추적 요소(경쟁사·고객사·기술·응용·시장·공급망 등) 전체를 일괄 수집해 DB화한다.

    정기 리포트 작성 전 최신 데이터를 확보할 때 사용. 카테고리별 신규 저장 건수와 대표 헤드라인을 반환한다.

    Args:
        days: 최근 N일 기사만 수집.
        categories: 특정 카테고리만 수집할 때 지정 (미지정 시 전체).
    """
    cfg = sources.load_tracking()
    summary = {}
    for topic in cfg["news_topics"]:
        if categories and topic["category"] not in categories:
            continue
        found, new, heads = 0, 0, []
        for q in topic["queries_ko"] + topic["queries_en"]:
            items = _collect_news(q, topic["category"], days, 15)
            n, _ = db.upsert_articles(items)
            found, new = found + len(items), new + n
            heads += [f"[{(it.get('published_at') or '')[:10]}] {it['title']} ({it.get('source')})" for it in items[:3]]
        summary[topic["category"]] = {"label": topic["label"], "found": found, "newly_saved": new,
                                      "sample_headlines": heads[:6]}
    return {"days": days, "collected": summary}


@mcp.tool
def search_papers(query: str, max_results: int = 8) -> dict:
    """arXiv에서 최신 이미지센서 관련 논문을 검색하고 DB에 저장한다 (기술 트렌드·학계 동향 파악용).

    Args:
        query: 영문 기술 키워드 (예: "SPAD image sensor", "stacked CMOS image sensor").
        max_results: 최대 결과 수.
    """
    papers = sources.arxiv_search(query, max_results)
    with db.connect() as conn:
        for p in papers:
            conn.execute("""INSERT OR IGNORE INTO papers
                (arxiv_id,title,authors,summary,published_at,url,query,collected_at) VALUES (?,?,?,?,?,?,?,?)""",
                (p["arxiv_id"], p["title"], p["authors"], p["summary"], p["published_at"], p["url"], query, db.now_iso()))
    return {"query": query, "papers": papers}


@mcp.tool
def get_market_data(tickers: list[str] | None = None, period: Literal["1mo", "3mo", "6mo", "1y"] = "3mo") -> dict:
    """주요 이미지센서 업체·고객사의 실제 주가를 조회하고 DB에 스냅샷으로 저장한다.

    Args:
        tickers: Yahoo Finance 티커 목록. 미지정 시 tracking.json의 기본 목록
                 (삼성전자, Sony, Will Semi/OmniVision, SmartSens, GalaxyCore, onsemi, SK hynix, Apple, Xiaomi).
        period: 조회 기간.
    """
    names = sources.load_tracking()["tickers"]
    tickers = tickers or list(names)
    result = []
    for t in tickers:
        try:
            c = sources.yahoo_chart(t, period)
        except Exception as e:
            result.append({"ticker": t, "error": f"{type(e).__name__}: {e}"})
            continue
        s = c["series"]
        with db.connect() as conn:
            conn.executemany("INSERT OR REPLACE INTO market_snapshots VALUES (?,?,?,?,?)",
                             [(t, names.get(t, t), d, v, c["currency"]) for d, v in s])
        first, last = s[0][1], s[-1][1]
        wk = s[-6][1] if len(s) >= 6 else first
        result.append({"ticker": t, "name": names.get(t, t), "currency": c["currency"],
                       "last_date": s[-1][0], "last_close": last,
                       "change_1w_pct": round((last / wk - 1) * 100, 2),
                       f"change_{period}_pct": round((last / first - 1) * 100, 2),
                       "period_high": max(v for _, v in s), "period_low": min(v for _, v in s)})
    return {"period": period, "quotes": result}


# ============================================================== DB 조회·분석 도구
@mcp.tool
def query_articles(keyword: str | None = None, category: str | None = None, company: str | None = None,
                   days: int = 30, min_importance: int | None = None, limit: int = 40) -> dict:
    """DB에 축적된 기사를 조건으로 조회한다 (과거 수집분 포함).

    Args:
        keyword: 제목 포함 키워드.
        category: 카테고리 필터.
        company: 기업 태그 필터 (예: Sony, OmniVision, Samsung, Apple).
        days: 최근 N일 (발행일 기준).
        min_importance: 에이전트가 매긴 중요도(1~5) 하한.
        limit: 최대 건수.
    """
    sql, p = "SELECT * FROM articles WHERE COALESCE(published_at, collected_at) >= ?", [db.days_ago_iso(days)]
    if keyword:
        sql += " AND title LIKE ?"; p.append(f"%{keyword}%")
    if category:
        sql += " AND category = ?"; p.append(category)
    if company:
        sql += " AND companies LIKE ?"; p.append(f'%"{company}"%')
    if min_importance:
        sql += " AND importance >= ?"; p.append(min_importance)
    sql += " ORDER BY published_at DESC LIMIT ?"; p.append(limit)
    rs = db.rows(sql, tuple(p))
    return {"count": len(rs), "articles": [
        {k: r[k] for k in ("id", "title", "source", "published_at", "category", "companies", "url",
                           "importance", "sentiment", "analyst_note")} for r in rs]}


@mcp.tool
def trend_stats(days: int = 28, bucket_days: int = 7) -> dict:
    """DB 기반 정량 트렌드: 기간별(주 단위) 카테고리·기업 언급량 추이와 DB 전체 현황.

    언급량 급증 기업/주제를 찾아 '신호'를 포착할 때 사용.
    """
    arts = db.rows("SELECT published_at, category, companies FROM articles WHERE published_at >= ?",
                   (db.days_ago_iso(days),))
    today = datetime.now(timezone.utc).date()
    buckets: dict[str, dict] = {}
    for a in arts:
        d = date.fromisoformat(a["published_at"][:10])
        idx = (today - d).days // bucket_days
        start = today - timedelta(days=(idx + 1) * bucket_days - 1)
        b = buckets.setdefault(start.isoformat(), {"total": 0, "by_category": {}, "by_company": {}})
        b["total"] += 1
        b["by_category"][a["category"]] = b["by_category"].get(a["category"], 0) + 1
        for c in json.loads(a["companies"] or "[]"):
            b["by_company"][c] = b["by_company"].get(c, 0) + 1
    totals = db.rows("""SELECT (SELECT COUNT(*) FROM articles) a, (SELECT COUNT(*) FROM papers) p,
                        (SELECT COUNT(*) FROM market_snapshots) m, (SELECT COUNT(*) FROM insights) i,
                        (SELECT COUNT(*) FROM reports) r""")[0]
    return {"db_totals": {"articles": totals["a"], "papers": totals["p"], "market_rows": totals["m"],
                          "insights": totals["i"], "reports": totals["r"]},
            "window_days": days, "buckets_by_start_date": dict(sorted(buckets.items()))}


@mcp.tool
def annotate_articles(annotations: list[dict]) -> dict:
    """에이전트의 기사 분석 결과(중요도·논조·코멘트)를 DB에 기록한다. 이후 min_importance로 핵심 기사만 재조회 가능.

    Args:
        annotations: [{"id": 기사id, "importance": 1~5, "sentiment": "positive|negative|neutral"
                       (삼성 CIS 사업 관점), "note": "사업적 시사점 한 줄"}]
    """
    n = 0
    with db.connect() as conn:
        for a in annotations:
            n += conn.execute("UPDATE articles SET importance=?, sentiment=?, analyst_note=? WHERE id=?",
                              (a.get("importance"), a.get("sentiment"), a.get("note"), a["id"])).rowcount
    return {"updated": n}


@mcp.tool
def save_insight(title: str, content: str, category: str, impact: Literal["high", "medium", "low"] = "medium",
                 evidence_article_ids: list[int] | None = None) -> dict:
    """핵심 인사이트를 DB에 누적 저장한다. 다음 리포트에서 '지난번 대비 변화'를 추적하는 데 쓰인다.

    Args:
        title: 인사이트 제목.
        content: 내용 (근거와 사업적 시사점).
        category: 관련 카테고리.
        impact: 삼성 CIS 사업 영향도.
        evidence_article_ids: 근거 기사 id 목록.
    """
    iid = db.execute("INSERT INTO insights (title,content,category,impact,evidence,created_at) VALUES (?,?,?,?,?,?)",
                     (title, content, category, impact, json.dumps(evidence_article_ids or []), db.now_iso()))
    return {"saved_insight_id": iid}


@mcp.tool
def get_history(kind: Literal["insights", "reports"] = "insights", limit: int = 10, report_id: int | None = None) -> dict:
    """과거에 저장한 인사이트 또는 리포트를 조회한다. report_id를 주면 해당 리포트 전문을 반환한다."""
    if kind == "reports" and report_id:
        return {"report": db.rows("SELECT * FROM reports WHERE id=?", (report_id,))}
    if kind == "reports":
        return {"reports": db.rows("SELECT id,title,kind,created_at FROM reports ORDER BY id DESC LIMIT ?", (limit,))}
    return {"insights": db.rows("SELECT * FROM insights ORDER BY id DESC LIMIT ?", (limit,))}


@mcp.tool
def get_tracking_config() -> dict:
    """현재 설정된 필수 추적 요소(카테고리·검색어·기업·티커·논문 키워드)를 반환한다."""
    return sources.load_tracking()


if __name__ == "__main__":
    mcp.run(show_banner=False)

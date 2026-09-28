"""외부 데이터 소스 수집기: 뉴스(Google/Bing News RSS), 논문(arXiv), 주가(Yahoo Finance).

모두 API 키 없이 동작하는 공개 엔드포인트를 사용한다.
주의: 뉴스 RSS는 개인·비상업 용도 약관이 있다. 사내 운영 시 유료 뉴스 API로 교체할 것.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, urlparse

import httpx

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CIS-Intel/1.0"}
TIMEOUT = httpx.Timeout(20.0)


def load_tracking() -> dict:
    return json.loads((ROOT / "config" / "tracking.json").read_text(encoding="utf-8"))


def tag_companies(text: str, entities: dict[str, list[str]] | None = None) -> list[str]:
    entities = entities or load_tracking()["entities"]
    low = text.lower()
    return [name for name, aliases in entities.items() if any(a.lower() in low for a in aliases)]


def _to_iso(pub: str | None) -> str | None:
    if not pub:
        return None
    try:
        return parsedate_to_datetime(pub).astimezone(timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        return None


def _is_korean(text: str) -> bool:
    return bool(re.search(r"[가-힣]", text))


# ---------------------------------------------------------------- 뉴스
def google_news(query: str, days: int = 14, lang: str | None = None, limit: int = 20) -> list[dict]:
    lang = lang or ("ko" if _is_korean(query) else "en")
    region = "hl=ko&gl=KR&ceid=KR:ko" if lang == "ko" else "hl=en-US&gl=US&ceid=US:en"
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}+when:{days}d&{region}"
    r = httpx.get(url, headers=UA, timeout=TIMEOUT, follow_redirects=True)
    r.raise_for_status()
    out = []
    for item in ET.fromstring(r.content).iter("item"):
        title = item.findtext("title") or ""
        source = item.findtext("source") or ""
        # Google News 제목은 "제목 - 매체명" 형태
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3]
        out.append({
            "title": title.strip(), "url": item.findtext("link") or "", "source": source,
            "published_at": _to_iso(item.findtext("pubDate")), "lang": lang, "provider": "google_news",
        })
        if len(out) >= limit:
            break
    return out


def bing_news(query: str, lang: str | None = None, limit: int = 20) -> list[dict]:
    """Bing News RSS. 원문 URL을 직접 얻을 수 있어 fetch MCP로 본문 조회가 가능하다."""
    lang = lang or ("ko" if _is_korean(query) else "en")
    mkt = "ko-KR" if lang == "ko" else "en-US"
    url = f"https://www.bing.com/news/search?q={quote_plus(query)}&format=rss&mkt={mkt}"
    r = httpx.get(url, headers=UA, timeout=TIMEOUT, follow_redirects=True)
    r.raise_for_status()
    out = []
    for item in ET.fromstring(r.content).iter("item"):
        link = item.findtext("link") or ""
        real = parse_qs(urlparse(link).query).get("url", [link])[0]
        source = ""
        for child in item:
            if child.tag.endswith("Source"):
                source = child.text or ""
        out.append({
            "title": (item.findtext("title") or "").strip(), "url": real, "source": source or urlparse(real).netloc,
            "published_at": _to_iso(item.findtext("pubDate")), "lang": lang, "provider": "bing_news",
            "snippet": (item.findtext("description") or "")[:300],
        })
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------- 논문
def arxiv_search(query: str, limit: int = 10) -> list[dict]:
    q = quote_plus(f'all:"{query}"')
    url = (f"https://export.arxiv.org/api/query?search_query={q}"
           f"&sortBy=submittedDate&sortOrder=descending&max_results={limit}")
    r = httpx.get(url, headers=UA, timeout=TIMEOUT, follow_redirects=True)
    r.raise_for_status()
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in ET.fromstring(r.content).findall("a:entry", ns):
        aid = (e.findtext("a:id", "", ns) or "").rsplit("/abs/", 1)[-1]
        out.append({
            "arxiv_id": aid,
            "title": " ".join((e.findtext("a:title", "", ns) or "").split()),
            "authors": ", ".join(a.findtext("a:name", "", ns) for a in e.findall("a:author", ns)[:6]),
            "summary": " ".join((e.findtext("a:summary", "", ns) or "").split())[:800],
            "published_at": e.findtext("a:published", "", ns),
            "url": f"https://arxiv.org/abs/{aid}",
        })
    return out


# ---------------------------------------------------------------- 주가
def yahoo_chart(ticker: str, range_: str = "3mo") -> dict:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={range_}&interval=1d"
    r = httpx.get(url, headers=UA, timeout=TIMEOUT, follow_redirects=True)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    meta = res["meta"]
    closes = res["indicators"]["quote"][0]["close"]
    series = [
        (datetime.fromtimestamp(ts, timezone.utc).date().isoformat(), round(c, 4))
        for ts, c in zip(res.get("timestamp", []), closes) if c is not None
    ]
    return {"ticker": ticker, "currency": meta.get("currency"), "series": series}

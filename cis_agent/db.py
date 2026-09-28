"""SQLite 저장소: 기사·논문·주가·인사이트·리포트·에이전트 실행 이력."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "cis_intel.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    url_hash      TEXT UNIQUE NOT NULL,
    title         TEXT NOT NULL,
    url           TEXT NOT NULL,
    source        TEXT,
    published_at  TEXT,
    lang          TEXT,
    category      TEXT,
    query         TEXT,
    companies     TEXT,
    provider      TEXT,
    collected_at  TEXT NOT NULL,
    importance    INTEGER,
    sentiment     TEXT,
    analyst_note  TEXT
);
CREATE INDEX IF NOT EXISTS ix_articles_pub ON articles(published_at);
CREATE INDEX IF NOT EXISTS ix_articles_cat ON articles(category);

CREATE TABLE IF NOT EXISTS papers (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    arxiv_id     TEXT UNIQUE NOT NULL,
    title        TEXT NOT NULL,
    authors      TEXT,
    summary      TEXT,
    published_at TEXT,
    url          TEXT,
    query        TEXT,
    collected_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS market_snapshots (
    ticker   TEXT NOT NULL,
    name     TEXT,
    date     TEXT NOT NULL,
    close    REAL,
    currency TEXT,
    PRIMARY KEY (ticker, date)
);

CREATE TABLE IF NOT EXISTS insights (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,
    category    TEXT,
    impact      TEXT,
    evidence    TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    kind       TEXT,
    request    TEXT,
    content_md TEXT NOT NULL,
    path_md    TEXT,
    path_html  TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    request     TEXT,
    model       TEXT,
    tool_calls  TEXT,
    status      TEXT,
    input_tokens  INTEGER,
    output_tokens INTEGER,
    started_at  TEXT,
    finished_at TEXT
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def days_ago_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def url_hash(url: str, title: str) -> str:
    # 같은 기사가 다른 리다이렉트 URL로 들어오는 경우가 많아 제목 기준으로도 중복 제거
    key = "".join(title.lower().split())[:120] or url
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def upsert_articles(items: list[dict]) -> tuple[int, list[int]]:
    """새로 저장된 개수와 저장된(또는 기존) 기사 id 목록을 반환."""
    new, ids = 0, []
    with connect() as conn:
        for it in items:
            h = url_hash(it["url"], it["title"])
            cur = conn.execute(
                """INSERT OR IGNORE INTO articles
                   (url_hash,title,url,source,published_at,lang,category,query,companies,provider,collected_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (h, it["title"], it["url"], it.get("source"), it.get("published_at"), it.get("lang"),
                 it.get("category"), it.get("query"), json.dumps(it.get("companies", []), ensure_ascii=False),
                 it.get("provider"), now_iso()),
            )
            new += cur.rowcount
            row = conn.execute("SELECT id FROM articles WHERE url_hash=?", (h,)).fetchone()
            ids.append(row["id"])
    return new, ids


def rows(sql: str, params: tuple = ()) -> list[dict]:
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def execute(sql: str, params: tuple = ()) -> int:
    with connect() as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid or cur.rowcount

"""에이전트 최종 답변 → Markdown/HTML 보고서 파일 + DB 기록."""
from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path

from markdown_it import MarkdownIt

from . import db

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "reports"

# 차트에 표시할 핵심 CIS 업체 (범주형 팔레트 고정 순서: 엔티티별로 색 고정)
CHART_SERIES = [
    ("005930.KS", "삼성전자", "--s1"),
    ("6758.T", "Sony", "--s2"),
    ("603501.SS", "Will Semi(OmniVision)", "--s3"),
    ("688213.SS", "SmartSens", "--s4"),
    ("688728.SS", "GalaxyCore", "--s5"),
]

CSS = """
:root{--bg:#fcfcfb;--fg:#1f1f1e;--muted:#6b6a64;--line:#e4e3dd;--card:#ffffff;--accent:#1428a0;
--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#1a1a19;--fg:#f4f3ee;--muted:#c3c2b7;
--line:#3a3935;--card:#232322;--accent:#8ea2ff;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;}}
:root[data-theme="dark"]{--bg:#1a1a19;--fg:#f4f3ee;--muted:#c3c2b7;--line:#3a3935;--card:#232322;--accent:#8ea2ff;
--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.7 "Pretendard","Malgun Gothic","Apple SD Gothic Neo",system-ui,sans-serif}
main{max-width:960px;margin:0 auto;padding:32px 16px 64px}
.meta{color:var(--muted);font-size:13px;border-bottom:2px solid var(--accent);padding-bottom:12px;margin-bottom:8px}
h1{font-size:26px;line-height:1.35;margin:8px 0 4px}
h2{font-size:19px;margin:36px 0 10px;padding-left:10px;border-left:4px solid var(--accent)}
h3{font-size:16px;margin:24px 0 8px}
a{color:var(--accent);word-break:break-all}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:6px 10px;text-align:left;vertical-align:top}
th{background:var(--card)}
blockquote{margin:12px 0;padding:8px 14px;border-left:3px solid var(--line);color:var(--muted)}
code{background:var(--card);padding:1px 5px;border-radius:4px}
figure{margin:20px 0;padding:16px;background:var(--card);border:1px solid var(--line);border-radius:8px}
figcaption{font-size:13px;color:var(--muted);margin-bottom:8px}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:13px;margin-top:8px}
.legend span::before{content:"";display:inline-block;width:14px;height:3px;border-radius:2px;background:var(--c);margin-right:6px;vertical-align:middle}
svg text{fill:var(--muted);font-size:11px}
"""


def _price_chart_svg(days: int = 90) -> str:
    """DB의 주가 스냅샷으로 핵심 업체 상대 주가(시작일=100) 라인차트를 만든다. 데이터 없으면 빈 문자열."""
    since = db.days_ago_iso(days)[:10]
    series = []
    for ticker, label, var in CHART_SERIES:
        pts = db.rows("SELECT date, close FROM market_snapshots WHERE ticker=? AND date>=? ORDER BY date", (ticker, since))
        if len(pts) >= 5:
            base = pts[0]["close"]
            series.append((label, var, [(p["date"], p["close"] / base * 100) for p in pts]))
    if not series:
        return ""
    W, H, L, R, T, B = 900, 300, 44, 150, 12, 28
    dates = sorted({d for _, _, pts in series for d, _ in pts})
    x_of = {d: L + i * (W - L - R) / max(len(dates) - 1, 1) for i, d in enumerate(dates)}
    vals = [v for _, _, pts in series for _, v in pts]
    lo, hi = min(vals + [100]) - 3, max(vals + [100]) + 3
    y = lambda v: T + (hi - v) * (H - T - B) / (hi - lo)  # noqa: E731
    parts = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="주요 CIS 업체 상대 주가 추이">']
    step = 10 if hi - lo > 40 else 5
    for g in range(int(lo // step + 1) * step, int(hi) + 1, step):
        parts.append(f'<line x1="{L}" x2="{W - R}" y1="{y(g):.1f}" y2="{y(g):.1f}" stroke="var(--line)" '
                     f'stroke-width="{1.5 if g == 100 else 1}"/><text x="{L - 6}" y="{y(g) + 4:.1f}" text-anchor="end">{g}</text>')
    for d in (dates[0], dates[len(dates) // 2], dates[-1]):
        parts.append(f'<text x="{x_of[d]:.1f}" y="{H - 8}" text-anchor="middle">{d[5:]}</text>')
    labels = []
    for label, var, pts in series:
        path = " ".join(f"{'M' if i == 0 else 'L'}{x_of[d]:.1f},{y(v):.1f}" for i, (d, v) in enumerate(pts))
        parts.append(f'<path d="{path}" fill="none" stroke="var({var})" stroke-width="2" stroke-linejoin="round">'
                     f'<title>{label}: {pts[-1][1]:.1f} ({pts[-1][1] - 100:+.1f}%)</title></path>')
        labels.append([y(pts[-1][1]), label, pts[-1][1]])
    labels.sort()
    for i in range(1, len(labels)):  # 직접 라벨 겹침 방지
        labels[i][0] = max(labels[i][0], labels[i - 1][0] + 14)
    for ly, label, v in labels:
        parts.append(f'<text x="{W - R + 8}" y="{ly + 4:.1f}" style="fill:var(--fg)">{label} {v - 100:+.1f}%</text>')
    parts.append("</svg>")
    legend = "".join(f'<span style="--c:var({var})">{label}</span>' for label, var, _ in series)
    return (f'<figure><figcaption>주요 CIS 업체 상대 주가 (최근 {days}일, 시작일=100 · Yahoo Finance)</figcaption>'
            f'{"".join(parts)}<div class="legend">{legend}</div></figure>')


def save_report(markdown: str, request: str, kind: str = "adhoc") -> dict:
    REPORT_DIR.mkdir(exist_ok=True)
    m = re.search(r"^#\s+(.+)$", markdown, re.M)
    title = m.group(1).strip() if m else request[:60]
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    slug = re.sub(r"[^\w가-힣]+", "_", title)[:40].strip("_")
    md_path = REPORT_DIR / f"{stamp}_{kind}_{slug}.md"
    html_path = md_path.with_suffix(".html")

    md_path.write_text(markdown, encoding="utf-8")
    body = MarkdownIt("commonmark").enable("table").render(markdown)
    chart = _price_chart_svg()
    if chart:  # 첫 번째 h2(요약) 다음 섹션 앞에 차트 삽입
        idx = [mm.start() for mm in re.finditer(r"<h2>", body)]
        pos = idx[1] if len(idx) > 1 else len(body)
        body = body[:pos] + chart + body[pos:]
    meta = (f'<div class="meta">Image Sensor 사업 인텔리전스 · {datetime.now():%Y-%m-%d %H:%M} 생성 · '
            f'요청: {html.escape(request[:120])}</div>')
    html_path.write_text(
        f'<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>'
        f"<style>{CSS}</style></head><body><main>{meta}{body}</main></body></html>",
        encoding="utf-8")
    rid = db.execute("INSERT INTO reports (title,kind,request,content_md,path_md,path_html,created_at) VALUES (?,?,?,?,?,?,?)",
                     (title, kind, request, markdown, str(md_path), str(html_path), db.now_iso()))
    return {"id": rid, "title": title, "md": md_path, "html": html_path}

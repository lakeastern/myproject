# Image Sensor 사업 인텔리전스 에이전트

삼성전자 Image Sensor 사업팀장 관점에서 **요청 → LLM(OpenAI)이 도구 판단·실행 → 실제 데이터 → 보고서**를 자동으로 만들어 주는 애플리케이션.

```
사용자 요청 ──▶ OpenAI (gpt-5.5, function calling)
                  │  어떤 데이터가 필요한지 판단 → tool_use (병렬)
                  ▼
          MCP Hub (cis_agent/agent.py)
          ├─ cis  : 자체 MCP 서버 (mcp_servers/cis_intel_server.py)
          │        뉴스검색·필수요소 일괄수집·arXiv 논문·주가·DB 조회/트렌드/주석/인사이트
          └─ web  : 공개 MCP 서버 (npm mcp-fetch-server) — 기사 원문 조회
                  │  실제 결과 → tool 메시지 → LLM 재판단 (반복)
                  ▼
          최종 보고서 ──▶ reports/*.md, *.html (주가 차트 포함) + SQLite DB 기록
```

## 설치 / 실행

```powershell
pip install -r requirements.txt        # Node.js(npx)도 필요: 공개 fetch MCP 서버 실행용
copy .env.example .env                 # OPENAI_API_KEY 입력 (CIS_MODEL로 모델 변경)

python app.py ask "Sony와 OmniVision의 최근 차량용 이미지센서 전략을 비교하고 우리 대응 방향을 제안해줘"
python app.py                          # 대화형 모드
python app.py collect --days 7         # LLM 없이 필수 추적 요소만 수집 (비용 0)
python app.py weekly                   # 수집 + 주간 동향 리포트
python app.py stats                    # DB 현황
```

## 웹 UI (간단 버전)

```powershell
python web.py                      # 브라우저에서 http://localhost:8000
python web.py --host 0.0.0.0       # 사내망 공유 (인증 없음 — 신뢰된 네트워크에서만)
```
- 요청 입력(예시 버튼 제공, Ctrl+Enter 실행) → 진행 로그 실시간 표시 → 완료 시 보고서 자동 표시
- 주간 리포트 / 데이터 수집 버튼, 보고서 목록(새 창·MD 다운로드), 최근 수집 기사, DB 현황

## 정기 리포트

```powershell
powershell -ExecutionPolicy Bypass -File scripts\register_schedule.ps1
```
- 매일 07:00 `collect` — 뉴스·주가·논문 DB 적재 (LLM 미사용)
- 매주 월 07:30 `weekly` — 주간 리포트 생성, 지난 리포트/인사이트 대비 변화 분석

## 필수 추적 요소 (`config/tracking.json`에서 수정)

| 카테고리 | 내용 |
|---|---|
| samsung | ISOCELL / 자사 동향 |
| competitor | Sony, OmniVision, SK hynix, SmartSens, GalaxyCore |
| customer | Apple, Galaxy, Xiaomi·Vivo·Oppo 등 세트 채용 |
| technology | 적층형, LOFIC/HDR, 글로벌셔터, SPAD, 이벤트 센서 |
| application | 차량, XR/스마트글래스, 휴머노이드/로봇 |
| market | 점유율, 시장 전망 |
| supply_chain | 파운드리, 팹 투자 |
| 주가 | 삼성전자, Sony, Will Semi, SmartSens, GalaxyCore, onsemi, SK hynix, Apple, Xiaomi |
| 논문 | arXiv: CMOS image sensor, SPAD, event-based, global shutter |

## DB (`data/cis_intel.db`, SQLite)
`articles`(기사+기업태그+에이전트 중요도/논조/시사점) · `papers` · `market_snapshots` · `insights` · `reports` · `agent_runs`(요청별 도구 호출 이력·토큰)

## MCP 서버 확장
`config/mcp_servers.json`에 서버를 추가하면 에이전트가 자동으로 도구를 인식한다.
자체 서버는 다른 MCP 호스트(Claude Desktop, Cursor 등)에도 그대로 등록 가능: `python mcp_servers/cis_intel_server.py`

## 참고/제약
- 뉴스는 Google/Bing News RSS(개인·비상업 약관). 사내 운영 시 유료 뉴스 API·시장조사(Yole, TSR, Counterpoint) 데이터로 교체 권장.
"# myproject" 

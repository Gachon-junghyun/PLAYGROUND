"""PLAY43 절대경로 상수 — 모든 경로가 여기서 파생 (PLAY33 _common.py 패턴).

원본(PLAY30/31/32/33 · mvp)은 읽기/호출만. 산출은 PLAY43/data/ 안에만.
경로 한 곳 집중 — 소스 폴더가 옮겨지면 여기만 고친다.
"""
from pathlib import Path

# scripts/_paths.py → PLAY43_card_factory
PLAY43_DIR = Path(__file__).resolve().parent.parent
PLAYGROUND = PLAY43_DIR.parent
DESKTOP = PLAYGROUND.parent

# ── 재사용 원본 (절대 변경 금지) ──
PLAY13_DIR = PLAYGROUND / "PLAY13_insight_distill"
PLAY30_DIR = PLAYGROUND / "PLAY30_naver_research_dl"
PLAY31_DIR = PLAYGROUND / "PLAY31_broker_report_distill"
PLAY32_DIR = PLAYGROUND / "PLAY32_r5_merge_v4"
PLAY33_DIR = PLAYGROUND / "PLAY33_yt_career_harvest"

BROKER_DISTILL_PROMPT = PLAY31_DIR / "prompts" / "broker_reverse_distill.md"
V4_LIB = PLAY32_DIR / "data" / "r5_v4_thinking_functions.json"
EXEC_PROTOCOL = PLAY32_DIR / "prompts" / "r5_v4_execution_protocol.md"

# ── mvp ──
MVP_DIR = DESKTOP / "mvp" / "research_Mvp"
NEWS_ALERT_DB = MVP_DIR / "news_alert.db"

# ── PLAY43 산출 (갱신 가능) ──
DATA_DIR = PLAY43_DIR / "data"
INBOX_DIR = DATA_DIR / "inbox"
INBOX_PDF_DIR = DATA_DIR / "inbox_pdf"
CARDS_DIR = DATA_DIR / "cards"
STRESS_DIR = DATA_DIR / "stress"
SEEN_REPORTS = DATA_DIR / "seen_reports.json"
V5_WORKING = DATA_DIR / "r5_v5_working.json"
REDESIGN_QUEUE = DATA_DIR / "function_redesign_queue.jsonl"


def ensure_dirs():
    for d in (DATA_DIR, INBOX_DIR, INBOX_PDF_DIR, CARDS_DIR, STRESS_DIR):
        d.mkdir(parents=True, exist_ok=True)

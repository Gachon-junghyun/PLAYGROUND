"""크롬(9222 CDP)으로 구글 검색해서 상위 결과 텍스트를 가져온다.

이미 떠있는 크롬에 새 탭으로만 붙는다 — 기존 탭/다른 에이전트 작업은 안 건드리고,
쓴 탭은 반드시 닫는다. 브라우저 자체는 절대 close() 하지 않는다(남의 크롬이라).
"""
from urllib.parse import quote

META = {
    "name": "web_search",
    "description": "웹에서 검색해 상위 결과 텍스트를 가져온다. 최신 정보나 사실 확인이 필요할 때 사용.",
    "params": {"query": "검색할 문장 또는 키워드"},
}


def run(query: str) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return "[web_search 불가] playwright 미설치. LLM 자체 지식으로 답할 것."
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            page = ctx.new_page()
            try:
                page.goto(f"https://www.google.com/search?q={quote(query)}", timeout=15000)
                page.wait_for_timeout(1500)
                return page.inner_text("body")[:3000]
            finally:
                page.close()
    except Exception as e:
        return (f"[web_search 실패] 크롬 9222 연결 안 됨({type(e).__name__}). "
                "검색 없이 LLM 자체 지식으로 답할 것.")

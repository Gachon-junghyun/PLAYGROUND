# PLAY29_naver_research_dl
# 네이버 금융 '산업분석' 리포트 목록(industry_list.naver)에서 PDF 첨부를 긁어 내려받는다.
#
# 사용법:
#   python naver_research_dl.py                 # 1페이지 전체 PDF 다운로드
#   python naver_research_dl.py --page 2        # 2페이지
#   python naver_research_dl.py --pages 1-3     # 1~3페이지
#   python naver_research_dl.py --list-only     # 다운로드 없이 목록/링크만 출력
#   python naver_research_dl.py --out ./pdfs    # 저장 폴더 지정 (기본: ./downloads)
#   python naver_research_dl.py --selftest      # 네트워크 없이 파서 단위 검증
#
# 의존성:  pip install requests beautifulsoup4
#
# 왜 requests+bs4인가: 이 목록 페이지는 서버 렌더링 HTML(EUC-KR)이라 JS 실행이 필요 없다.
# CDP/Playwright 브라우저 에이전트는 과한 도구 — 정적 HTML엔 HTTP GET + 파싱이 정답.

import argparse
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://finance.naver.com"
LIST_URL = BASE + "/research/industry_list.naver"
# 네이버는 referer/UA 없으면 막거나 빈 페이지를 주는 경우가 있어 브라우저처럼 위장.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer": LIST_URL,
}


def fetch_html(url, params=None):
    """EUC-KR 페이지를 받아 str로 디코드해 반환."""
    r = requests.get(url, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    # 네이버 금융은 EUC-KR. requests가 가끔 ISO-8859-1로 잘못 추정하니 명시.
    r.encoding = "euc-kr"
    return r.text


def _clean(s):
    return re.sub(r"\s+", " ", (s or "").strip())


def parse_list(html):
    """목록 HTML에서 리포트 행을 추출.

    각 행 dict: {category, title, broker, pdf_url, date, views}
    pdf_url이 없는(=첨부 없는) 행은 건너뛴다.

    구조 가정(2024~2026 기준): 본문 테이블의 각 <tr> 안에
    제목 셀(<a href="industry_read.naver?...">), 증권사 셀,
    PDF 첨부 셀(<a href="...*.pdf"><img ...></a>), 날짜/조회수 셀이 있다.
    클래스명에 의존하지 않고 '.pdf로 끝나는 a 태그가 있는 tr'만 리포트 행으로 본다 —
    네이버가 헤더/광고/페이지네이션 tr을 섞어두기 때문에 PDF 유무로 거른다.
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for tr in soup.find_all("tr"):
        pdf_a = None
        for a in tr.find_all("a", href=True):
            if ".pdf" in a["href"].lower():
                pdf_a = a
                break
        if pdf_a is None:
            continue  # 첨부 없는 행 = 리포트 행 아님

        pdf_url = urljoin(BASE, pdf_a["href"])

        # 제목: industry_read 로 가는 링크(첨부 .pdf 아닌 a 중 텍스트 있는 것)
        title = ""
        title_a = None
        for a in tr.find_all("a", href=True):
            if ".pdf" in a["href"].lower():
                continue
            txt = _clean(a.get_text())
            if txt:
                title = txt
                title_a = a
                break

        tds = tr.find_all("td")
        cells = [_clean(td.get_text()) for td in tds]
        # 휴리스틱: 카테고리=첫 셀, 증권사/날짜/조회수는 뒤쪽 셀에서 패턴으로 회수.
        category = cells[0] if cells else ""
        date = next((c for c in cells if re.fullmatch(r"\d{2,4}[.\-/]\d{1,2}[.\-/]\d{1,2}", c)), "")
        views = next((c for c in reversed(cells) if c.isdigit()), "")
        # 증권사: 제목·카테고리·날짜·조회수·빈칸 빼고 남는 짧은 텍스트 셀
        broker = ""
        for c in cells:
            if c and c not in (category, title, date, views) and len(c) <= 20:
                broker = c
                break

        rows.append({
            "category": category,
            "title": title or "(제목 없음)",
            "broker": broker,
            "pdf_url": pdf_url,
            "date": date,
            "views": views,
        })
    return rows


def safe_filename(row, idx):
    """제목+증권사로 안전한 파일명. 중복/특수문자 방지."""
    base = f"{idx:02d}_{row['title']}"
    if row["broker"]:
        base += f"_{row['broker']}"
    base = re.sub(r'[\\/:*?"<>|]', "", base)
    base = re.sub(r"\s+", "_", base).strip("_")
    return (base[:120] or f"report_{idx:02d}") + ".pdf"


def download(rows, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ok, fail = 0, 0
    for i, row in enumerate(rows, 1):
        fname = safe_filename(row, i)
        dest = out / fname
        if dest.exists():
            print(f"[SKIP] 이미 있음: {fname}")
            ok += 1
            continue
        try:
            r = requests.get(row["pdf_url"], headers=HEADERS, timeout=60)
            r.raise_for_status()
            dest.write_bytes(r.content)
            kb = len(r.content) // 1024
            print(f"[OK]   {fname}  ({kb} KB)  <- {row['pdf_url']}")
            ok += 1
        except Exception as e:
            print(f"[FAIL] {fname}  <- {row['pdf_url']}\n        {e}")
            fail += 1
        time.sleep(0.4)  # 과도한 요청 방지(매너)
    print(f"\n총 {len(rows)}건 중 성공 {ok} / 실패 {fail}  -> {out.resolve()}")


def parse_pages_arg(args):
    if args.pages:
        m = re.fullmatch(r"(\d+)-(\d+)", args.pages.strip())
        if not m:
            sys.exit("--pages 형식: 1-3")
        a, b = int(m.group(1)), int(m.group(2))
        return list(range(a, b + 1))
    return [args.page]


def run(args):
    pages = parse_pages_arg(args)
    all_rows = []
    for pg in pages:
        print(f"=== page {pg} 목록 가져오는 중 ===")
        html = fetch_html(LIST_URL, params={"page": pg})
        rows = parse_list(html)
        print(f"  리포트 {len(rows)}건 발견")
        all_rows.extend(rows)

    if not all_rows:
        print("리포트를 못 찾았다. --list-only 로 원본 구조를 확인하거나 페이지 구조가 바뀐 것일 수 있음.")
        return

    for i, row in enumerate(all_rows, 1):
        print(f"  [{i:02d}] {row['date']:>10} | {row['broker']:<10} | {row['title']}")

    if args.list_only:
        print("\n--list-only: 다운로드 생략. PDF URL 목록:")
        for row in all_rows:
            print(row["pdf_url"])
        return

    download(all_rows, args.out)


# ---------------- 파서 자체 검증 (네트워크 불필요) ----------------
_SAMPLE = """
<table>
 <tr><th>분류</th><th>제목</th><th>증권사</th><th>첨부</th><th>작성일</th><th>조회수</th></tr>
 <tr>
   <td>반도체</td>
   <td><a href="/research/industry_read.naver?nid=111">2026 메모리 업황 점검</a></td>
   <td>미래에셋증권</td>
   <td><a href="https://stock.pstatic.net/stock-research/industry/1/a.pdf"><img src="x"></a></td>
   <td>26.05.27</td>
   <td>1234</td>
 </tr>
 <tr>
   <td>자동차</td>
   <td><a href="/research/industry_read.naver?nid=222">전기차 수요 전망</a></td>
   <td>삼성증권</td>
   <td><a href="https://ssl.pstatic.net/imgstock/research/b.pdf"><img src="x"></a></td>
   <td>26.05.26</td>
   <td>987</td>
 </tr>
 <tr><td>광고행</td><td>첨부 없는 잡음 행</td><td></td><td></td><td></td><td></td></tr>
</table>
"""


def selftest():
    rows = parse_list(_SAMPLE)
    assert len(rows) == 2, f"기대 2건, 실제 {len(rows)}"
    assert rows[0]["title"] == "2026 메모리 업황 점검", rows[0]
    assert rows[0]["pdf_url"].endswith("/a.pdf"), rows[0]
    assert rows[0]["broker"] == "미래에셋증권", rows[0]
    assert rows[0]["date"] == "26.05.27", rows[0]
    assert rows[1]["pdf_url"].endswith("/b.pdf"), rows[1]
    fn = safe_filename(rows[0], 1)
    assert fn.endswith(".pdf") and "/" not in fn, fn
    print("selftest 통과:")
    for r in rows:
        print(" ", r)
    print("  파일명 예시:", fn)


def main():
    ap = argparse.ArgumentParser(description="네이버 금융 산업분석 PDF 다운로더")
    ap.add_argument("--page", type=int, default=1, help="가져올 페이지 (기본 1)")
    ap.add_argument("--pages", default=None, help="페이지 범위, 예: 1-3")
    ap.add_argument("--out", default="./downloads", help="저장 폴더 (기본 ./downloads)")
    ap.add_argument("--list-only", action="store_true", help="다운로드 없이 목록/URL만 출력")
    ap.add_argument("--selftest", action="store_true", help="네트워크 없이 파서 검증")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return
    run(args)


if __name__ == "__main__":
    main()

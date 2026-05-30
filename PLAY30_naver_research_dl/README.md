# PLAY29_naver_research_dl

## 목적
네이버 금융 '산업분석' 리포트 목록(`industry_list.naver`)에서 각 리포트의 PDF 첨부를 긁어 한 폴더에 내려받는 단일 스크립트.

## 실행법
```powershell
# 의존성 설치 (최초 1회)
pip install requests beautifulsoup4

# 1페이지 전체 PDF 다운로드 (기본: ./downloads 폴더에 저장)
python naver_research_dl.py

# 저장 폴더 지정
python naver_research_dl.py --out .\naver_research_reports

# 다른 페이지 / 여러 페이지
python naver_research_dl.py --page 2
python naver_research_dl.py --pages 1-3

# 다운로드 없이 목록과 PDF URL만 확인
python naver_research_dl.py --list-only

# 네트워크 없이 파서 단위 검증
python naver_research_dl.py --selftest
```

## 입력 / 출력
- **입력:** CLI 인자만. `--page`(기본 1), `--pages a-b`, `--out`(기본 `./downloads`), `--list-only`, `--selftest`. 네트워크로 네이버 목록 페이지를 직접 받는다.
- **출력:** `--out` 폴더에 `01_제목_증권사.pdf` 형식으로 PDF 저장. 콘솔에 목록과 성공/실패 집계 출력. 이미 존재하는 파일은 SKIP.

## 가정 & 제약
- **⚠️ 이 스크립트는 정현 님 로컬 PC에서 직접 실행해야 한다.** 만든 환경(Cowork)에서는 `finance.naver.com`이 웹 도구·브라우저 양쪽에서 정책적으로 차단돼 있어, 작성자(Claude)가 실제로 페이지를 받아 PDF까지 받아보는 검증은 **하지 못했다.** 차단 우회는 하지 않았다. 따라서 아래는 "검증되지 않은 가정"이다:
  - **목록 페이지 구조 가정:** 본문 테이블의 각 `<tr>` 안에 `.pdf`로 끝나는 `<a href>`(첨부 아이콘)가 있고, 그 행에 제목 링크(`industry_read.naver`)·증권사·날짜·조회수 셀이 함께 있다고 본다. 클래스명에 의존하지 않고 **".pdf 링크가 있는 tr만 리포트 행으로 간주"** 하는 방식이라 헤더/광고/페이지네이션 행은 자동으로 걸러진다. 네이버가 테이블 구조를 크게 바꾸면 0건이 나올 수 있고, 그때는 `--list-only`로 원본을 보거나 파서를 손봐야 한다. (파서 로직 자체는 샘플 HTML로 `--selftest` 통과 — 가정한 구조 하에서는 정상 작동 확인됨.)
  - **인코딩:** 네이버 금융은 EUC-KR. `r.encoding = "euc-kr"`로 강제했다. 혹시 페이지가 UTF-8로 바뀌면 제목이 깨질 수 있음.
  - **PDF 호스트:** 첨부는 보통 `stock.pstatic.net` / `ssl.pstatic.net`의 직접 `.pdf` URL. 상대경로면 `finance.naver.com` 기준으로 합친다.
  - **증권사 셀 추출은 휴리스틱**(카테고리·제목·날짜·조회수를 뺀 20자 이하 짧은 셀). 드물게 빈 값/오인식 가능 — 파일명에만 영향, 다운로드 자체엔 무관.
- **범위:** 요청은 "1페이지 전체"였다. 기본값이 1페이지다. 여러 페이지는 `--pages`로.
- **매너:** PDF 사이 0.4초 sleep. 1페이지 ~30건 기준 수십 초 내 끝나도록 설계. 대량 페이지를 한 번에 받으면 오래 걸릴 수 있음.
- **저장 위치:** 다운로드를 못 돌려서 PDF 폴더는 아직 안 만들어져 있다. 로컬에서 `--out .\naver_research_reports` 로 돌리면 그 폴더가 생성된다.
- **의존성:** `requests`, `beautifulsoup4` (둘 다 가벼움, 표준 라이브러리 아님). CDP/Playwright는 쓰지 않음 — 목록 페이지가 정적 서버 렌더링 HTML이라 브라우저가 불필요하기 때문(기존 `experiments/browser_agent`의 CDP 방식은 이 작업엔 과함).

## 더블클릭 실행
`run.bat`을 더블클릭하면 의존성 설치 → 목록 미리보기 → 1페이지 PDF를 `.\naver_research_reports`에 저장까지 한 번에 한다. (Python이 PATH에 있어야 함.)

## 변경 이력
- 2026-05-27 — 최초 생성. requests+bs4 기반 산업분석 PDF 다운로더. 파서 `--selftest` 통과. 네이버 도메인 차단으로 실제 fetch 검증은 미실시(로컬 실행 필요).
- 2026-05-27 — `run.bat` 추가(더블클릭 1회 실행: 설치+미리보기+다운로드).

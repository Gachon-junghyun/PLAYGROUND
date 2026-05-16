# PLAY4_news_retrieval

## 목적
뉴스 기사 본문을 임베딩하여 사례 검색(retrieval) DB 를 구축한다. 후속으로 (뉴스 임베딩 ↔ 다음 거래일 가격 변동) 페어를 만들어, 새 뉴스가 들어왔을 때 KNN 으로 비슷한 과거 사례를 찾아 결과 분포를 확률로 산출하는 기반.

이번 cut 은 **임베딩 풀 확장까지만**. 가격 라벨링 / retrieval 인터페이스 / 평가 루프는 후속 단계.

## 실행법
```bash
# 의존성
pip install google-genai numpy

# 실제 실행 (총 임베딩 5,000개 채울 때까지)
python -u embed_news.py 5000 > run.log 2>&1

# 테스트 (5 건만 실행)
python -u embed_news.py 5000 --dry-run
```

`embed_news.py <target_total>` 은 incremental: `article_embeddings` 테이블에 이미 들어있는 url_hash 는 스킵하고, 부족한 만큼만 새로 임베딩한다. 같은 명령으로 여러 번 돌려도 안전하고, 나중에 target 을 더 크게 해서 다시 돌리면 추가분만 임베딩한다.

## 입력 / 출력
- **입력:**
  - `data/news_alert.db` — `mvp/research_Mvp/news_alert.db` 에서 복사한 SQLite. 161MB. 핵심 테이블: `article_contents`(33,387 본문), `article_embeddings`(기존 1,600 임베딩, gemini-embedding-001, 3072d).
  - `.env` — `mvp/research_Mvp/.env` 에서 복사. `GEMINI_API_KEY` 사용. `.gitignore` 에 등재.
  - `data/kospi_all.txt` — 836 KOSPI 종목 (헤더 3줄 제외). 후속 단계용 (이번 cut 은 미사용).
  - `data/corp_codes.csv` — 회사명-종목코드 매핑. 후속 단계용 (이번 cut 은 미사용).
- **출력:**
  - `data/news_alert.db` 의 `article_embeddings` 테이블에 새 임베딩 row 추가. 스키마 동일 (`url_hash`, `embedding` BLOB, `embed_model`, `embed_dim`, `embedded_at`).
  - 콘솔/`run.log`: 진행 로그, 최종 요약, sentinel `DONE`/`FAILED`.
- **추적:** "어떤 뉴스가 임베딩됐는지"는 `article_embeddings.url_hash` 존재 여부로 자연스럽게 표현된다. 별도 추적 테이블 불필요.

## 가정 & 제약

검증 없이 진행한 부분:

1. **"5,000 개"는 총량으로 해석.** 사용자 지시가 "5,000 개로 일단 해봐". 기존 1,600 + 신규 약 3,400 = 총 5,000 으로 잡음. 추가 5,000(=총 6,600) 의도였다면 `python embed_news.py 6600` 으로 다시 돌리면 됨.
2. **선택 기준은 RANDOM (의사-).** 최근 뉴스 우선과 분포 균등 중 retrieval 풀로는 분포 균등이 더 합리적이라 판단. 시간순 정렬은 `published_at` 형식이 RFC 822 (`'Wed, 6 May 2026 ...'`) 라 SQL 정렬이 시간순과 안 맞고, 해석에 추가 코드 필요해서 일단 회피. SQL 의 `RANDOM()` 대신 `url_hash` 의 앞 8 hex 정렬을 써서 결정적 (재현 가능) — `RNG_SEED` 는 코드 상수로만 의미 있고 실제 정렬은 hash 앞부분을 씀.
3. **본문 8,000자에서 truncate.** gemini-embedding-001 의 8K 토큰 입력 한도를 한국어 1자≈1토큰으로 보수적 추정. 실제로는 더 들어가지만 안전 우선. 본문 max 가 20,338자라 일부는 잘림 — 잘린 분 신호 손실 가능.
4. **task_type=SEMANTIC_SIMILARITY 고정.** 기존 1,600 임베딩이 이 task_type 으로 빌드됐을 가능성이 높음 (mvp/module_embedding/_client.py 패턴 따름). 다른 task_type 으로 임베딩하면 같은 풀에서 cosine 비교가 깨짐.
5. **Rate limit 가정.** 기본값 sleep 0.10s ≈ 10 RPS. Gemini embedding API 의 free/paid tier 별 RPM 한도가 다른데, 내 키 등급을 모름. 429 가 자주 뜨면 `SLEEP_BETWEEN` 을 늘려라. 재시도는 10/30/60/120s 백오프 4회.
6. **추정 비용.** 본문 평균 1,522자 × 3,400건 ≈ 520만 자. 토큰 기준 200~400 만 토큰 가정 시 gemini-embedding-001 단가 ($0.15/1M tokens 정도, 변동 가능) 로 **약 $0.3~0.6**. 임베딩 자산은 일회성 비용.
7. **추정 소요 시간.** 0.10s sleep + API latency 0.2~0.5s 가정 시 호출당 0.3~0.6s. 3,400건 ≈ **17~34분**. 디스패치 Bash 의 45초 제약 때문에 무조건 백그라운드 잡으로 돌려야 함 (`run_in_background: true`).
8. **DB 동시성.** `PRAGMA journal_mode=WAL` 로 켰지만, 이 PLAY 외부에서 같은 `news_alert.db` 를 동시에 쓰면 위험. mvp 의 원본은 별도 파일이라 충돌 없음.
9. **빈 본문 2,697건은 자동 제외** (`length(body) > 0` 조건).
10. **모듈 의존:** `google-genai` 패키지 (mvp 와 동일). `python-dotenv` 는 직접 안 쓰고 자체 파서로 처리.

알려진 한계:
- 임베딩 풀이 5,000 이라도 (티커, 거래일) 셀로 집계하면 실제 분석용 표본은 훨씬 작음. 후속 cut 에서 매칭 성공률을 봐야 함.
- 뉴스 기간이 2026-05-01 ~ 05-06 약 6일. 시계열 길이 자체가 짧아 다음 거래일 수익률 예측의 통계 검증력이 약함. forward test 로 보강 필요.

## 변경 이력
- 2026-05-08 — 최초 생성. mvp/research_Mvp 에서 news_alert.db / .env / kospi_all.txt / corp_codes.csv 복사. embed_news.py 작성 (incremental, gemini-embedding-001, target_total=5000 까지 채움).

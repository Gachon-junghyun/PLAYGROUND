# PLAY2_chart_embedding

## 목적
코스피 200 종목의 1개월 단위 텍스트 차트를 임베딩으로 클러스터링하고, 각 클러스터에서 "이후 1개월" 수익률 분포를 분석한다.

## 실행법
```powershell
# 의존성 설치 (한 번만)
pip install pandas numpy scikit-learn pyarrow finance-datareader scipy dtaidistance

# 디렉토리 안에서 실행 (PYTHONPATH 자기 자신)
cd PLAY2_chart_embedding

# 1) 일봉 데이터 수집 (200종목 × ~6년 → 디스패치 45초 초과 가능성 큼.
#    백그라운드 패턴으로 띄울 것을 권장)
python -u fetch_data.py --start 2020-01-01 --end 2026-05-08 --top 200 > run_fetch.log 2>&1

# 2) 월별 차트 + 라벨
python -u build_charts.py > run_build.log 2>&1

# 3) 임베딩 + KMeans (기본: MiniBatchKMeans + n_init=3, K=20).
#    풀 KMeans는 --no_minibatch이지만 디스패치 45초 초과 가능.
python -u embed_cluster.py --k 20 --pca 64 > run_cluster.log 2>&1

# 4) 클러스터별 요약
python -u analyze.py > run_analyze.log 2>&1
```

개선 실험 (각 디스패치 호출 1개로 끝남, 자세한 결과는 "개선 실험" 섹션):
```powershell
# (1) K sweep — K마다 따로 호출
python -u sweep_k.py --k 10
python -u sweep_k.py --k 20
python -u sweep_k.py --k 40
python -u sweep_k.py --k 80
python -u aggregate_sweep.py   # k_comparison.csv 생성

# (2) 유의성 검정
python -u significance.py --clusters cache/clusters.csv --out output/significance_K20.csv
python -u significance.py --clusters cache/sweep/clusters_K10.csv --out output/sweep/significance_K10.csv
# ... K=20/40/80 동일 패턴

# (3) 우선주 제외
python -u run_no_pref.py
python -u significance.py --clusters cache/no_pref/clusters.csv --out output/no_pref/significance.csv

# (4) Sensitivity — 시나리오마다 별도 호출
python -u sensitivity.py --scenario baseline
python -u sensitivity.py --scenario chart_small
python -u sensitivity.py --scenario chart_large
python -u sensitivity.py --scenario chart_wide
python -u sensitivity.py --scenario label_5d
python -u sensitivity.py --scenario label_20d
python -u sensitivity.py --scenario label_3class
python -u aggregate_sensitivity.py
```

후속 실험 (2026-05-08 두 번째 디스패치):
```powershell
# (5) 표본 독립성 부트스트랩 — 4개 호출로 분리
python -u bootstrap_independence.py --method per_ticker --B 1000
python -u bootstrap_independence.py --method block --block_L 3 --B 500
python -u bootstrap_independence.py --method block --block_L 6 --B 500
python -u bootstrap_independence.py --method block --block_L 12 --B 500

# (6) 새 임베딩 3종 — 각각 별도 호출
python -u embed_norm_series.py
python -u significance.py --clusters cache/emb_norm_series/clusters.csv --out output/emb_norm_series/significance.csv
python -u embed_shape_features.py
python -u significance.py --clusters cache/emb_shape_features/clusters.csv --out output/emb_shape_features/significance.csv
python -u embed_dtw_prototype.py
python -u significance.py --clusters cache/emb_dtw_prototype/clusters.csv --out output/emb_dtw_prototype/significance.csv

# (7) 종합 비교
python -u aggregate_embeddings.py
```

시장 통제 실험 (2026-05-08 세 번째 디스패치, B-1 norm_series K=20 고정):
```powershell
# (8) KOSPI 지수 fetch (1티커, ~3초). FDR pyopenssl 의존이 깨져 있어 스크립트가 자동 패치.
python -u fetch_market.py

# (9) simple/CAPM 잔차 라벨 + B-1 클러스터에 머지 (~5초)
python -u compute_residuals.py

# (10) 시장 중립 cluster summary + significance
python -u analyze_market_neutral.py
python -u significance.py --clusters cache/emb_norm_series/clusters_simple.csv --out output/market_neutral/significance_simple.csv
python -u significance.py --clusters cache/emb_norm_series/clusters_capm.csv --out output/market_neutral/significance_capm.csv

# (11) 부트스트랩 (block L=6 만, B=500). bootstrap_independence.py 의 --clusters 옵션 재사용.
python -u bootstrap_independence.py --clusters cache/emb_norm_series/clusters_simple.csv --method block --block_L 6 --B 500 --out output/market_neutral/bootstrap_simple_block_L6.csv
python -u bootstrap_independence.py --clusters cache/emb_norm_series/clusters_capm.csv --method block --block_L 6 --B 500 --out output/market_neutral/bootstrap_capm_block_L6.csv

# (12) Cross-sectional (시점 단위)
python -u cross_sectional.py

# (13) 회귀 (Linear / Ridge / RandomForest × 3 라벨)
python -u regression.py

# (14) 통합 비교
python -u build_comparison.py
```

검증용 작은 표본:
```powershell
python -u fetch_data.py --top 5 --start 2024-01-01 --end 2024-12-31 --force
python -u build_charts.py
python -u embed_cluster.py --k 3
python -u analyze.py
```

## 입력 / 출력
- 입력: 외부 — FinanceDataReader가 KRX/네이버 등에서 일봉 OHLCV를 받아온다. 인터넷 필요. 종목 유니버스는 `fdr.StockListing("KOSPI")`의 시가총액 상위 N(기본 200).
- 출력 (모두 PLAY 디렉토리 기준):
  - `cache/universe.csv` — 선정된 N종목 (Code, Name, Marcap)
  - `cache/ohlcv.parquet` — 일봉 OHLCV. 컬럼: `code, name, date, open, high, low, close, volume`
  - `cache/samples.parquet` — 월별 샘플. 컬럼: `code, name, year_month, n_days, ret_next, sign_next, chart_text, grid_tokens`
    - `grid_tokens`: (PRICE_ROWS+VOL_ROWS) × COLS = 20 × 22 = 440 길이 정수 리스트
    - `sign_next`: `U`(상승) / `D`(하락) / `F`(0)
    - `ret_next`: 다음달 첫 close → 다음달 마지막 close 비율 - 1
  - `cache/embeddings.npy` — float32, 임베딩 벡터 (기본 차원 = 440 × 7 = 3080, `--pca`로 축소 가능)
  - `cache/clusters.csv` — 샘플별 cluster_id 매핑
  - `output/cluster_summary.csv` — 클러스터별 통계: `n_samples, up_count, up_rate, down_count, down_rate, mean_ret, median_ret, p25_ret, p75_ret`. up_rate 내림차순.
  - `output/cluster_centroids.txt` — 클러스터별 무작위 5개 샘플의 텍스트 차트 (육안 확인용)
  - **(후속)** `cache/bootstrap/` (없음 — bootstrap은 cache 안 씀), `output/bootstrap/per_ticker_K20.csv`, `output/bootstrap/block_L{3,6,12}_K20.csv`, `output/bootstrap/summary_compare.csv`
  - **(후속)** `cache/emb_norm_series/`, `cache/emb_shape_features/`, `cache/emb_dtw_prototype/` — 각 임베딩의 `embeddings.npy`, `clusters.csv` (+ shape_features는 `feature_names.txt`, dtw는 `proto_idx.npy`)
  - **(후속)** `output/emb_norm_series/`, `output/emb_shape_features/`, `output/emb_dtw_prototype/` — 각각 `cluster_summary.csv`, `significance.csv`
  - **(후속)** `output/embedding_compare.csv` — 4개 임베딩 종합 비교
  - **(시장 통제)** `cache/market/kospi.parquet` — KOSPI 종합지수 일봉.
  - **(시장 통제)** `cache/market/labels_residual.csv` — `code, year_month, ret_next, ret_market_next, beta_60d, ret_residual_simple, ret_residual_capm`.
  - **(시장 통제)** `cache/emb_norm_series/clusters_simple.csv`, `clusters_capm.csv` — B-1 클러스터 + 잔차 라벨로 ret_next/sign_next 교체.
  - **(시장 통제)** `output/market_neutral/cluster_summary_{simple,capm}.csv`, `significance_{simple,capm}.csv`, `bootstrap_{simple,capm}_block_L6.csv`, `comparison.csv`.
  - **(시장 통제)** `output/cross_sectional/cluster_cs_summary.csv`.
  - **(시장 통제)** `output/regression/results.csv`.

## 가정 & 제약
- **종목 유니버스**: 사용자 합의로 "현재 시점 코스피 200 ≈ KOSPI 시총 상위 200" 으로 단순화. `fdr.StockListing("KOSPI200")`은 미구현이라 사용 불가. 우선주(예: 005935 삼성전자우)도 시총 상위면 포함된다 — 일반적인 KOSPI 200 구성과 약간 다를 수 있음.
- **데이터 소스**: pykrx는 이 환경에서 KRX 응답이 비어 있어 사용 불가. 대신 `FinanceDataReader 0.9.110`을 사용한다. 휴장일 처리·상장폐지 종목 누락 가능성 있음.
- **월 윈도우**: 캘린더 월 단위. 한 달 안 거래일 < 10이면 해당 샘플 버림. 따라서 신규 상장 직후 월, 거래정지 많은 월은 자동 제외됨.
- **차트 크기**: cols=22, price_rows=16, vol_rows=4 (총 20×22 = 440 셀)로 고정. 한 달 거래일이 22 초과면 마지막 22일만, 22 미만이면 우측 패딩. 패딩이 임베딩 공간에서 의미 있는 신호로 잡힐 가능성 있음.
- **임베딩**: 신경망 임베딩 일체 사용 안 함. 각 셀의 토큰을 길이-7 원-핫으로 펼쳐 평탄화. 결과적으로 임베딩 거리는 셀 단위 일치도(Hamming 거리에 비례).
- **클러스터링**: 기본 MiniBatchKMeans(K=20, n_init=3, seed=42, batch_size=1024). 풀 KMeans는 `--no_minibatch`로 가능하나 디스패치 45초 한도를 초과한다. K는 임의값 — 검증 안 됨. PCA는 기본 64.
- **라벨 정의**: 다음 달의 (마지막 close / 첫 close) - 1. 갭/배당 보정 안 함.
- **시간 제약**: `fetch_data.py`는 200종목 × 6년 호출 시 디스패치 45초를 초과한다. 백그라운드 패턴으로 띄울 것. `build_charts.py`/`embed_cluster.py`/`analyze.py`는 캐시된 입력에서 시작하므로 단일 호출로 끝남.
- **재실행**: `fetch_data.py`는 `cache/ohlcv.parquet`이 있으면 자동 스킵. `--force`로 재요청.
- **시크릿**: 없음.

### 개선 실험 추가 가정 (2026-05-08)
- **K sweep**: 기존 PCA 64 임베딩을 그대로 재사용. silhouette는 안 계산. inertia만 기록하므로 elbow 결정 근거는 약함.
- **유의성 검정**: 클러스터 vs '나머지 전체'로 정의. 같은 종목의 다른 시점 샘플이 양쪽에 섞여 표본 독립성 가정이 약함 — p-value를 보수적으로 해석. BH/Bonferroni는 같은 K 안의 검정만 묶어 보정. ret_next 분포가 정규가 아니라 t-test 결과는 근사.
- **우선주 정의**: 종목코드 마지막 자리가 '5' OR 종목명이 '우' 또는 '우B'. 풀 universe 200개 중 5개 해당.
- **Sensitivity 라벨 변형**: 기존 cluster_id를 재사용. 라벨 정의가 바뀌면 더 좋은 클러스터링이 따로 있을 가능성은 무시.
- **Sensitivity 차트 변형 PCA**: 동일 PCA 차원에서 비교. 정보 손실 정도가 시나리오마다 다름.

### 후속 실험 추가 가정 (2026-05-08 두 번째)
- **per-ticker 부트스트랩 단순화**: 매 반복마다 KMeans 재적합 안 하고 기존 cluster_id 그대로 재사용. 종목당 1샘플만 뽑으면 N=200 → 클러스터당 ~10. 검정력이 매우 낮아 0/20 유의 판정 — 이게 "보정"이라기보다 "검정력 한계 시연"에 가까움.
- **블록 부트스트랩 자기상관 가정**: moving block bootstrap (overlapping). 종목별 시계열 길이 T 가 L 미만이면 그 종목은 그대로 사용 (블록화 안 함). T=70 평균에서 L=3/6/12 모두 적용 가능. 동일 cluster_id 재사용 (KMeans 재적합 안 함). 시장 추세에 의한 자기상관은 일부 보정되나 cross-sectional 의존성은 보정 안 됨.
- **부트스트랩 empirical p-value 정의**: 매 반복의 (클러스터 up_rate − 베이스라인 up_rate) 분포에서 0 대비 양측 p = 2·min(P(diff≥0), P(diff≤0)).
- **B-1 정규화 시계열 길이 20**: build_charts 의 cols=22 와 다름 — PCA 가능하도록 짧게. 한 달 거래일이 20 미만인 샘플은 마지막 값으로 우측 패딩. 패딩이 PCA에 노이즈를 더할 수 있음.
- **B-2 shape feature 10개**: ret_month, max_drawdown, recovery, vol_daily, skew, kurt, high_pos, low_pos, bull_ratio, vol_logstd. 거래량은 "월 내부 변동성(log std)"으로 단순화 — 사용자 지정 "거래량 z-score 평균(=0)" 을 유의미한 피처로 바꿈.
- **B-3 DTW prototype**: dtaidistance 의 C 백엔드(`distance_matrix_fast`) 사용. 길이 20 시계열 × 200 prototype × 13,971 샘플 ≈ 3초로 끝남. PCA 16 으로 압축. 거리 행렬을 직접 PCA에 넣어 좌표화 — 정확한 metric 의미는 약하지만 거리 보존 측면에서 충분.
- **K=20 고정**: 4개 임베딩 모두 K=20 으로만 클러스터링. K 변경에 robust한지는 측정 안 함.
- **시간 측정 (디스패치, 2026-05-08)**:
  - bootstrap_independence.py per_ticker B=1000: ~0.3초.
  - bootstrap_independence.py block L=3/6/12 B=500: 각 ~1.2초.
  - embed_norm_series.py: ~6초 (시계열 빌드 5.5초가 대부분).
  - embed_shape_features.py: ~20초 (피처 계산이 itertuples 로 sample 단위 루프라 느림).
  - embed_dtw_prototype.py: ~9초 (시계열 5.5초 + DTW 3초).
  - aggregate_embeddings.py: 1초 미만.
  - 모두 단일 디스패치 호출(45초)로 통과.

### 시장 통제 실험 추가 가정 (2026-05-08 세 번째)
- **B-1 임베딩 고정**: 모든 분석은 cache/emb_norm_series/ (PCA 8) 의 K=20 클러스터를 재사용. B-2 (shape_features) 는 ret_month 가 직접 피처라 미래 라벨에 대한 누설 위험이 있어 제외. cell_onehot/B-3 도 비교 대상에서 제외 (B-1 이 후속 실험에서 가장 robust한 baseline 으로 판정됨).
- **시장 지수**: KOSPI 종합지수(`KS11`). KOSPI 200 (`KS200`) 미사용 — 코드 매핑이 환경마다 차이 있고 종합지수가 코스피 대형주 평균과 충분히 가까움.
- **시장 라벨 윈도우**: 각 (종목, year_month) 의 라벨 = 다음 캘린더월 첫 close → 마지막 close. 시장도 동일 윈도우의 KOSPI 종합지수 첫 close → 마지막 close 비율 - 1. 휴장일/배당 보정 안 함.
- **베타 추정**: 종목 일별 수익률 vs KOSPI 일별 수익률, rolling 60거래일 cov/var. 윈도우 끝 = year_month 마지막 거래일 (라벨 시작 직전) 시점의 베타를 그 (종목, year_month) 의 베타로 사용 — 라벨 미래 정보 사용 안 함. 60일 미달 종목·시점은 412 샘플(2.95%) NaN → CAPM 잔차에서 제외.
- **CAPM 잔차 정의**: `ret_next - beta * ret_market_next`. 무위험수익률 차감 안 함. 알파 의도 = 0 가정.
- **부트스트랩 — block L=6 만**: 잔차 라벨에 대해 per_ticker / L=3, L=12 는 시간 절약 목적으로 생략. 이전 실험에서 L=3/6/12 결과가 거의 동일했음.
- **Cross-sectional 시점 필터**: 한 (cluster × month) 셀의 종목 수 < 5 인 셀은 분산 불안정으로 제외. 1,363 cluster-month 중 508 (37.3%) 제외 — 작은 클러스터의 통계는 사실상 측정 못 함.
- **Cross-sectional 부트스트랩**: 클러스터별 시점 시퀀스에 대해 moving block (L=6) bootstrap, B=500. 시점 < 5 또는 < L 인 클러스터는 부트스트랩 NaN.
- **회귀 split**: time-series 1회 분할. 75개월 정렬 후 앞 60개월(2020-01..2024-12) 학습, 뒤 15개월(2025-01..2026-03) 검증. K-fold 안 씀. cutoff 위치에 결과 sensitivity 측정 안 함.
- **회귀 X**: PCA 8차원 임베딩만. 비선형 신호 탐색은 RandomForest (n_estimators=100, max_depth=8, n_jobs=-1) 로.
- **시간 측정 (디스패치, 2026-05-08 세 번째)**:
  - fetch_market.py: ~3초. compute_residuals.py: ~5초.
  - analyze_market_neutral.py + significance × 2: 각 ~1초.
  - bootstrap_independence.py block L=6 (B=500) × 2: 각 ~1.2초.
  - cross_sectional.py: ~1초.
  - regression.py: ~8초 (RF 3개 학습이 2~3초씩).
  - 모두 단일 디스패치 호출(45초)로 통과.

## 실측 결과 (2026-05-08 풀 실행)
- 데이터: 200종목 × 일봉 290,444행. fetch ~21초.
- 샘플 N = 13,971. 베이스라인 up_rate = 0.5224, mean_ret = +2.36%.
- KMeans K=20 (MiniBatch + PCA 64): 최강 클러스터 19 (N=593) up_rate **0.6324**, mean_ret +6.32%; 최약 5(N=906) 0.4713, 13(N=898) 0.4733.
- 클러스터 19 의 시각 특성: 월초 급락 후 월말 반등 (낙폭과대 후 회복) 형태로 보임.

## 변경 이력
- 2026-05-08 — 최초 생성. fetch → build → cluster → analyze 4단계 파이프라인.
- 2026-05-08 — 풀 실행 완료. KMeans → MiniBatchKMeans + n_init=3, PCA 64.
- 2026-05-08 — 4가지 개선 추가 (sweep_k, significance, run_no_pref, sensitivity).
- 2026-05-08 — **후속 실험 추가**: 표본 독립성 부트스트랩 (per_ticker B=1000, block L=3/6/12 B=500) + 새 임베딩 3종 (B-1 정규화 시계열, B-2 shape feature, B-3 DTW prototype). 4검정(BH+block3/6/12) 모두에서 일관 유의한 클러스터 = up_rate 2/20, mean_ret 1/20. 5검정 (per_ticker 포함) 모두에서는 0/20 — per_ticker 검정력 한계.
- 2026-05-08 — **시장 통제 실험 추가**: B-1 임베딩 K=20 고정. (1) 시장 효과 제거(simple, CAPM 잔차 라벨) 후 BH α=0.05 유의 클러스터 0/20 — 원시 라벨에서의 4-5/20 유의 시그널이 전부 시장 추세 효과였음을 시사. (2) Cross-sectional 분석 (시점 평균 차감) 도 BH 0/20. (3) 회귀(Linear/Ridge/RF × 3 라벨) 모두 검증 R² < 0, RF가 선형 대비 의미있게 좋지 않음 — 임베딩 공간에 비선형 신호도 거의 없음. **결론: 패턴-수익률 시그널의 대부분은 시장 추세에 의한 자기상관/공통요인이었고, 시장 효과를 제거하면 종목 특이적 신호가 사실상 0.**
- 2026-05-08 — **풀 차트 (RSI/OBV/MA/볼린저) 재실험**: module_text_chart 풀 렌더러를 PLAY2 안으로 복사(text_chart/), 27×22 풀 그리드(13971 샘플) 재생성 (cache/full/charts_full.npz). 셀 알파벳 12종 자동 수집, 셀-원핫 7128차원 → TruncatedSVD 64 → MiniBatchKMeans K=20. 핵심 5개 실험(a/c/g/i/k) 풀 차트로 재실행. **raw**: top up_rate 0.6324→0.6842, spread 16.1→23.6pp, BH t/p 5/3→6/4. **시장 잔차**: simple/CAPM 모두 BH t/p 0~1/20 (캔들만과 동일 결론). **회귀**: 모든 라벨 R²<0, 캔들만보다 약간 더 음수. **결론: 지표 추가가 raw 시그널은 강화하지만 그 강화분 전부가 시장 효과로 환원되어 종목 특이적 알파는 캔들만과 동일하게 ~0.** 후속 (b/d/e/f/h/j) 6개는 별도 디스패치로 이월.

## 개선 실험 (2026-05-08)

### 신규 스크립트
- `sweep_k.py` — K∈{10,20,40,80}. PCA 64 임베딩 재사용.
- `aggregate_sweep.py` — `output/sweep/k_comparison.csv` 집계.
- `significance.py` — Welch t-test + two-proportion z-test, BH/Bonferroni 보정.
- `run_no_pref.py` — 우선주 제외 universe 로 build → embed → cluster → analyze.
- `sensitivity.py --scenario S` — 차트/라벨 변형 7시나리오.
- `aggregate_sensitivity.py` — `sensitivity_summary.csv` 집계.

### 결과 요약

**(1) K sweep** — `output/sweep/k_comparison.csv`
| K  | inertia | 최강 up_rate | n   | Δ(pp) | 최약 up_rate | n   |
|----|---------|--------------|-----|-------|--------------|-----|
| 10 | 889,980 | 0.5940 | 1,266 | +7.16  | 0.4905 | 1,158 |
| 20 | 834,536 | 0.6324 |   593 | +11.00 | 0.4713 |   906 |
| 40 | 782,459 | 0.7875 |   240 | +26.51 | 0.4403 |   318 |
| 80 | 728,564 | 0.9806 |   155 | +45.83 | 0.4029 |   139 |

**(2) 유의성 검정 (K=20, BH α=0.05)**
- ret_next Welch t-test: 5/20 유의
- up_rate two-proportion z-test: 3/20 유의
- (Bonferroni: 4/20, 3/20)

**(3) 우선주 제외**
풀(200종목) → 195종목으로 줄여도 베이스라인 up_rate −0.03pp, 최강 클러스터 up_rate −1.78pp, 유의 클러스터 5→4. 영향 거의 없음.

**(4) Sensitivity (`output/sensitivity/sensitivity_summary.csv`)**
- 베이스라인 up_rate 자체는 차트 크기 변화에는 안 흔들리고, 라벨 정의에 따라 ±1pp 변동.
- 클러스터 spread (max−min)는 차트 변형에서 16→24pp 로 늘어남. 패턴-수익률 신호는 차트 변형에 sensitive (robust 하지 않음).
- 라벨 변형은 비교적 robust.

## 후속 실험 (2026-05-08, 두 번째 디스패치)

### 신규 스크립트
- `bootstrap_independence.py --method {per_ticker, block} [--block_L L] --B B` — 표본 독립성 보정 부트스트랩. 결과 `output/bootstrap/per_ticker_K20.csv` / `block_L{3,6,12}_K20.csv`.
- `embed_norm_series.py` — 정규화 가격 시계열 + z-score → 길이 20 → PCA 8 → KMeans K=20.
- `embed_shape_features.py` — 10개 shape feature → z-score → KMeans K=20.
- `embed_dtw_prototype.py` — DTW (dtaidistance) 200 prototype 거리 → PCA 16 → KMeans K=20.
- `aggregate_embeddings.py` — `output/embedding_compare.csv` + `output/bootstrap/summary_compare.csv` 동시 생성.

### 부트스트랩 결과 (K=20, α=0.05)
| 검정 | 유의 cluster (up_rate) | 유의 cluster (mean_ret) |
|------|-----------------------|-------------------------|
| 기존 BH (K=20) | 3/20 | 5/20 |
| per_ticker (B=1000) | 0/20 | 0/20 |
| block_L=3 (B=500) | 4/20 | 6/20 |
| block_L=6 (B=500) | 5/20 | 5/20 |
| block_L=12 (B=500) | 5/20 | 5/20 |

- **5검정 (BH + per_ticker + block 3/6/12) 모두 일관 유의**: up_rate **0/20**, mean_ret **0/20**. per_ticker 의 underpower 가 결정적.
- **4검정 (BH + block 3/6/12, per_ticker 제외) 일관 유의**: up_rate **2/20** (cluster 13, 5 — 둘 다 "약한" 클러스터로 유의하게 baseline 미만), mean_ret **1/20** (cluster 3 — baseline 초과).
- 최강 클러스터 19 (up_rate 0.6324) 는 BH/block_L3/6 에서 유의했으나 block_L12 (p=0.296) 와 per_ticker (p=0.51) 에서 떨어짐 — 자기상관 보정 정도와 표본 축소에 따라 유의성이 흔들린다 = "robust한 시그널이 아니다".

### 임베딩 3종 비교 (`output/embedding_compare.csv`)
| 임베딩 | dim | spread (pp) | top up_rate (n) | weak up_rate (n) | BH α=0.05 (t-test, prop) |
|--------|-----|-------------|------------------|------------------|---------------------------|
| cell_onehot (기존)   | PCA 64 (3080) | 16.11 | 0.6324 (n=593) | 0.4713 (n=906) | 5, 3 |
| norm_series (B-1)    | PCA 8 (20)    | 14.08 | 0.5944 (n=429) | 0.4536 (n=507) | 5, 4 |
| shape_features (B-2) | 10            | **46.12** | **0.9096 (n=166)** | 0.4484 (n=368) | **9, 5** |
| dtw_prototype (B-3)  | PCA 16 (200)  | 11.95 | 0.5818 (n=758) | 0.4623 (n=504) | 4, 1 |

### 해석
- **B-2 (shape_features)** 가 spread (+46pp) 와 유의 클러스터 수 (9 t-test) 양쪽에서 압도. 다만 top cluster up_rate 0.9096 은 N=166 의 작은 표본 — 평균회귀 가능성 큼. shape feature 가 "실제 미래 신호" 를 더 잘 잡는다기보다 "shape feature 가 미래 수익률과 더 강한 상관 차원을 직접 임베딩에 박은 결과" 일 수 있다 (예: ret_month 자체가 피처라 momentum/reversal 효과를 직접 클러스터링).
- **B-1 (norm_series PCA)** 와 **B-3 (DTW prototype)** 은 기존 cell_onehot 과 비슷한 수준 (spread 12~14pp). 차트 해상도에 robust 한가는 별도 검증 필요 (현재 측정은 베이스라인 K=20 한 번뿐).
- 가장 robust 한 임베딩은? — **데이터 효율성 측면에선 B-1 (PCA 8 차원에서 5/4 BH 유의 달성)**. 하지만 "신호 강도" 측면에선 B-2 가 압승. 추천:
  - 차트 행/열 변형 robustness 만 본다면 B-1.
  - 신호 강도(클러스터 spread + 유의성)를 본다면 B-2.
  - 둘을 평균적으로 잘 하는 baseline이 필요하면 cell_onehot 도 나쁘지 않음.

### 한계
- 부트스트랩 모두 KMeans 재적합 안 함 (디스패치 시간 단축). cluster boundary 자체의 불확실성은 보정 안 됨.
- B-2 의 ret_month 피처가 실제로 다음달 ret_next 와 momentum/reversal 관계라면, B-2 는 임베딩이 라벨을 간접적으로 보고 있는 셈 — 데이터 누설은 아니지만 "패턴이 미래를 예측한다"는 인과 해석은 금물.
- B-3 DTW 의 prototype 200개는 무작위 — prototype 선택에 따라 결과가 흔들릴 수 있음 (시드 고정만 함, 강건성 측정 안 함).

## 시장 통제 실험 (2026-05-08, 세 번째 디스패치)

### 신규 스크립트
- `fetch_market.py` — KOSPI 종합지수(`KS11`) 일봉 fetch.
- `compute_residuals.py` — simple/CAPM 잔차 라벨 + B-1 클러스터 머지.
- `analyze_market_neutral.py` — `cluster_summary_{simple,capm}.csv`.
- `cross_sectional.py` — 시점 평균 차감 후 클러스터별 cs_residual 분포 + t-test/BH/block bootstrap.
- `regression.py` — Linear/Ridge/RandomForest × 3 라벨, time-series split.
- `build_comparison.py` — `output/market_neutral/comparison.csv`.

### 시장 효과 제거 후 클러스터 결과 (B-1 K=20, BH α=0.05)
| 라벨 | 베이스라인 up_rate | 베이스라인 mean | 최강 클러스터 up_rate | 유의 (prop / t-test BH) | block L=6 boot α=0.05 |
|------|-------------------|------------------|----------------------|-------------------------|----------------------|
| ret_next (원시) | 0.5224 | +2.36% | 0.5944 (n=429) | 4/20, 5/20 | (이전 후속에서 5/20, 5/20) |
| ret_residual_simple | 0.4723 | +0.65% | 0.5035 (n=429) | **0/20, 0/20** | up_rate 2/20, mean 2/20 |
| ret_residual_capm | 0.4826 | +0.92% | 0.5357 (n=420) | **0/20, 0/20** | up_rate 3/20, mean 4/20 |

- 베이스라인 up_rate 이 0.522 → 0.472/0.483 으로 떨어짐 = 원시 라벨 베이스라인의 +2.2pp 만큼이 시장 추세 효과.
- 최강 클러스터 up_rate Δ: simple −9.1pp (0.5944 → 0.5035), CAPM −5.9pp (0.5944 → 0.5357).
- BH 보정 유의 클러스터: 4/20 → **0/20** (둘 다). 블록 부트스트랩(BH 미적용)에선 2-4 건 유의가 남지만, 다중검정 보정 후엔 사라짐.

### Cross-sectional (`output/cross_sectional/cluster_cs_summary.csv`)
- N=13,971 → 1,363 cluster-month 셀 → MIN_N=5 필터로 855 셀 (37.3% 제외).
- BH α=0.05 유의: **0/20**. 블록 부트스트랩 단독: 1/20 (cluster 4, p=0.024 — BH 후 0.948 로 떨어짐).
- mean_cs_residual 의 절댓값 최대치 ≈ 0.94% (cluster 14, n_periods=24) — 표본 크기·표준편차 고려하면 0과 구분 안 됨.

### 회귀 (`output/regression/results.csv`, time-series split 60/15 개월)
| 라벨 | best 모델 | R² (검증) | sign_acc | top-bottom quintile spread |
|------|-----------|-----------|----------|----------------------------|
| ret_next | linear/ridge | **−0.110** | 0.603 | +0.0019 |
| ret_residual_simple | linear/ridge | −0.012 | 0.420 | +0.0077 |
| ret_residual_capm | linear/ridge | −0.002 | 0.458 | +0.0036 |

- **R² 모두 0보다 작음** = 임베딩 기반 예측이 평균(=0)을 그대로 쓰는 것보다도 못함.
- ret_next 의 sign_acc 0.603 은 검증 기간(2025-01..2026-03) 시장 상승 추세에서 그냥 "U 다수" 가 정답인 효과 — 잔차 라벨에선 0.42–0.46 으로 떨어져 무의미.
- **RF (n_estimators=100, max_depth=8) ≤ Linear/Ridge**: 모든 라벨에서 RF 가 R² 더 작음. 임베딩 공간에 비선형 신호도 사실상 없음.
- 5분위 long-short spread: simple 0.77pp, CAPM 0.36pp — 거래비용 0bp 가정에서도 미미.

### 통합 비교 (`output/market_neutral/comparison.csv`) — 분석별 1줄 요약
| 분석 | 라벨 | 통계량 | 유의 (BH α=0.05) |
|------|------|--------|------------------|
| cluster (raw) | ret_next | top up_rate 0.5944 | 4/20 prop, 5/20 t-test |
| cluster (mkt_neutral) | residual_simple | top 0.5035 | **0/20, 0/20** |
| cluster (mkt_neutral) | residual_capm | top 0.5357 | **0/20, 0/20** |
| cross_sectional | cs_residual | max +0.94pp | **0/20** |
| regression | ret_next | best R²=−0.110 | — |
| regression | residual_simple | best R²=−0.012 | — |
| regression | residual_capm | best R²=−0.002 | — |

### 핵심 인사이트
- **시장 효과를 제거하면 시그널은 거의 전부 사라진다.** 원시 라벨에서 보였던 "up_rate +7-11pp" 클러스터는 "그 클러스터에 분류된 종목들이 평균적으로 시장 상승기에 등장했다" 는 사실에 거의 모두 귀속됨. CAPM 잔차에서도 같은 결론.
- **Cross-sectional 분석도 같은 결론**: 한 시점의 모든 종목 평균을 빼면 클러스터별 잔차는 0과 구분되지 않는다. 시점 효과(=시장 효과)가 클러스터 spread 의 거의 모든 분산을 설명.
- **회귀 R² < 0**: 임베딩 8차원에 다음달 잔차 수익률을 설명하는 선형/비선형 정보가 사실상 없음. RF가 도움 안 됨 → "모델이 약했다" 라기보단 "정보가 없다" 에 가까움.
- **결론 강도 (저자 판단)**: 강함. 검정 3종(클러스터 t-test/proportion + cross-sectional + 회귀) 이 일관되게 시장 효과 제거 후 0 신호를 가리키며, BH 보정에서 모두 0/20 통과. 데이터/임베딩/라벨/모델 모두 다양화했음에도 일관됨.
- **단, 절대 단언은 금물**: K=20 단일 K, B-1 단일 임베딩, 60일 베타, 1회 time-series split 만 측정. 이 결론을 흔들 수 있는 변형 — Mid/Low cap 종목 한정, K=80 fine-grained, 더 짧은(주간) 라벨, 산업 중립화 — 은 측정 안 함.

### 한계 (시장 통제)
- KOSPI 종합지수 ≠ 동일가중 시장 평균. 대형주 편향이 있어 잔차가 "대형주 대비 초과수익" 에 가까움. 동일가중 평균과 비교한 적 없음.
- 베타 60일 윈도우는 임의 선택. 30/120일 변형 측정 안 함.
- Cross-sectional MIN_N=5 필터로 작은 클러스터의 cs_residual 시계열이 짧아져 검정력이 떨어짐 — 0/20 결과의 일부는 검정력 한계일 수 있음.
- time-series split 1회 — cutoff 변경에 R² 가 흔들릴 수 있음. cutoff sensitivity 측정 안 함.

## 풀 차트 (RSI/OBV/MA/볼린저 포함) 실험 — 2026-05-08, 네 번째 디스패치

### 누락 발견
이전까지 PLAY2의 `text_chart/renderer.py` 는 `module_text_chart` 의 캔들 부분만 복사한 상태였다. 그래서 (1) RSI 서브차트, (2) OBV 캔들 색상 (가격 기반), (3) MA20/60 오버레이, (4) 볼린저 밴드 오버레이가 모두 빠진 채 클러스터링이 진행됐다. 이번 라운드에서 풀 렌더러를 PLAY2 안으로 복사하고 27행×22열 풀 그리드(price 16 + vol 4 + RSI 7) 를 새로 생성한 뒤, 5개 핵심 실험을 풀 차트로 재실행했다.

### 신규 스크립트 / 디렉토리
- `text_chart/` — `module_text_chart` 의 풀 렌더러 5개 파일(`_constants.py, _utils.py, indicators.py, metadata.py, renderer.py`) 복사. fetcher(`_ohlcv.py`) 제외.
- `text_chart/renderer.py` 끝에 `build_full_grid(df, price_rows=16, vol_rows=4, rsi_rows=7, cols=22)` 헬퍼 추가 — 라벨/축 없는 raw 셀 매트릭스(27, 22) 반환.
- `build_charts_full2.py` — `cache/samples.parquet` 의 (code, year_month) 인덱스 그대로 사용해 각 샘플별 풀 그리드 재생성. 청크 모드(5000건/청크) + `--merge` 로 통합.
- `embed_full.py` — 셀-원핫 평탄화(13971 × 27·22·12=7128) → TruncatedSVD 64 → MiniBatchKMeans K=20.
- `regression_full.py` — 풀 임베딩 PCA64 × 라벨 3종 × 모델 3종 회귀.

### 산출물 위치
- `cache/full/charts_full.npz` — (13971, 27, 22) int8 그리드 + 알파벳 12종 (`' ' * + : = ^ v · ─ │ █ ░`).
- `cache/full/embedding_pca.npy` — TruncatedSVD 64차원, explained_var 0.478.
- `cache/full/clusters_K20.npy` — 풀 차트 K=20 cluster_id.
- `cache/full/clusters_K20{,_simple,_capm}.csv` — significance/bootstrap 입력용 CSV.
- `output/full/cluster_summary_K20.csv` + `cluster_centroids.txt`
- `output/full/significance_K20.csv`
- `output/full/market_neutral/{cluster_summary,significance,bootstrap_block_L6}_{simple,capm}.csv`
- `output/full/regression/results.csv`
- `output/full/grand_comparison.csv`

### 핵심 5개 실험 결과

| 실험 | 메트릭 | 풀차트 | 캔들만 (기존) |
|------|--------|--------|---------------|
| (a) 베이스라인 K=20 | top up_rate (n) | **0.6842** (n=323) | 0.6324 (n=593) |
| (a) 베이스라인 K=20 | spread (max−min) | **23.6pp** | 16.1pp |
| (a) 베이스라인 K=20 | top mean_ret | **+9.78%** | +6.32% |
| (c) 유의성 K=20 raw | t-test BH α=0.05 | **6/20** | 5/20 |
| (c) 유의성 K=20 raw | prop BH α=0.05 | **4/20** | 3/20 |
| (g) 시장 잔차 simple | t-test/prop BH | **0/20, 0/20** | 0/20, 0/20 |
| (g) 시장 잔차 CAPM | t-test/prop BH | **0/20, 1/20** | 1/20, 1/20 |
| (g) block L=6 boot simple | up_rate sig (raw α=0.05) | **4/20** | 3/20 |
| (g) block L=6 boot CAPM | up_rate sig (raw α=0.05) | **7/20** | 5/20 |
| (i) 회귀 raw | best R² (RF) | **−0.131** | −0.110 (Ridge) |
| (i) 회귀 simple | best R² (Lin/Ridge) | **−0.0135** | −0.012 |
| (i) 회귀 CAPM | best R² (Lin/Ridge) | **−0.0026** | −0.002 |

### 캔들만 vs 풀차트 인사이트
- **원시 라벨에서는 풀 차트가 신호를 약간 강화한다.** Spread 가 16.1pp → 23.6pp 로 +7.5pp 증가하고 top up_rate 가 0.632 → 0.684 로 +5pp 증가. BH 보정 유의 클러스터도 t-test 5→6, prop 3→4 로 +1 씩. 즉 RSI/OBV/MA/BB 정보가 클러스터 분리도를 키운다.
- **그러나 시장 효과 제거 시 차이는 거의 사라진다.** simple 잔차 라벨에서 BH 유의 클러스터가 캔들만/풀 모두 0/20. CAPM 에서 풀이 t-test 1/20 → 0/20 으로 오히려 줄었다(prop 은 양쪽 1/20). block L=6 부트스트랩(BH 미적용) 에서는 풀이 simple 4/20, CAPM 7/20 으로 캔들만(3/20, 5/20) 대비 살짝 많지만, 다중검정 보정 후엔 모두 ~1 이하로 수렴.
- **회귀에서도 풀차트가 캔들만보다 더 나쁘다.** 모든 라벨에서 R² < 0 이고 풀이 캔들만보다 약간 더 음수쪽. RF 도 도움 안 됨 = 비선형 신호도 없음. 임베딩 차원에 다음달 잔차 수익률을 설명하는 정보가 사실상 없다는 결론은 캔들만/풀 모두 동일.
- **결론: 지표 추가가 raw 시그널을 강화하지만 그 강화분이 전부 시장 추세 효과로 환원된다.** "패턴-수익률" 의 추가 분리도는 종목 특이적 신호가 아니라 "시장 상승기에 더 자주 나오는 패턴" 효과이고, 시장 효과를 빼면 캔들만과 거의 동일한 0 신호로 떨어진다. 결론 강도는 시장 통제 실험(세 번째 디스패치) 과 동일 — 강함.

### 가정 & 제약 (풀 차트)
- **풀 그리드 차원**: 27 행(price 16 + vol 4 + RSI 7) × 22 열 = 594 셀. 캔들 + MA20/60 + 볼린저(상/중/하) 오버레이 + OBV 색상 거래량 + RSI(14) 서브차트(70/50/30 기준선 포함).
- **셀 알파벳 12 종** (자동 수집): `' '`(빈칸), `*`(RSI 중립), `+`(RSI 과매수), `:`(RSI 50선), `=`(RSI 과매도), `^`(BB 상단), `v`(BB 하단), `·`(BB 중단), `─`(DOJI/RSI 30·70선/OBV 0선), `│`(꼬리), `█`(양봉/OBV 매수), `░`(음봉/OBV 매도). MA20(`.`)·MA60(`-`)·VOL_BEAR(`▒`) 는 거의 캔들·OBV 우선순위에 가려져 알파벳에 등장 안 함 — 정보 손실 가능성 있음 (육안 확인 필요).
- **임베딩**: 셀-원핫 평탄화 7128 차원 sparse → **TruncatedSVD 64** (PCA 가 dense 7128 차원에서 메모리 부담이라 SVD 사용. explained_var 0.478, 즉 47.8%). 캔들만 cell_onehot 원본은 3080 차원(440 셀 × 7 알파벳)→PCA 64 (README "기존 실험" 섹션) 와 직접 비교 가능.
- **indicator 계산은 module 에 위임**: RSI/MA/BB 모두 module_text_chart 풀 렌더러가 자체 계산. PLAY2 fetch_data 와 무관한 indicator 함수를 재사용.
- **차트 재생성 시간**: 청크 0-5000 18s, 5000-10000 23s, 10000-13971 22s, merge 1.6s = 합 ~64s 분산. 단일 디스패치 호출(45s) 안 들어가지 않아 청크 분할 필수.
- **PCA 차원 변경**: 사용자 명시 PCA 64 그대로 유지 가능했음(시간 부담 X). 32 로 축소 안 함.
- **잔차 라벨 재사용**: 기존 `cache/market/labels_residual.csv` (세 번째 디스패치 산출) 그대로 사용. 풀 차트 cluster_id 와 머지만.
- **캔들만 cell_onehot 잔차 분석은 이번에 신규**: 이전엔 norm_series(B-1) 임베딩으로만 잔차 분석했고, cell_onehot 캔들만 임베딩에 대해선 안 돌아갔음. 이번 (k) grand_comparison 의 fair 비교를 위해 `cache/cellonehot_residual/` + `output/cellonehot_residual/` 에 추가.
- **이전 위임 산출물**: 같은 라운드에서 두 번 위임된 에이전트가 사양 위반(440+8 차원 단순화)을 반복해 만든 9개 파일(`build_charts_full.py, build_full_charts.py, build_full_embeddings.py, embed_cluster_full.py, sweep_k_full.py, run_quick_full_suite.py, run_full_experiments.py, INDEX_FULL_CHART_EXPERIMENTS.md, FULL_CHART_EXECUTION_SUMMARY.txt`) 는 cowork 환경에서 파일 삭제 권한이 거부되어 deprecated 스텁 한 줄로 무력화. 활성 풀 차트 코드는 `build_charts_full2.py`, `embed_full.py`, `regression_full.py` 셋.
- **미실행 (후속 예정)**: (b) K sweep K∈{10,40,80}, (d) 우선주 제외, (e) sensitivity 7시나리오, (f) 부트스트랩 per_ticker / block L=3/12, (h) cross-sectional, (j) metadata features 임베딩. 시간 제약 + 핵심 5개 실험만으로도 캔들만 vs 풀의 본질적 결론이 도출되어 다음 디스패치로 이월.

### 후속 예정
다음 디스패치에서 (b)(d)(e)(f)(h)(j) 6개 실험을 풀 차트로 추가 실행. 모두 캔들만 결과(README 위 섹션) 와 1:1 비교 표 만들기.


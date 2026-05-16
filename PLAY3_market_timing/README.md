# PLAY3_market_timing

## 목적
PLAY2의 차트 모양 클러스터 분포가 KOSPI 다음달 수익률을 예측할 수 있는 시장 타이밍 신호로 작동하는지 검증.

## 실행법
```powershell
# 의존성 설치
pip install pandas numpy scikit-learn scipy matplotlib pyarrow

# 단계별 실행 (PLAY2 cache가 이미 존재한다고 가정)
python PLAY3_market_timing/build_panel.py    # (1) 시점별 클러스터 분포 → cache/timing_panel.parquet
python PLAY3_market_timing/lead_lag.py       # (2) lead-lag 상관 → output/lead_lag_correlation.csv
python PLAY3_market_timing/walk_forward.py   # (3) 70/30 walk-forward → output/walk_forward_results.csv
python PLAY3_market_timing/make_plots.py     # (4) 시각화 → output/cluster_vs_kospi.png, timing_panel_with_kospi.csv
```

각 스크립트는 인자 없이 PLAY3 루트 또는 PLAYGROUND 루트에서 실행 가능. 현재 작업 디렉토리에 무관하게 PLAY3 cache를 찾는다.

## 입력 / 출력
**입력 (PLAY2 cache 재사용 — 코드 의존이 아닌 데이터 산출물 재사용):**
- `PLAY2_chart_embedding/cache/samples.parquet` — (code, year_month, ret_next, sign_next 등 13,971행)
- `PLAY2_chart_embedding/cache/full/clusters_K20_full.npy` — 풀 차트 K=20 cluster_id (samples와 행 정렬)
- `PLAY2_chart_embedding/cache/full/embeddings_pca_64_full.npy` — 풀 임베딩 PCA 64
- `PLAY2_chart_embedding/cache/market/kospi.parquet` — KOSPI 일별 종가/수익률 (2019-12 ~ 2026-05)

**출력:**
- `cache/cluster_dist_by_month.parquet` — year_month × (cluster_0_pct ... cluster_19_pct, top1_pct, bot1_pct, n_stocks)
- `cache/timing_panel.parquet` — 위 + KOSPI 당월/다음달 수익률 join
- `output/lead_lag_correlation.csv` — (cluster_id, lag, pearson_r, p_value)
- `output/walk_forward_results.csv` — (model, features, train_R2, test_R2, test_sign_acc)
- `output/cluster_vs_kospi.png` — top1/bot1 클러스터 비율 vs KOSPI 시계열
- `output/timing_panel_with_kospi.csv` — 사람이 직접 보고 판단할 수 있는 한 장짜리 패널

## 가정 & 제약
- **Top1/Bot1 클러스터 정의:** 학습 데이터(또는 전체 풀 데이터) 평균 ret_next 기준으로 **가장 높은 평균 수익률 클러스터를 top1, 가장 낮은 평균 수익률 클러스터를 bot1**으로 사전 정의. PLAY2 분석에서 cluster_19/cluster_0 류로 집계됐을 가능성이 높지만 실제 ID는 데이터로 결정. (1)단계에서 이 매핑을 산출해 `cache/cluster_ranking.csv`에 저장.
- **PLAY2 클러스터링은 in-sample fit이라는 한계:** 풀 데이터 13,971개 전체로 KMeans를 적합한 결과라 미래 정보가 클러스터 분포에 누설돼 있을 여지가 있다. 이를 우회하기 위해 (3) walk-forward에서는 **학습기간 데이터만으로 KMeans를 다시 fit** 한 뒤 검증기간 샘플을 transform하여 cluster_dist를 재계산한다.
- **70/30 split의 임의성:** 시간순 70/30으로 자르면 학습 ≈ 2020-01 ~ 2024-04 (52개월), 검증 ≈ 2024-05 ~ 2026-03 (23개월) 정도. split 비율을 다른 값(60/40, 80/20)으로 바꾸면 결과가 흔들릴 수 있다. 본 PLAY는 70/30 단일값만 보고하며, 결과 해석에 신뢰구간을 부여하지 않는다.
- **표본 크기 한계:** 75개월 시계열로는 lag = -3~+3 cross-correlation의 통계적 검정력이 약하다. p-value는 참고용으로만 보고하며 다중검정 보정 안 함.
- **KOSPI 월간 수익률 정의:** 매월 마지막 영업일 종가 기준 monthly compound return. `ret_next`(KOSPI)는 t+1월 수익률.
- **단순화 B (분기별 walk-forward) 미수행:** 시간 제약 + 디스패치 ~45초 한계로 단순화 A만 진행. 분기별 재적합 walk-forward는 후속 PLAY 또는 오프라인 작업.
- **클러스터 비율 신호의 노이즈:** 매월 KOSPI 200 중 코드 ~190개 정도가 분류돼 cluster_pct 단위가 0.5%pt(=1종목) 정도라 시계열이 톱니 모양이 될 수 있다. 평활화는 적용하지 않음.
- **회귀 baseline:** KOSPI 자체 momentum (lag-1, lag-3 월간 수익률)만으로 같은 회귀 fit. 클러스터 신호가 baseline 대비 train/test R²를 얼마나 끌어올리는지로 추가 정보량 평가.
- **Random Forest 하이퍼파라미터:** n_estimators=100, max_depth=8, random_state=42 고정. 튜닝 안 함.
- **디스패치 시간 제약 대응:** KMeans는 학습기간 데이터만(약 9,800샘플 × 64차원)으로 fit. 단일 호출에서 ~5초 내. RF 회귀도 75 행 미만이라 빠름.
- **시각화 백엔드:** GUI 없이 `matplotlib.use('Agg')`로 png 저장만.

## 핵심 결과 요약 (2026-05-08 실행)

**Top1 / Bot1 매핑 (전체 데이터 평균 ret_next 기준):**
- top1 = cluster_11 (mean ret_next = +5.76%)
- bot1 = cluster_19 (mean ret_next ≈ -0.00%)
- 상위/하위 클러스터의 평균 수익률 분리도가 비대칭. "강한 약세 클러스터"는 사실상 없음.

**(2) Lead-Lag (cluster_pct vs KOSPI 월간 수익률, lag = -3..+3, n=72~75):**
- 전 클러스터 평균 |r|이 lag=0에서 0.290으로 압도적 (lag=-1: 0.110, lag=+1: 0.068).
- top1_pct: lag=0 r=-0.30 (p=0.008), 다른 lag는 모두 |r|<0.15.
- bot1_pct: lag=0 r=-0.42 (p=0.0002), lag=-3 r=-0.23 (p=0.054)로 약한 lead 신호 잔재.
- 결론: 모양 신호와 KOSPI는 **동시기 상관**이 본체. 모양이 시장을 lead 한다는 증거 미약.

**(3) Walk-Forward (70/30 split, 학습 2020-01~2024-04 49개월, 검증 2024-05~2026-03 23개월):**
- 모든 cluster_only 모델의 test R² < 0 (학습기간 R²는 0.29~0.83 → 심한 overfit).
- 가장 좋은 test R²: Linear momentum_only baseline 0.084. 클러스터 추가 시 오히려 악화.
- 단, RF cluster_only / cluster+momentum의 test sign accuracy는 0.739로 mean baseline 0.565 대비 +17%pt. 단순 회귀는 망가져도 부호 예측력은 잔존.
- 종합: 클러스터 비율은 **수치 회귀로는 KOSPI 다음달 수익률을 예측 못 하지만**, 비선형 모델의 **부호 분류로는 약한 신호 가능성** 있음. 다만 23개월 검증 표본은 너무 작아 안정적 결론 어려움.

**한 줄 결론:** 차트 모양 클러스터 분포는 **시장 동시기 상태를 반영하는 거울이지 lead 시그널이 아니다**. 시장 타이밍 신호로서는 **약(weak)** — 부호 예측에 한해 보조 지표 가능성, 수익률 회귀 예측력은 사실상 없음.

## 변경 이력
- 2026-05-08 — 최초 생성. build_panel/lead_lag/walk_forward/make_plots 작성. 결과 요약 추가.

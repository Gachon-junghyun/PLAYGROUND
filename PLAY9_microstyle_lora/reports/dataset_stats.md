# PLAY9 데이터셋 통계

전체 1411건 → train 1327 / val 84 (val_ratio=0.06).

## 문자 길이 (char count)
- **system**: n=1411, min=166, median=166, p90=166, p99=166, max=166
- **user (입력 톡)**: n=1411, min=10, median=37, p90=58, p99=77, max=80
- **assistant (think + reply)**: n=1411, min=339, median=515, p90=610, p99=709, max=840
- **think 내용만**: n=1411, min=300, median=465, p90=562, p99=654, max=805
- **reply 한 줄만**: n=1411, min=10, median=33, p90=47, p99=59, max=76
- **system+user+assistant total**: n=1411, min=542, median=720, p90=820, p99=921, max=1023

## 토큰 길이 추정
- p99 total char ≈ 921 → token 추정 ≈ 1197
- **권장 max_seq_length: 1280**

## 주의
- 토큰 카운트는 char × 1.3의 거친 추정. 학습 시작 직후 실제 tokenizer로 한 번 더 측정해라.
- p99에 맞추면 1% truncate. p99.9로 맞추거나 패딩 부담이 크면 줄여도 됨.

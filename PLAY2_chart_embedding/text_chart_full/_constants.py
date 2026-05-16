# Full-chart constants (RSI/OBV/MA/Bollinger)

# === 캔들 문자 ===
EMPTY     = " "
WICK      = "│"
BULL_BODY = "█"
BEAR_BODY = "░"
DOJI_BODY = "─"

# === 거래량 문자 ===
VOL_BULL = "█"
VOL_BEAR = "▒"

# === 지표 기본 문자 ===
DEFAULT_IND_CHARS = [".", "-", "+", "~", "*", "="]

# 캔들 문자는 지표보다 우선
_CANDLE_CHARS = {WICK, BULL_BODY, BEAR_BODY, DOJI_BODY}

# === RSI 서브차트 문자 ===
RSI_DOT = "*"   # 중립 (30~70)
RSI_OB  = "+"   # 과매수 (>70)
RSI_OS  = "="   # 과매도 (<30)
RSI_REF = "─"   # 30/70 기준선
RSI_MID = ":"   # 50 중간선

# === OBV 서브차트 문자 ===
OBV_BULL = "█"
OBV_BEAR = "░"
OBV_ZERO = "─"

# === 통합 차트 고정 지표 문자 ===
_COMBINED_IND_CHARS = {
    "MA20":     ".",
    "MA60":     "-",
    "BB_upper": "^",
    "BB_mid":   "·",
    "BB_lower": "v",
}

# === 토큰 어휘 (캔들 + MA + BB + OBV + RSI) ===
# 총 ~12 문자: 캔들(5) + 지표문자(6) + RSI(5) + OBV(2) 중 중복 제거
# 실제 사용 어휘를 자동으로 수집할 것이므로, 여기선 기본만.
TOKEN_VOCAB = [
    EMPTY,      # 0
    WICK,       # 1
    BULL_BODY,  # 2
    BEAR_BODY,  # 3
    DOJI_BODY,  # 4
    VOL_BULL,   # 5
    VOL_BEAR,   # 6
    ".",        # 7 — MA20
    "-",        # 8 — MA60
    "^",        # 9 — BB_upper
    "·",        # 10 — BB_mid
    "v",        # 11 — BB_lower
    RSI_DOT,    # 12 — *
    RSI_OB,     # 13 — +
    RSI_OS,     # 14 — =
    RSI_REF,    # 15 — ─
    RSI_MID,    # 16 — :
    OBV_BULL,   # 17 — █
    OBV_BEAR,   # 18 — ░
    OBV_ZERO,   # 19 — ─ (중복)
]

TOKEN_ID = {ch: i for i, ch in enumerate(TOKEN_VOCAB)}

def build_token_id_from_chars(chars_set):
    """동적으로 발견된 문자 집합에서 TOKEN_ID 재구성."""
    vocab = sorted(chars_set)
    return {ch: i for i, ch in enumerate(vocab)}

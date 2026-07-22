"""규칙 기반 태깅 — LLM 없이 (토큰 0).

핵심 설계(가설):
- 주제/앱 분류는 '줄'이 아니라 '화면(capture)' 단위로 한다. 한 스크린샷은 보통
  한 가지에 관한 것이므로, 화면 전체 텍스트 + 활성앱으로 한 번 정하고 그 화면의
  모든 줄이 상속받는다 → 키워드 없는 일반 문장도 과소집계되지 않음.
- 앱은 강한 사전확률. Word→학교공부, Claude→바이브코딩 prior 를 점수로 주고
  키워드 증거가 충분하면 뒤집는다(점수 argmax).
- '내용 거의 같음' 링크는 기호를 떼낸 normalize 로 사소한 OCR 차이를 흡수.

규칙은 rules.json(사용자 편집). /reload-rules 로 무중단 갱신.
"""
import json
import re
import threading
from datetime import datetime, timedelta, timezone

import config

_lock = threading.Lock()
_rules = None

# 활성 앱(front_app)은 '지금 뭘 하는지'의 가장 강한 신호다. 그래서 앱 prior 를
# 높게 둬서 '활성 앱 기준으로 가되, 키워드 증거가 압도적(8개+)일 때만 뒤집기'로.
APP_PRIOR = 8
KW_CAP = 20        # 키워드 점수 상한(반복 텍스트가 점수를 폭주시키지 않게)
CROSS_APP_MIN = 4  # 특정 앱용 주제가 '다른 앱' 화면을 가로채려면 키워드가 이만큼은 필요


def load_rules():
    global _rules
    with _lock:
        with open(config.RULES_PATH, encoding="utf-8") as f:
            _rules = json.load(f)
    return _rules


def rules():
    if _rules is None:
        load_rules()
    return _rules


# --- 내용 유사 링크용 정규화 ---------------------------------------------- #
# 소문자화 + 영숫자/한글만 남기고 기호 제거 → "작업방 4" 와 "작업방 4|" 가 같은 norm.
_KEEP = re.compile(r"[^0-9a-z가-힣\s]")
_WS = re.compile(r"\s+")


def normalize(text):
    if not text:
        return ""
    t = _KEEP.sub(" ", text.lower())
    return _WS.sub(" ", t).strip()


MIN_LINK_LEN = 6  # 이보다 짧은 norm 은 너무 흔해서 과거 링크에서 제외


# --- 앱 버킷 -------------------------------------------------------------- #
def app_bucket(front_app, text):
    fa = (front_app or "").lower()
    tx = (text or "").lower()
    for name, spec in rules()["app_buckets"].items():
        if any(n.lower() in fa for n in spec.get("app", [])):
            return name
        if any(h.lower() in tx for h in spec.get("text", [])):  # Gmail 등 브라우저 내부 앱
            return name
    return "기타"


# --- 화면 단위 분류 (핵심) ------------------------------------------------ #
def classify_capture(front_app, full_text):
    """화면 전체 텍스트 + 활성앱 -> (bucket, topic).
    topic = 키워드 출현수(상한) + 앱 prior 의 argmax. 전부 0이면 '기타'."""
    bucket = app_bucket(front_app, full_text)
    tx = (full_text or "").lower()
    best, best_score = "기타", 0
    for name, spec in rules()["topics"].items():
        kw = min(sum(tx.count(k.lower()) for k in spec.get("keywords", [])), KW_CAP)
        apps = spec.get("apps", [])
        if bucket in apps:           # 이 화면의 앱이 곧 이 주제 → prior + 키워드
            score = APP_PRIOR + kw
        elif apps:                   # 특정 앱용 주제인데 지금은 다른 앱 → 강한 증거만 인정
            score = kw if kw >= CROSS_APP_MIN else 0
        else:                        # 앱에 매이지 않은 주제(수산나=이름 기반) → 키워드만으로 발화
            score = kw
        if score > best_score:       # 동점이면 rules.json 순서가 우선
            best, best_score = name, score
    return bucket, best


# --- 시간 --------------------------------------------------------------- #
def local_dt(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc) + timedelta(hours=config.TZ_OFFSET_HOURS)


def period_of(ts):
    h = local_dt(ts).hour
    if h < 6:
        return "새벽"
    if h < 12:
        return "아침"
    if h < 18:
        return "오후"
    return "저녁"


def app_names():
    return list(rules()["app_buckets"].keys()) + ["기타"]


def topic_names():
    return list(rules()["topics"].keys()) + ["기타"]

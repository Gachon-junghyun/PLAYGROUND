"""환경변수 기반 설정. 시크릿은 코드에 박지 않고 전부 env로 받는다."""
import os

_HERE = os.path.dirname(__file__)


def _get(name, default=None):
    v = os.environ.get(name)
    return v if v not in (None, "") else default


# 인증 토큰. 미설정이면 인증 엔드포인트는 503으로 거부한다(시크릿 하드코딩 금지).
TOKEN = _get("HINDSIGHT_TOKEN")

DB_PATH = _get("HINDSIGHT_DB", os.path.join(_HERE, "hindsight.db"))

# 앱/주제 분류 규칙(사용자 편집). LLM 안 쓰는 규칙 기반 태깅.
RULES_PATH = _get("HINDSIGHT_RULES", os.path.join(_HERE, "rules.json"))

# date 파라미터/기본 윈도우를 사용자 로컬 하루로 해석하기 위한 오프셋. KST=+9.
TZ_OFFSET_HOURS = int(_get("HINDSIGHT_TZ_OFFSET_HOURS", "9"))

HOST = _get("HINDSIGHT_HOST", "0.0.0.0")
PORT = int(_get("HINDSIGHT_PORT", "8000"))

SEARCH_DEFAULT_LIMIT = 50       # /search 기본 반환 세그먼트 수
TIMELINE_MAX_LINES = 5000       # /timeline 한 번에 반환할 세그먼트 상한
BREAKDOWN_MAX_LINES = 100000    # /breakdown 이 집계할 윈도우 내 세그먼트 상한
TEXT_BLOB_MAX_CHARS = 40000     # /timeline 의 ready-to-read text 블록 글자 상한

# 같은 (내용, 앱)이 이 갭(초) 안에 또 잡히면 '지속'으로 보고 한 세그먼트에 합친다.
# 갭을 넘겨 다시 나타나면 '재방문'으로 새 세그먼트(이벤트)를 만든다.
SEGMENT_GAP_SEC = 180

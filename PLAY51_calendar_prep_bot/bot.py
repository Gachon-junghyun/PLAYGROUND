"""PLAY51 개인 오케스트레이터 봇.

텔레그램 하나로 대화하되, 내부에 "세션"이 있다:
- 🧭 오케스트레이터: 기본 상태. 요청을 이해하고 도구를 써서 처리.
- 🔧 작업자(worker): 특정 작업(예: 캘린더 일정 준비)에 집중. /up 으로 오케스트레이터로 복귀.

캘린더 일정 1시간 전에 준비를 물어보고(인라인 버튼: 같이/혼자 진행/사용자가 진행/대기),
"혼자 진행"을 누르면 그 일정 전용 작업자 세션으로 전환된다.

도구는 tools/ 폴더의 플러그인(자세한 규격은 tools/__init__.py, 템플릿은 tools/_TEMPLATE.py).
LLM 은 무료 NVIDIA NIM API. 실행 엔진에 돈 안 든다.

    pip install caldav requests playwright openai
    python bot.py --list-events          # CalDAV 연결 확인
    python bot.py --test-telegram "hi"   # 텔레그램 연결 확인
    python bot.py --check-once           # 캘린더 체크 1회
    python bot.py                        # 상시 가동 (Ctrl+C 종료)
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

# Windows 콘솔(cp949) 한글 출력 깨짐 방지 (PLAY50 과 동일).
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).parent))  # tools 패키지 / list_events 의 `import bot` 위해
import tools as tool_loader  # noqa: E402

HERE = Path(__file__).parent
DB_PATH = HERE / "state.local.db"

# ── 튜닝 상수 ──
LEAD_TIME_HOURS = 1
CALENDAR_POLL_SECONDS = 15 * 60
SNOOZE_MINUTES = 20
LOOKAHEAD_HOURS = 6
CATCHUP_LOOKBACK_HOURS = 24
TELEGRAM_LONG_POLL_SECONDS = 25
AGENT_MAX_STEPS = 4        # 한 요청에서 도구 호출 반복 상한
HISTORY_KEEP = 10          # 세션별 대화 기록 유지 개수(메시지)
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_MODEL = "qwen/qwen3.5-122b-a10b"

# 세션별 대화 기록(메모리) — 재시작하면 초기화됨(README 에 명시).
HISTORIES = {"orchestrator": [], "worker": []}


# ── 시크릿 (환경변수 우선 → 옆 폴더 *.local.txt) ──
def load_secret(env_name, filename):
    val = os.environ.get(env_name)
    if val:
        return val.strip()
    p = HERE / filename
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    return None


# ── 상태 저장 ──
def db_connect():
    # busy timeout: 도구가 별도 커넥션으로 memory 를 쓸 때 '잠김' 예외를 줄인다.
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.execute("""CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uid TEXT UNIQUE, title TEXT, start_ts TEXT, notes TEXT,
        status TEXT, decision TEXT, snooze_until_ts TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS tg_offset (
        id INTEGER PRIMARY KEY CHECK (id = 1), offset INTEGER
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS session (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        mode TEXT,            -- orchestrator | worker
        task TEXT             -- worker 일 때 무슨 작업인지
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT,
        created_at TEXT
    )""")
    conn.commit()
    return conn


def get_session(conn):
    row = conn.execute("SELECT mode, task FROM session WHERE id=1").fetchone()
    if not row:
        conn.execute("INSERT INTO session (id, mode, task) VALUES (1, 'orchestrator', NULL)")
        conn.commit()
        return ("orchestrator", None)
    return row


def set_session(conn, mode, task=None):
    conn.execute("INSERT OR REPLACE INTO session (id, mode, task) VALUES (1, ?, ?)", (mode, task))
    conn.commit()


# ── 지속 기억 (비서의 첫 번째 덕목) ──
def mem_add(conn, content):
    content = (content or "").strip()
    if not content:
        return
    conn.execute("INSERT INTO memory (content, created_at) VALUES (?, ?)",
                 (content, datetime.now(timezone.utc).isoformat()))
    conn.commit()


def mem_all(conn, limit=60):
    rows = conn.execute("SELECT id, content FROM memory ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return list(reversed(rows))  # 오래된 것 → 최신 순


def mem_delete(conn, mem_id):
    cur = conn.execute("DELETE FROM memory WHERE id=?", (mem_id,))
    conn.commit()
    return cur.rowcount


def mem_block(conn, limit=60, max_chars=3000):
    rows = mem_all(conn, limit)
    if not rows:
        return "(아직 기억한 것 없음)"
    return "\n".join(f"#{rid}: {c}" for rid, c in rows)[:max_chars]


# ── iCloud CalDAV ──
def caldav_client():
    try:
        import caldav
    except ImportError:
        sys.exit("[!] caldav 미설치.  pip install caldav")
    icloud_id = load_secret("ICLOUD_ID", "icloud_id.local.txt")
    icloud_pw = load_secret("ICLOUD_APP_PASSWORD", "icloud_app_password.local.txt")
    if not icloud_id or not icloud_pw:
        sys.exit("[!] iCloud 계정 정보 없음. icloud_id.local.txt / icloud_app_password.local.txt 를 채우세요.\n"
                 "    앱 전용 암호: https://appleid.apple.com → 보안 → 앱 암호 생성")
    return caldav.DAVClient(url="https://caldav.icloud.com/", username=icloud_id, password=icloud_pw)


def fetch_upcoming_events(lookahead_hours=LOOKAHEAD_HOURS, lookback_hours=0):
    """[now-lookback, now+lookahead] 범위의 이벤트. lookback 은 트리거 시점 지났는데
    아직 못 보낸 이벤트를 잡기 위함(CalDAV 는 이미 끝난 이벤트를 안 돌려줌)."""
    client = caldav_client()
    principal = client.principal()
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=lookback_hours)
    until = now + timedelta(hours=lookahead_hours)
    events = []
    for cal in principal.calendars():
        try:
            results = cal.search(start=start, end=until, event=True, expand=True)
        except Exception as e:
            print(f"[캘린더 조회 실패, 건너뜀] {type(e).__name__}: {e}", flush=True)
            continue
        for ev in results:
            comp = ev.icalendar_component  # caldav 3.x: vobject 대신 icalendar
            uid = str(comp.get("uid", ev.url))
            title = str(comp.get("summary", "(제목 없음)"))
            start_dt = comp.get("dtstart").dt
            if isinstance(start_dt, datetime):
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
            else:
                start_dt = datetime.combine(start_dt, datetime.min.time()).replace(tzinfo=timezone.utc)
            notes = str(comp.get("description", "")).strip()
            events.append({"uid": uid, "title": title, "start": start_dt, "notes": notes})
    events.sort(key=lambda e: e["start"])
    return events


# ── 텔레그램 (raw HTTP) ──
def tg_call(method, request_timeout=30, **params):
    import requests
    token = load_secret("TG_BOT_TOKEN", "tg_bot_token.local.txt")
    if not token:
        sys.exit("[!] 텔레그램 봇 토큰 없음. tg_bot_token.local.txt 를 채우세요.")
    resp = requests.post(f"https://api.telegram.org/bot{token}/{method}", json=params, timeout=request_timeout)
    resp.raise_for_status()
    return resp.json()["result"]


def _chunks(text, n=4000):
    if not text:
        yield "(빈 응답)"
        return
    for i in range(0, len(text), n):
        yield text[i:i + n]


def tg_send_text(text, reply_markup=None):
    chat_id = load_secret("TG_CHAT_ID", "tg_chat_id.local.txt")
    if not chat_id:
        sys.exit("[!] 텔레그램 챗 ID 없음. tg_chat_id.local.txt 를 채우세요.")
    for chunk in _chunks(text):
        params = {"chat_id": chat_id, "text": chunk}
        if reply_markup:
            params["reply_markup"] = reply_markup
        tg_call("sendMessage", **params)


def tg_typing():
    """직관화: 입력 즉시 '입력 중…' 을 띄워 봇이 살아서 처리 중임을 알린다."""
    chat_id = load_secret("TG_CHAT_ID", "tg_chat_id.local.txt")
    try:
        tg_call("sendChatAction", chat_id=chat_id, action="typing")
    except Exception:
        pass


def tg_send_decision_buttons(event_row_id, text):
    keyboard = {"inline_keyboard": [[
        {"text": "같이", "callback_data": f"same:{event_row_id}"},
        {"text": "혼자 진행", "callback_data": f"alone:{event_row_id}"},
        {"text": "사용자가 진행", "callback_data": f"user:{event_row_id}"},
        {"text": "대기", "callback_data": f"wait:{event_row_id}"},
    ]]}
    tg_send_text(text, reply_markup=keyboard)


def tg_answer_callback(callback_query_id):
    """스피너 해제일 뿐 — 만료돼도 실제 버튼 로직은 계속돼야 한다."""
    try:
        tg_call("answerCallbackQuery", callback_query_id=callback_query_id)
    except Exception as e:
        print(f"[answerCallbackQuery 실패, 무시] {type(e).__name__}: {e}", flush=True)


def tg_get_updates(offset, poll_timeout=TELEGRAM_LONG_POLL_SECONDS):
    return tg_call("getUpdates", request_timeout=poll_timeout + 10, offset=offset, timeout=poll_timeout)


# ── NVIDIA NIM LLM ──
def _nvidia_client():
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("[!] openai SDK 없음.  pip install openai")
    key = load_secret("NVIDIA_API_KEY", "nvapi_key.local.txt")
    if not key:
        sys.exit("[!] NVIDIA_API_KEY 없음. nvapi_key.local.txt 를 채우세요.")
    return OpenAI(base_url=NVIDIA_BASE_URL, api_key=key, timeout=45, max_retries=0)


# LLM 이 타임아웃/실패했을 때 돌려주는 표식 — run_agent 가 사용자용 문구로 바꿔준다.
LLM_FAIL = "__LLM_FAIL__"


def ask_llm_messages(messages, max_tokens=700):
    """NVIDIA 는 (a) 가끔 빈 응답 (b) 무료티어 과부하 시 타임아웃 이 있음 — 둘 다 재시도.
    끝까지 실패하면 예외를 던지지 않고 LLM_FAIL 표식을 반환(봇이 죽지 않고 사용자에게 알리게)."""
    client = _nvidia_client()
    last_err = None
    for attempt in range(2):
        try:
            resp = client.chat.completions.create(
                model=NVIDIA_MODEL, messages=messages,
                temperature=0.4, top_p=0.9, max_tokens=max_tokens, stream=False,
            )
        except Exception as e:
            last_err = e
            print(f"[LLM 호출 실패 {attempt + 1}/2] {type(e).__name__}: {e}", flush=True)
            continue
        msg = resp.choices[0].message
        text = (msg.content or "").strip()
        reasoning = (getattr(msg, "reasoning_content", None) or "").strip()
        out = text or reasoning
        if out:
            return out
        print(f"[LLM 빈 응답 {attempt + 1}/2]", flush=True)
    return f"{LLM_FAIL}: {type(last_err).__name__ if last_err else '빈응답'}"


def ask_llm(prompt, max_tokens=500):
    return ask_llm_messages([{"role": "user", "content": prompt}], max_tokens=max_tokens)


# ── 에이전트 루프 (오케스트레이터 / 작업자 공용) ──
TOOL_CALL_RE = re.compile(r"CALL\s+([A-Za-z0-9_]+)[ \t]*(.*)", re.DOTALL)


def parse_tool_call(reply, tools):
    """LLM 응답에서 도구 호출을 관대하게 파싱. 반환 (name, args, mod) 또는 None.
    지원 형태: CALL name {"k":"v"}  /  CALL name "문자열"  /  CALL name 값
    (모델이 JSON 규약을 자주 안 지켜서, 맨 문자열/숫자면 도구의 첫 인자에 매핑한다.)"""
    m = TOOL_CALL_RE.search(reply.strip())
    if not m:
        return None
    name = m.group(1)
    if name not in tools:
        return None
    mod = tools[name]
    rest = m.group(2).strip()
    args = {}
    if rest.startswith("{"):
        try:
            parsed = json.loads(rest)
            if isinstance(parsed, dict):
                args = {str(k): str(v) for k, v in parsed.items()}
        except Exception:
            args = {}
    if not args and rest:
        val = rest.strip().strip("`").strip()
        if len(val) >= 2 and val[0] in "\"'" and val[-1] == val[0]:
            val = val[1:-1]
        params = list(mod.META.get("params", {}).keys())
        args = {params[0]: val} if params else {}
    return name, args, mod


# 좋은 비서의 덕목 — 모든 에이전트 턴 system 프롬프트에 공통 주입.
ASSISTANT_PRINCIPLES = (
    "너는 유능한 개인 비서다. 다음 원칙을 지켜라:\n"
    "1) 아래 [기억]을 적극 활용해 부족한 정보를 메꿔라. 일정에 단어 몇 개뿐이어도, 기억과 제목으로 "
    "무슨 뜻인지 추론해서 '일단 진행'하라. 되묻는 건 최후의 수단.\n"
    "2) 추론/추정한 부분은 '(추정)'처럼 짧게 표시하되, 없는 사실을 지어내지는 마라.\n"
    "3) 사용자가 '기억해/참고해둬' 하거나, 앞으로 또 쓸 사실(사람·프로젝트·선호·약칭 등)을 알게 되면 "
    "remember 도구로 저장하라.\n"
    "4) 간결하게, 중요한 것부터. 장황한 설명 금지.\n"
    "5) 정말 정보가 없어 막힐 때만, 딱 하나의 핵심 질문을 던져라."
)


def run_agent(conn, system_prompt, history, user_text):
    """LLM 이 필요하면 도구를 부르고(ReAct-lite), 최종 답을 문자열로 반환.
    conn: 기억 주입용. 도구 호출 규약: 답 대신 딱 한 줄 `CALL <도구> {"인자":"값"}`."""
    tools = tool_loader.discover()
    cat = tool_loader.catalog(tools)
    now_kst = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M (KST, %a)")
    sys_full = (
        system_prompt
        + "\n\n" + ASSISTANT_PRINCIPLES
        + f"\n\n[현재 시각] {now_kst} — '오늘/내일/급한 것' 판단은 이 시각 기준으로."
        + "\n\n[기억하고 있는 것들]\n" + mem_block(conn)
        + "\n\n[쓸 수 있는 도구]\n" + cat
        + "\n\n도구가 필요하면 다른 말 없이 딱 한 줄로만 출력해:\n"
          'CALL <도구이름> {"인자": "값"}\n'
        "도구 결과를 받으면 그걸 근거로 사용자에게 자연스러운 한국어로 답해. "
        "도구가 필요 없으면 바로 답해."
    )
    msgs = [{"role": "system", "content": sys_full}] + history[-HISTORY_KEEP:] + \
           [{"role": "user", "content": user_text}]

    reply = ""
    last_obs = None
    for step in range(AGENT_MAX_STEPS):
        reply = ask_llm_messages(msgs, max_tokens=700)
        if reply.startswith(LLM_FAIL):
            break
        call = parse_tool_call(reply, tools)
        if not call:
            break
        name, args, mod = call
        argstr = ", ".join(f"{k}={v}" for k, v in args.items())
        print(f"[에이전트] step{step}: 도구 {name}({argstr})", flush=True)
        tg_send_text(f"🔧 도구 실행: {name}({argstr})")
        tg_typing()
        try:
            last_obs = mod.run(**args)
        except Exception as e:
            last_obs = f"[도구 실행 오류] {type(e).__name__}: {e}"
        msgs.append({"role": "assistant", "content": reply})
        msgs.append({"role": "user",
                     "content": f"도구 결과:\n{last_obs}\n\n이미 도구 결과를 받았으니 또 부르지 말고 "
                                "이 결과로 사용자에게 바로 답해."})

    # LLM 이 끝내 실패하면 사용자용 안내로 치환.
    if reply.startswith(LLM_FAIL):
        reply = ("⚠ 지금 무료 LLM(NVIDIA) 응답이 지연/실패하고 있어요(과부하로 추정). "
                 "잠시 후 다시 말 걸어주세요.")
    # 폴백: 도구 결과는 있는데 최종 답이 비거나 아직도 CALL 만 뱉으면, 도구 결과로 강제 요약 1회.
    elif last_obs is not None and (not reply.strip() or TOOL_CALL_RE.search(reply.strip())):
        reply = ask_llm_messages([
            {"role": "system", "content": "아래 자료를 바탕으로 사용자에게 간결한 한국어로 답하라. 도구 호출 금지."},
            {"role": "user", "content": f"질문: {user_text}\n\n자료:\n{last_obs}"},
        ], max_tokens=700)
        if reply.startswith(LLM_FAIL):
            reply = f"(LLM 요약 실패 — 원본 도구 결과)\n{last_obs[:1500]}"

    # 도구 호출 흔적은 빼고, 사용자 발화 + 최종 답만 기록에 남긴다.
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": reply})
    del history[:-HISTORY_KEEP]
    return reply


# ── 캘린더 체크 → 알림 ──
def check_calendar_and_notify():
    conn = db_connect()
    now = datetime.now(timezone.utc)
    try:
        events = fetch_upcoming_events(lookback_hours=CATCHUP_LOOKBACK_HOURS)
    except SystemExit:
        raise
    except Exception as e:
        print(f"[캘린더 체크 실패] {type(e).__name__}: {e}", flush=True)
        conn.close()
        return

    fired = 0
    for ev in events:
        if now < ev["start"] - timedelta(hours=LEAD_TIME_HOURS):
            continue
        row = conn.execute("SELECT id, status, snooze_until_ts FROM events WHERE uid=?", (ev["uid"],)).fetchone()
        if row is None:
            cur = conn.execute(
                "INSERT INTO events (uid, title, start_ts, notes, status) VALUES (?,?,?,?,?)",
                (ev["uid"], ev["title"], ev["start"].isoformat(), ev["notes"], "pending"),
            )
            conn.commit()
            row_id, status, snooze_until = cur.lastrowid, "pending", None
        else:
            row_id, status, snooze_until = row

        if status in ("awaiting_decision", "awaiting_notes", "working", "done", "expired"):
            continue
        if snooze_until and now < datetime.fromisoformat(snooze_until):
            continue
        if now >= ev["start"]:
            conn.execute("UPDATE events SET status='expired' WHERE id=?", (row_id,))
            conn.commit()
            continue

        _notify_event(conn, row_id, ev)
        fired += 1

    conn.close()
    print(f"[체크 완료] 이벤트 {len(events)}개 중 {fired}개 알림", flush=True)


def _propose_prep(conn, title, notes):
    """일정 준비 제안 생성. 메모가 부실해도 [기억]과 제목으로 추론해서 진행한다(비서 덕목)."""
    return ask_llm(
        ASSISTANT_PRINCIPLES
        + "\n\n[기억하고 있는 것들]\n" + mem_block(conn)
        + f"\n\n다가오는 일정 — 제목: {title}\n메모: {notes or '(없음)'}\n\n"
        "이 일정 준비로 뭘 하면 좋을지 2~3문장으로 제안해줘. 메모가 부실하면 위 기억과 제목으로 "
        "무슨 일정인지 추론해서 제안하되, 추정한 부분은 '(추정)'으로 짧게 표시. 한국어로."
    )


def _notify_event(conn, row_id, ev):
    # 메모가 없어도 되묻지 않고, 기억+제목으로 추론해 '일단' 제안+버튼을 낸다(비서 덕목).
    proposal = _propose_prep(conn, ev["title"], ev["notes"])
    memo = ev["notes"] if ev["notes"] else "(없음 — 제목+기억으로 추정)"
    tg_send_decision_buttons(row_id,
        f"\U0001F514 {ev['title']} — {LEAD_TIME_HOURS}시간 후 시작\n"
        f"메모: {memo}\n\n제안: {proposal}\n\n어떻게 할까요?")
    conn.execute("UPDATE events SET status='awaiting_decision' WHERE id=?", (row_id,))
    conn.commit()


def _open_worker_for_event(conn, row_id, title, notes):
    set_session(conn, "worker", title)
    HISTORIES["worker"] = []
    conn.execute("UPDATE events SET status='working', decision='alone' WHERE id=?", (row_id,))
    conn.commit()
    tg_send_text(f"🔧 '{title}' 준비 작업자로 전환했어요. 지금부터 이 작업 얘기를 하면 돼요. (/up 으로 나가기)")
    tg_typing()
    sysp = (f"너는 '{title}' 일정 준비를 돕는 작업자(worker) 에이전트다. 메모: {notes or '(없음)'}. "
            "이 작업에만 집중해서 실용적으로 준비를 도와라. 필요하면 web_search 도구로 최신 정보를 찾아라.")
    reply = run_agent(conn, sysp, HISTORIES["worker"], f"이 일정 준비를 시작하자. 제목: {title}. 메모: {notes or '(없음)'}")
    tg_send_text(f"🔧 [{title}]\n{reply}\n\n(/up 으로 오케스트레이터로)")


# 명시적 '기억해줘'는 LLM 도구호출에 맡기면 자주 놓쳐서(말만 하고 저장 안 함),
# 키워드로 결정론적으로 잡아 확실히 저장한다.
MEM_INTENT = ("기억해", "기억 해", "기억해둬", "기억해 둬", "기억해줘", "기억 해줘",
              "참고해둬", "참고해 둬", "잊지마", "잊지 마", "메모해둬", "기억할")


def maybe_remember(conn, text):
    """발화에 기억 의도가 있으면 핵심 사실을 뽑아 저장하고 True. (LLM 실패 시 원문 저장)"""
    if not any(k in text for k in MEM_INTENT):
        return False
    tg_typing()
    fact = ask_llm(
        "다음 사용자 발화에서 '앞으로 계속 기억해둘 핵심 사실'만 군더더기 없이 뽑아줘. "
        "설명·인사 없이 사실만 (한 문장이나 짧은 항목).\n발화: " + text, max_tokens=200)
    if fact.startswith(LLM_FAIL) or not fact.strip():
        fact = text  # 폴백: 원문 저장
    fact = fact.strip()
    mem_add(conn, fact)
    tg_send_text(f"🧠 기억했어요:\n{fact}")
    print(f"[기억 저장] {fact[:80]!r}", flush=True)
    return True


# ── 텔레그램 업데이트 처리 ──
def handle_command(conn, text):
    cmd = text.split()[0].lower()
    mode, task = get_session(conn)
    if cmd == "/up":
        set_session(conn, "orchestrator", None)
        HISTORIES["worker"] = []
        tg_send_text("🧭 오케스트레이터로 돌아왔어요.")
    elif cmd == "/who":
        if mode == "worker":
            tg_send_text(f"🔧 지금 '작업자'와 대화 중 — 작업: {task}\n(/up 으로 오케스트레이터 복귀)")
        else:
            tg_send_text("🧭 지금 '오케스트레이터'와 대화 중")
    elif cmd == "/tools":
        tg_send_text("등록된 도구:\n" + tool_loader.catalog(tool_loader.discover()))
    elif cmd == "/reload":
        tools = tool_loader.discover()
        tg_send_text(f"도구 {len(tools)}개 리로드됨:\n" + tool_loader.catalog(tools))
    elif cmd == "/memories":
        rows = mem_all(conn)
        if not rows:
            tg_send_text("아직 기억한 게 없어요. '이거 기억해줘' 하고 말해보세요.")
        else:
            tg_send_text("🧠 기억하고 있는 것들:\n" + "\n".join(f"#{i}: {c}" for i, c in rows)
                         + "\n\n(지우려면 /forget <번호>)")
    elif cmd == "/forget":
        parts = text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            tg_send_text("사용법: /forget <번호>  (번호는 /memories 에서 확인)")
        else:
            n = mem_delete(conn, int(parts[1]))
            tg_send_text(f"#{parts[1]} 잊었어요." if n else f"#{parts[1]} 은(는) 없어요.")
    elif cmd in ("/start", "/help"):
        tg_send_text("개인 비서 봇 🧭\n"
                     "- 그냥 말하면 처리해요 (필요하면 도구 사용)\n"
                     "- '이거 기억해줘' → 기억해서 다음부터 알아서 참고\n"
                     "- /memories  기억 목록  ·  /forget <번호>  기억 삭제\n"
                     "- /who  지금 누구랑 대화 중인지\n"
                     "- /tools  도구 목록  ·  /reload  도구 새로고침\n"
                     "- /up  작업자에서 오케스트레이터로 복귀")
    else:
        tg_send_text(f"모르는 명령: {cmd}  (/help 참고)")


def handle_update(conn, update):
    if "callback_query" in update:
        cq = update["callback_query"]
        tg_answer_callback(cq["id"])
        action, _, row_id = cq.get("data", "").partition(":")
        if not row_id:
            return
        row = conn.execute("SELECT id, title, notes FROM events WHERE id=?", (row_id,)).fetchone()
        if row is None:
            return
        _, title, notes = row

        if action == "same":
            tg_send_text(f"알겠습니다 — '{title}' 은 같이 진행할게요. 준비되면 말씀해주세요.")
            conn.execute("UPDATE events SET status='done', decision='same' WHERE id=?", (row_id,))
            conn.commit()
        elif action == "alone":
            _open_worker_for_event(conn, row_id, title, notes)
            conn.execute("UPDATE events SET status='done' WHERE id=?", (row_id,))
            conn.commit()
        elif action == "user":
            tg_send_text(f"넵, '{title}' 은 직접 준비하시는 걸로 알겠습니다.")
            conn.execute("UPDATE events SET status='done', decision='user' WHERE id=?", (row_id,))
            conn.commit()
        elif action == "wait":
            snooze_until = (datetime.now(timezone.utc) + timedelta(minutes=SNOOZE_MINUTES)).isoformat()
            conn.execute("UPDATE events SET status='pending', decision='wait', snooze_until_ts=? WHERE id=?",
                         (snooze_until, row_id))
            conn.commit()
            tg_send_text(f"{SNOOZE_MINUTES}분 뒤에 다시 물어볼게요.")
        return

    if "message" not in update or "text" not in update.get("message", {}):
        return
    text = update["message"]["text"].strip()
    print(f"[메시지 수신] {text[:80]!r}", flush=True)

    if text.startswith("/"):
        handle_command(conn, text)
        return

    # 명시적 '기억해줘'는 결정론적으로 먼저 처리 (LLM 도구호출 신뢰 안 함)
    if maybe_remember(conn, text):
        return

    # 일반 대화 → 현재 세션(오케스트레이터/작업자)으로 라우팅
    mode, task = get_session(conn)
    # 직관화: 입력 즉시(느린 LLM 호출 '전에') 구체적 접수 메시지 + typing 을 보낸다.
    if mode == "worker":
        tg_send_text(f"🔧 [{task}] 받았어요 — 작업 중… 🤔")
    else:
        tg_send_text("🧭 받았어요 — 처리 중… 🤔 (필요하면 도구 실행할게요)")
    tg_typing()
    if mode == "worker":
        sysp = (f"너는 '{task}' 작업을 돕는 작업자(worker) 에이전트다. 이 작업에 집중해서 실용적으로 도와라. "
                "필요하면 web_search 도구로 최신 정보를 찾아라.")
        reply = run_agent(conn, sysp, HISTORIES["worker"], text)
        tg_send_text(f"🔧 [{task}]\n{reply}\n\n(/up 으로 오케스트레이터로)")
    else:
        sysp = ("너는 사용자의 개인 오케스트레이터(비서)다. 요청을 이해하고, 필요하면 도구를 써서 처리하고, "
                "간결한 한국어로 답하라.")
        reply = run_agent(conn, sysp, HISTORIES["orchestrator"], text)
        tg_send_text(f"🧭 {reply}")


# ── 상시 가동 루프 ──
def run_forever():
    conn = db_connect()
    row = conn.execute("SELECT offset FROM tg_offset WHERE id=1").fetchone()
    offset = row[0] if row else 0
    last_check = 0.0
    mode, task = get_session(conn)
    print(f"[가동 시작] mode={mode} task={task}  (Ctrl+C 종료)", flush=True)
    tg_send_text("🧭 봇 가동됨. /help 로 사용법, 아무 말이나 하면 처리해요.")
    while True:
        try:
            updates = tg_get_updates(offset)
            for u in updates:
                try:
                    handle_update(conn, u)
                except Exception as e:
                    # 한 메시지 처리 실패가 봇을 멈추거나 조용히 사라지지 않게 — 사용자에게 알린다.
                    print(f"[처리 오류] {type(e).__name__}: {e}", flush=True)
                    try:
                        tg_send_text(f"⚠ 처리 중 오류가 났어요: {type(e).__name__}. 다시 시도해주세요.")
                    except Exception:
                        pass
                offset = u["update_id"] + 1
                conn.execute("INSERT OR REPLACE INTO tg_offset (id, offset) VALUES (1, ?)", (offset,))
                conn.commit()
            if time.time() - last_check > CALENDAR_POLL_SECONDS:
                check_calendar_and_notify()
                last_check = time.time()
        except KeyboardInterrupt:
            print("[종료]", flush=True)
            break
        except Exception as e:
            print(f"[루프 에러, 계속] {type(e).__name__}: {e}", flush=True)
            time.sleep(5)


def main():
    ap = argparse.ArgumentParser(description="iCloud 캘린더 + 텔레그램 개인 오케스트레이터 봇")
    ap.add_argument("--list-events", action="store_true", help="CalDAV 연결 확인 후 향후 일정 나열")
    ap.add_argument("--hours", type=int, default=LOOKAHEAD_HOURS, help="--list-events 조회 범위(시간)")
    ap.add_argument("--test-telegram", metavar="TEXT", help="텔레그램 메시지 1회 발송 후 종료")
    ap.add_argument("--check-once", action="store_true", help="캘린더 체크 1회 후 종료")
    args = ap.parse_args()

    if args.list_events:
        events = fetch_upcoming_events(lookahead_hours=args.hours)
        if not events:
            print("(향후 일정 없음)")
        for ev in events:
            flag = "[메모 있음]" if ev["notes"] else "[메모 없음]"
            print(f"- {ev['start'].isoformat()}  {ev['title']}  {flag}")
    elif args.test_telegram is not None:
        tg_send_text(args.test_telegram)
        print("전송 완료", flush=True)
    elif args.check_once:
        check_calendar_and_notify()
    else:
        run_forever()


if __name__ == "__main__":
    main()

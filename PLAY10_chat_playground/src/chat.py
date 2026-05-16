"""
PLAY10 — Gradio 챗 UI (튠 모델 vs 베이스 사이드바이사이드 + ㅋㅋㅋ 데이터 수집).

좌측 패널: PLAY9 학습된 LoRA 어댑터 (Korean microstyle).
우측 패널: 동일 base Gemma 4 E2B (어댑터 disable로 raw 응답).
사용자 메시지에 ㅋ 3개 이상 연속이면 → 그 패널의 직전 3 메시지를
data/collected_kkkk.jsonl 에 append.

실행:
  $env:PYTHONUTF8 = "1"
  python -u src/chat.py
  → 브라우저에서 http://localhost:7860 열림
"""
from __future__ import annotations
import datetime as dt
import io
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ADAPTER_DIR = ROOT / "adapter"
COLLECTED_PATH = DATA / "collected_kkkk.jsonl"

SYSTEM_PROMPT = (
    "너는 친구의 톡을 받고 머릿속으로 어떻게 답할지 한 번 굴린 뒤 답하는 한국어 화자다. "
    "먼저 <think>...</think> 안에 자연스러운 자기 사고를 적고, 그 뒤에 실제 답 한 줄만 보낸다. "
    "진지 신호(죽음·이별·우울·해고·강한 자기비하)가 보이면 비유·받아치기·펀치라인은 사용하지 않는다."
)

KKK_REGEX = re.compile(r"ㅋ{3,}")


def has_kkk(text: str) -> bool:
    return bool(KKK_REGEX.search(text or ""))


def split_think_reply(gen: str) -> tuple[str, str]:
    """모델 출력에서 think 블록과 답변을 분리. 못 찾으면 (전체, "")."""
    if "<think>" in gen and "</think>" in gen:
        th = gen.split("<think>", 1)[1].split("</think>", 1)[0].strip()
        rp = gen.split("</think>", 1)[1].strip()
        return th, rp
    return "", gen.strip()


def format_for_display(gen: str) -> str:
    """채팅창 표시용. think + 답변 같이 보이게."""
    th, rp = split_think_reply(gen)
    if th:
        return f"🧠 *{th}*\n\n💬 **{rp}**"
    return gen


def capture_kkk(history: list[dict], trigger_msg: str, model_label: str) -> None:
    """ㅋㅋㅋ 감지 시 직전 3 메시지 + trigger를 jsonl로 append."""
    DATA.mkdir(exist_ok=True)
    # history는 ㅋㅋㅋ 발화 직전까지의 turn 리스트. 마지막 3 메시지 잡음.
    last3 = history[-3:] if len(history) >= 3 else history[:]
    # display용 think/reply 합체를 raw로 되돌릴 수 없으니, 그대로 저장.
    row = {
        "model": model_label,
        "trigger": trigger_msg,
        "captured_at": dt.datetime.now().isoformat(timespec="seconds"),
        "messages": last3,
    }
    with io.open(COLLECTED_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[KKK] captured ({model_label}, n={len(last3)}) → {COLLECTED_PATH}", flush=True)


# ============================================================
# 모델 로딩 (한 번만, base 공유 + adapter 토글)
# ============================================================
print("[load] starting…", flush=True)
from unsloth import FastModel
from unsloth.chat_templates import get_chat_template
import torch

model, tokenizer = FastModel.from_pretrained(
    model_name=str(ADAPTER_DIR),       # adapter 디렉토리 → unsloth가 base 자동 추론
    max_seq_length=1536,
    load_in_4bit=True,
    full_finetuning=False,
    dtype=None,
)
tokenizer = get_chat_template(tokenizer, chat_template="gemma-4")
FastModel.for_inference(model)
print(f"[load] ready. adapter dir: {ADAPTER_DIR}", flush=True)


def generate_stream(messages: list[dict], use_adapter: bool,
                    max_new_tokens: int = 150):
    """토큰 단위로 yield. Gradio가 받으면 실시간 streaming 표시.
    속도 우선: greedy decoding(do_sample=False) + max_new_tokens=150."""
    from transformers import TextIteratorStreamer
    from threading import Thread

    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text=prompt, return_tensors="pt").to(model.device)

    streamer = TextIteratorStreamer(
        tokenizer, skip_special_tokens=True, skip_prompt=True, timeout=120.0)
    gen_kwargs = dict(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,                       # greedy (빠름 + 결정적)
        pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
        streamer=streamer,
    )

    def _run():
        if use_adapter:
            with torch.no_grad():
                model.generate(**gen_kwargs)
        else:
            with model.disable_adapter():
                with torch.no_grad():
                    model.generate(**gen_kwargs)

    Thread(target=_run, daemon=True).start()

    acc = ""
    for tok in streamer:
        acc += tok
        yield acc


# ============================================================
# Gradio UI
# ============================================================
import gradio as gr


def respond(message: str, history: list, use_adapter: bool,
            model_label: str):
    """
    Gradio generator (yield). 토큰씩 흘러나오면 chat이 실시간 업데이트.
    history: Gradio Chatbot의 history (tuples 형식 또는 messages dict — 둘 다 호환되게).
    """
    history = list(history) if history else []

    # 1. ㅋㅋㅋ 감지 → 현재 history(아직 message 들어가기 전) 캡처
    if has_kkk(message):
        capture_kkk(history, message, model_label)

    # 2. history를 messages 형식으로 normalize (모델 입력용)
    convo = [{"role": "system", "content": SYSTEM_PROMPT}]
    for entry in history:
        if isinstance(entry, dict):
            convo.append(entry)
        elif isinstance(entry, (list, tuple)) and len(entry) == 2:
            # tuples 형식 [user, bot]
            if entry[0]:
                convo.append({"role": "user", "content": entry[0]})
            if entry[1]:
                # bot 메시지는 display용 (sigil 포함) — raw로 변환 시도
                convo.append({"role": "assistant", "content": entry[1]})
    convo.append({"role": "user", "content": message})

    # 3. user 메시지 화면 즉시 표시 (Gradio 6: messages dict 형식)
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ""})
    yield "", history

    # 4. streaming generate
    acc = ""
    for partial in generate_stream(convo, use_adapter=use_adapter):
        acc = partial
        history[-1]["content"] = format_for_display(acc)
        yield "", history

    # 5. 최종 정리 (think/reply 분리 표시)
    history[-1]["content"] = format_for_display(acc)
    yield "", history


def respond_tuned(message: str, history: list):
    yield from respond(message, history, use_adapter=True, model_label="tuned")


def respond_base(message: str, history: list):
    yield from respond(message, history, use_adapter=False, model_label="base")


def clear_both() -> tuple[list, list]:
    return [], []


with gr.Blocks(title="PLAY10 — Korean Microstyle Chat") as demo:
    gr.Markdown(
        "# 🎯 PLAY10 — 튠 vs 베이스 + ㅋㅋㅋ 데이터 수집\n"
        "양쪽 패널 독립 대화. **ㅋ 3개 이상**(예: `ㅋㅋㅋ`) 입력하면 직전 3 메시지가\n"
        f"`{COLLECTED_PATH}` 에 자동 저장됨."
    )

    with gr.Row():
        with gr.Column():
            gr.Markdown("### 🎓 튠 모델 (PLAY9 어댑터)")
            chat_tuned = gr.Chatbot(height=520)
            input_tuned = gr.Textbox(
                placeholder="튠 모델에게 보내기… (예: 나 오늘 발표 망한 듯)",
                show_label=False,
            )
        with gr.Column():
            gr.Markdown("### 🤖 베이스 모델 (raw Gemma 4 E2B)")
            chat_base = gr.Chatbot(height=520)
            input_base = gr.Textbox(
                placeholder="베이스에게 보내기…",
                show_label=False,
            )

    with gr.Row():
        clear_btn = gr.Button("🗑️ 양쪽 다 지우기")

    input_tuned.submit(respond_tuned, [input_tuned, chat_tuned],
                       [input_tuned, chat_tuned])
    input_base.submit(respond_base, [input_base, chat_base],
                      [input_base, chat_base])
    clear_btn.click(clear_both, outputs=[chat_tuned, chat_base])


if __name__ == "__main__":
    print("[gradio] launching…", flush=True)
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False,
                inbrowser=True)

"""도구 플러그인 로더.

이 폴더(`tools/`)에 `<이름>.py` 파일을 두고 그 안에 `META`(dict)와 `run`(함수)만 있으면
봇이 자동으로 도구로 등록한다. Claude Code 가 새 기능을 붙일 땐 `_TEMPLATE.py` 를 복사해
채우고 저장 → 봇에서 `/reload` 만 하면 바로 붙는다. (봇 재시작 불필요.)

규칙:
- 파일명 = 도구 이름(영문 snake_case). `_` 로 시작하는 파일과 `__init__.py` 는 무시.
- `run(**kwargs) -> str` : 인자는 전부 문자열로 들어온다(오케스트레이터 LLM 이 문자열로 넘김).
  반환도 문자열(사람이/LLM 이 읽을 결과).
- 무거운 import 는 `run` 안에서 lazy 로. (import tools 만으로 playwright 등이 안 끌려오게)
"""
import importlib.util
import pathlib

TOOLS_DIR = pathlib.Path(__file__).parent


def discover():
    """{도구이름: module} 반환. 매 호출마다 파일을 다시 읽어 핫리로드를 지원한다."""
    found = {}
    for path in sorted(TOOLS_DIR.glob("*.py")):
        if path.stem.startswith("_") or path.stem == "__init__":
            continue
        spec = importlib.util.spec_from_file_location(f"_tool_{path.stem}", path)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            print(f"[도구 로드 실패 {path.name}] {type(e).__name__}: {e}", flush=True)
            continue
        meta = getattr(mod, "META", None)
        run = getattr(mod, "run", None)
        if not isinstance(meta, dict) or "name" not in meta or not callable(run):
            print(f"[도구 형식 오류 {path.name}] META/run 규격 불충족 — 건너뜀", flush=True)
            continue
        found[meta["name"]] = mod
    return found


def catalog(mods):
    """LLM 프롬프트에 넣을 도구 카탈로그 문자열."""
    if not mods:
        return "(등록된 도구 없음)"
    lines = []
    for name, mod in mods.items():
        m = mod.META
        params = ", ".join(f"{k}({v})" for k, v in m.get("params", {}).items()) or "없음"
        lines.append(f"- {name}: {m['description']} | 인자: {params}")
    return "\n".join(lines)

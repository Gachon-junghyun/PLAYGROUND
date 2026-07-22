"""실행 중인 서버에 더미 배치를 보내 손으로 검증하는 헬퍼.

사용:
    $env:HINDSIGHT_TOKEN = "..."
    python send_dummy.py                       # http://localhost:8000
    python send_dummy.py http://100.118.139.82:8000  # Tailscale IP
"""
import os
import sys
import time

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
H = {"Authorization": f"Bearer {os.environ.get('HINDSIGHT_TOKEN', '')}"}
now = int(time.time())

batch = [
    {"ts": now - 3600, "front_app": "KakaoTalk", "visible_apps": ["KakaoTalk"], "source": "ocr",
     "client_capture_id": 91001,
     "lines": [{"text": "수산나: 오늘 저녁에 시간 돼?", "x": 0.1, "y": 0.8, "w": 0.6, "h": 0.03}]},
    {"ts": now - 1800, "front_app": "Claude", "visible_apps": ["Claude"], "source": "ocr",
     "client_capture_id": 91002,
     "lines": [{"text": "def insert_capture_batch(captures): error traceback git commit",
                "x": 0.1, "y": 0.7, "w": 0.7, "h": 0.03}]},
    {"ts": now - 900, "front_app": "Microsoft Word", "visible_apps": ["Microsoft Word"], "source": "ocr",
     "client_capture_id": 91003,
     "lines": [{"text": "Example 6.17 지수분포 확률 정답 0.2666", "x": 0.1, "y": 0.6, "w": 0.5, "h": 0.03}]},
    {"ts": now - 120, "front_app": "Google Chrome", "visible_apps": ["Google Chrome"], "source": "ocr",
     "client_capture_id": 91004,
     "lines": [{"text": "받은편지함 (3) - Gmail 결제 영수증", "x": 0.1, "y": 0.9, "w": 0.5, "h": 0.03}]},
    # 같은 카톡 내용을 '나중에 다시 봄' → 과거 링크/재열람으로 잡혀야 함
    {"ts": now - 30, "front_app": "KakaoTalk", "visible_apps": ["KakaoTalk"], "source": "ocr",
     "client_capture_id": 91005,
     "lines": [{"text": "수산나: 오늘 저녁에 시간 돼?", "x": 0.1, "y": 0.8, "w": 0.6, "h": 0.03}]},
]

print("POST /captures   ->", requests.post(f"{BASE}/captures", json=batch, headers=H).json())
print("재전송(멱등)     ->", requests.post(f"{BASE}/captures", json=batch, headers=H).json())
print("GET  /health     ->", requests.get(f"{BASE}/health", headers=H).json())
print("GET  /breakdown  ->", requests.get(f"{BASE}/breakdown", headers=H).json())
print("GET  /search 수산나 ->", requests.get(f"{BASE}/search", params={"q": "수산나"}, headers=H).json())
print("GET  /timeline 바이브코딩 ->",
      requests.get(f"{BASE}/timeline", params={"topic": "바이브코딩"}, headers=H).json())
print("GET  /history 수산나 ->", requests.get(f"{BASE}/history", params={"q": "수산나"}, headers=H).json())

#!/usr/bin/env bash
# OSINT 자가점검 러너. holehe(이메일) + maigret(닉네임)을 순서대로 돌리고
# 원시 출력을 results/에 저장한다. 본인 소유 계정 자가점검 전용.
set +e
cd "$(dirname "$0")"
mkdir -p results
export PATH="/c/Users/fivep/AppData/Roaming/Python/Python311/Scripts:$PATH"
# Windows 콘솔 기본 인코딩(cp949)에서 maigret 진행바 블록문자(▁█)가
# UnicodeEncodeError로 죽는다 → utf-8 강제 + 진행바 끄기로 회피.
export PYTHONIOENCODING=utf-8

EMAILS=("fivepeople201@gmail.com" "fourpeople201@gmail.com")
HANDLES=("fivepeople201" "fourpeople201")

echo "### holehe (이메일 가입여부) ###"
for e in "${EMAILS[@]}"; do
  echo ">>> holehe $e"
  holehe "$e" --only-used --no-color > "results/holehe_${e%@*}.txt" 2>&1
  echo "    exit=$? -> results/holehe_${e%@*}.txt"
done

echo "### maigret (닉네임 SNS 탐색) ###"
for h in "${HANDLES[@]}"; do
  echo ">>> maigret $h"
  maigret "$h" --top-sites 500 --timeout 15 --retries 1 \
    --html --json simple --folderoutput results \
    --no-color --no-progressbar > "results/maigret_${h}.txt" 2>&1
  echo "    exit=$? -> results/maigret_${h}.txt"
done

echo "ALL_DONE"

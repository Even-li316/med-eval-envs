#!/usr/bin/env python3
"""CI 闸门：任何任务的可复现项不过，直接 fail。"""
import json
import sys

ok = True
for task in ("eeg", "oct"):
    with open(f"results/{task}_baseline.json", encoding="utf-8") as f:
        d = json.load(f)
    print(f"{task}: replay_ok={d['replay_ok']} digest={d['digest']} score={d['score_mean']}")
    ok = ok and bool(d["replay_ok"])
print("REPLAY GATE:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)

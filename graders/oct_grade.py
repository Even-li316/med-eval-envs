#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""评分器：OCT 分层边界定位（只吃预测 + 真值，可离线复算）

判据
  G1 命中率：预测边界与真值边界的最近距离 ≤ TOL_PX 即算命中（一对一匹配）
  G2 漏检率：未命中的真值层 / 真值层总数 ≤ MISS_MAX
  G3 误检率：未匹配的预测 / 预测总数 ≤ FALSE_MAX
  G4 可复现：一票否决
"""
from __future__ import annotations

import json

TOL_PX = 3          # ±9 µm（UM_PER_PX = 3 µm）
MISS_MAX = 0.10
FALSE_MAX = 0.10


def _match(preds, truths, tol=TOL_PX):
    """贪心一对一匹配，返回 (matches, missed_truth, false_pred)。"""
    used = set()
    matches = []
    for t in truths:
        best, bd = None, None
        for i, p in enumerate(preds):
            if i in used:
                continue
            d = abs(p - t)
            if d <= tol and (bd is None or d < bd):
                best, bd = i, d
        if best is not None:
            used.add(best)
            matches.append((t, preds[best], bd))
    missed = [t for t in truths if not any(m[0] == t for m in matches)]
    false = [p for i, p in enumerate(preds) if i not in used]
    return matches, missed, false


def grade(pred: dict, truth: dict, replay_ok: bool = True) -> dict:
    preds = [float(x) for x in pred.get("depths_px", [])]
    truths = [float(x) for x in truth["depths_px"]]
    matches, missed, false = _match(preds, truths)

    hit_rate = len(matches) / max(1, len(truths))
    miss_rate = len(missed) / max(1, len(truths))
    false_rate = len(false) / max(1, len(preds)) if preds else 1.0
    g1 = hit_rate >= 0.9
    g2 = miss_rate <= MISS_MAX
    g3 = false_rate <= FALSE_MAX

    score = 100.0 * (0.5 * hit_rate + 0.25 * (1 - miss_rate) + 0.25 * (1 - false_rate))
    if not replay_ok:
        score = 0.0

    return {
        "score": round(score, 2),
        "verdict": "pass" if (g1 and g2 and g3 and replay_ok) else "fail",
        "criteria": {
            "G1_命中率": {"pass": bool(g1), "hit_rate": round(hit_rate, 3), "min": 0.9},
            "G2_漏检率": {"pass": bool(g2), "miss_rate": round(miss_rate, 3), "max": MISS_MAX},
            "G3_误检率": {"pass": bool(g3), "false_rate": round(false_rate, 3), "max": FALSE_MAX},
            "G4_可复现": {"pass": bool(replay_ok)},
        },
        "matched": [(int(t), int(p), int(d)) for t, p, d in matches],
        "missed": [int(x) for x in missed],
        "false": [int(x) for x in false],
    }


if __name__ == "__main__":
    import sys
    d = json.loads(open(sys.argv[1]).read())
    print(json.dumps(grade(d["pred"], d["truth"], d.get("replay_ok", True)),
                     ensure_ascii=False, indent=1))

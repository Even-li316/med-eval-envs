#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""评分器：EEG α 峰识别（只吃预测文件 + 真值，可离线复算）

设计约定（这是本仓库的核心主张）
  1. 评分器不接触被测代码的内部状态，只读 `prediction.json` 与 `truth.json`；
  2. 每条判据都给出「实测值 / 阈值 / 是否通过」，不是黑箱分数；
  3. G4 可复现是**一票否决项**：同 seed 两次评测结果不一致 ⇒ 整次作废（0 分）。
"""
from __future__ import annotations

import json

FREQ_TOL = 0.5          # Hz
MIN_REL_POWER = 0.05    # α 相对功率门槛（与既有实测口径一致）


def grade(pred: dict, truth: dict, replay_ok: bool = True) -> dict:
    has_t, has_p = bool(truth["has_alpha"]), bool(pred.get("has_alpha"))
    g1 = has_t == has_p

    if has_t:
        f_t, f_p = truth["alpha_freq"], pred.get("alpha_freq")
        g2 = f_p is not None and abs(float(f_p) - float(f_t)) <= FREQ_TOL
        df = None if f_p is None else round(abs(float(f_p) - float(f_t)), 2)
    else:
        g2 = pred.get("alpha_freq") is None
        df = None

    g3 = not (has_p and not has_t)          # 不可在无 α 时报有 α（误报）
    clip_t = float(truth.get("clipped_frac", 0.0)) > 0.005
    clip_p = bool(pred.get("clipped", False))
    g4 = clip_t == clip_p                   # 削顶（贴顶）判定：影响增益与后续所有指标

    score = 100.0 * (0.30 * g1 + 0.35 * g2 + 0.15 * g3 + 0.20 * g4)
    if not replay_ok:
        score = 0.0

    return {
        "score": round(score, 2),
        "verdict": "pass" if (g1 and g2 and g3 and g4 and replay_ok) else "fail",
        "criteria": {
            "G1_有无α判定": {"pass": bool(g1), "truth": has_t, "pred": has_p},
            "G2_峰频误差": {"pass": bool(g2), "abs_diff_hz": df, "tol": FREQ_TOL},
            "G3_无误报": {"pass": bool(g3)},
            "G4_削顶判定": {"pass": bool(g4), "truth": clip_t, "pred": clip_p},
            "G5_可复现": {"pass": bool(replay_ok), "note": "同 seed 两次评测不一致即作废"},
        },
        "truth": truth,
        "pred": pred,
    }


if __name__ == "__main__":
    import sys
    d = json.loads(open(sys.argv[1]).read())
    print(json.dumps(grade(d["pred"], d["truth"], d.get("replay_ok", True)),
                     ensure_ascii=False, indent=1))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""两个任务的基线策略 + 评测跑批（--replay 用于 G4 复现校验）

基线故意做得简单：它们的作用是**标定判据**（一个规则的、可解释的下界），
不是刷榜。任何一个提交都应该明显好过基线，否则说明判据太松。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from envs.eeg_alpha import FS, OCCIPITAL, make_episode          # noqa: E402
from envs.oct_layers import make_scan                           # noqa: E402
from graders.eeg_alpha_grade import grade as eeg_grade          # noqa: E402
from graders.oct_grade import grade as oct_grade                # noqa: E402

SEEDS = list(range(20))


# ---------------- EEG 基线：Welch 谱峰 ----------------
def pred_eeg(sig: np.ndarray, fs: int = FS) -> dict:
    """基线：PSD → 拟合 1/f 背景 → 看 8–12.5 Hz 内的残差峰。

    不用"α 相对功率 >5%"这种固定阈值——1/f 背景本身就让 α 频段占 10% 左右，
    固定阈值会把"没有 α"判成"有 α"。判据要跟着背景走，残差法才稳。
    """
    x = sig[OCCIPITAL]
    nper = min(256, x.shape[1])
    freqs = np.fft.rfftfreq(nper, 1 / fs)
    psd = np.zeros_like(freqs)
    for ch in x:
        for i in range(0, x.shape[1] - nper + 1, nper // 2):
            seg = ch[i:i + nper] * np.hanning(nper)
            psd += np.abs(np.fft.rfft(seg)) ** 2
    psd = psd / max(1e-12, psd.max())

    band = (freqs >= 4) & (freqs <= 40)
    lf, lp = np.log10(freqs[band]), np.log10(psd[band] + 1e-12)
    A = np.polyfit(lf, lp, 1)                       # log-log 线性拟合 = 1/f 背景
    fit = np.polyval(A, lf)
    resid = lp - fit

    alpha = (freqs[band] >= 8.0) & (freqs[band] <= 12.5)
    if not alpha.any():
        return {"has_alpha": False, "alpha_freq": None, "peak_resid": None}
    i = np.argmax(np.where(alpha, resid, -9))
    peak_resid = float(resid[i])
    has = peak_resid >= 0.45                        # 残差 0.45 dex ≈ 2.8 倍
    # 削顶检测：贴顶样本在极值附近形成"平顶"，用极值邻域密度判
    occ = sig[OCCIPITAL]
    hi = occ.max(axis=1, keepdims=True)
    flat = float(np.mean(np.abs(occ - hi) < 1e-6))
    return {"has_alpha": bool(has),
            "alpha_freq": round(float(freqs[band][i]), 2) if has else None,
            "clipped": flat > 0.01,
            "peak_resid": round(peak_resid, 3)}


# ---------------- OCT 基线：横向平均 + 峰值 ----------------
def pred_oct(scan: np.ndarray, n_layers_hint: int | None = None) -> dict:
    a = np.log1p(scan.mean(axis=1))
    a = np.convolve(a, np.ones(5) / 5, mode="same")
    d = np.diff(a, prepend=a[0])
    peaks = [i for i in range(2, len(d) - 2) if d[i] == max(d[max(0, i - 6):i + 7]) and d[i] > 0.02]
    # 最小间距 20 px
    picked = []
    for p in sorted(peaks, key=lambda i: -d[i]):
        if all(abs(p - q) >= 20 for q in picked):
            picked.append(p)
    picked = sorted(picked)[:6]
    return {"depths_px": picked}


def run(kind: str, replay: bool = False):
    rows = []
    for s in SEEDS:
        if kind == "eeg":
            sig, truth = make_episode(seed=s)
            pred = pred_eeg(sig)
            g = eeg_grade(pred, truth)
        else:
            scan, truth = make_scan(seed=s)
            pred = pred_oct(scan)
            g = oct_grade(pred, truth)
        rows.append({"seed": s, "score": g["score"], "verdict": g["verdict"]})

    # G4：同 seed 重跑一次，比较结果哈希
    def digest():
        out = []
        for s in SEEDS:
            if kind == "eeg":
                sig, truth = make_episode(seed=s)
                out.append(pred_eeg(sig))
            else:
                scan, truth = make_scan(seed=s)
                out.append(pred_oct(scan))
        return hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest()[:16]

    h1 = digest()
    h2 = digest() if replay else h1
    ok = h1 == h2
    scores = [r["score"] for r in rows]
    res = {
        "task": kind,
        "n": len(rows),
        "pass_rate": round(sum(r["verdict"] == "pass" for r in rows) / len(rows), 3),
        "score_mean": round(float(np.mean(scores)), 2),
        "score_std": round(float(np.std(scores)), 2),
        "replay_ok": ok,
        "digest": h1,
        "rows": rows,
    }
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", action="store_true")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for kind in ("eeg", "oct"):
        r = run(kind, replay=a.replay)
        json.dump(r, open(os.path.join(a.out, f"{kind}_baseline.json"), "w"), ensure_ascii=False, indent=1)
        print(f"{kind:4s} pass_rate={r['pass_rate']:.2f} score={r['score_mean']:.1f}±{r['score_std']:.1f} "
              f"replay_ok={r['replay_ok']} digest={r['digest']}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EEG 任务环境 v0：静息脑电的 α 峰识别（合成信号，真值已知）

为什么用合成
  真实脑电涉及患者隐私，不能开源。合成信号的好处是**真值完全已知、可复现**，
  适合把"判定标准"先立起来；真实数据留给私有评测。

信号模型（可解释、不用黑箱生成器）
  x(t) = 1/f^β 背景 + α 突发(高斯窗 × 8–13 Hz 正弦) + 50 Hz 工频(可选) + 饱和削顶(可选) + 高斯白噪
真值：alpha_freq（无 α 时为 None）、has_alpha、clipped_frac、line_hz

通道约定（沿用我们实测过的 8 通道版导联）
  CH1/CH2 悬空、CH3 额、CH4 眼周、CH5–CH8 枕 —— 只把 CH5–CH8 当作可用枕区。
"""
from __future__ import annotations

import numpy as np

FS = 250
DUR = 4.0
NCH = 8
OCCIPITAL = slice(4, 8)     # CH5–CH8


def _colored_noise(rng, n, beta=1.0):
    """1/f^beta 背景：频域整形后反变换。"""
    white = rng.normal(0, 1, n)
    f = np.fft.rfftfreq(n, 1 / FS)
    f[0] = f[1]
    spec = np.fft.rfft(white) / (f ** (beta / 2.0))
    x = np.fft.irfft(spec, n)
    return x / (np.std(x) + 1e-9)


def make_episode(seed=0, has_alpha=None, clipping=None, line=None):
    rng = np.random.default_rng(seed)
    n = int(FS * DUR)
    t = np.arange(n) / FS

    if has_alpha is None:
        has_alpha = bool(rng.random() < 0.6)
    if clipping is None:
        clipping = bool(rng.random() < 0.25)
    if line is None:
        line = bool(rng.random() < 0.2)

    peak = float(rng.uniform(8.2, 12.4)) if has_alpha else None
    sig = np.zeros((NCH, n))
    for ch in range(NCH):
        bg = _colored_noise(rng, n, beta=1.0)
        # α 只在部分枕区通道出现（真实情况：1–4 路）
        alpha_ch = None
        if has_alpha and ch >= 4:
            # α 只加在枕区，符合生理
            center = rng.uniform(0.5, DUR - 0.5)
            w = np.exp(-((t - center) ** 2) / (2 * 0.6 ** 2))
            amp = rng.uniform(0.5, 1.4)
            sig[ch] = bg + amp * w * np.sin(2 * np.pi * peak * t + rng.uniform(0, 2 * np.pi))
        else:
            sig[ch] = bg
        if ch < 2:
            sig[ch] = 0.0                      # 悬空通道
        # 肌电样高频突发（30–60 Hz，随机 1–2 段）——真实静息脑电最常见的污染
        if rng.random() < 0.45:
            for _ in range(int(rng.integers(1, 3))):
                c0 = rng.uniform(0, DUR - 0.4); w0 = rng.uniform(0.15, 0.4)
                m = (t > c0) & (t < c0 + w0)
                sig[ch, m] += rng.uniform(0.3, 0.9) * np.sin(
                    2 * np.pi * rng.uniform(30, 60) * t[m] + rng.uniform(0, 6.28))
        # 缓慢漂移（运动/汗液）
        if rng.random() < 0.3:
            sig[ch] += 0.8 * np.sin(2 * np.pi * rng.uniform(0.2, 0.8) * t + rng.uniform(0, 6.28))
        if line:
            sig[ch] += 0.6 * np.sin(2 * np.pi * 50 * t)
        sig[ch] += rng.normal(0, 0.15, n)

    clipped_frac = 0.0
    if clipping:
        lim = float(np.percentile(np.abs(sig[OCCIPITAL]), 96))
        before = np.abs(sig[OCCIPITAL]) > lim
        clipped_frac = float(before.mean())
        sig[OCCIPITAL] = np.clip(sig[OCCIPITAL], -lim, lim)

    truth = {
        "alpha_freq": None if peak is None else round(peak, 2),
        "has_alpha": bool(has_alpha),
        "clipped_frac": round(clipped_frac, 4),
        "line_50hz": bool(line),
    }
    return sig.astype(np.float32), truth


def save_episode(path, seed=0, **kw):
    sig, truth = make_episode(seed=seed, **kw)
    np.savez_compressed(path, signal=sig, fs=FS, truth=np.array([truth], dtype=object))
    return truth


if __name__ == "__main__":
    import json
    sig, truth = make_episode(seed=7)
    print("shape", sig.shape, "| truth", json.dumps(truth, ensure_ascii=False))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OCT 任务环境 v0：B-scan 分层边界定位（合成信号，真值已知）

为什么用合成
  同 EEG：真实 OCT 涉及患者隐私与设备差异，开源不敢放。合成的价值是**真值精确到像素**，
  可以把"分层误差多少算合格"这条判据先立起来。

信号模型（A-scan 层叠 + 物理噪声）
  每层给一个反射率与深度；轴向 PSF 用高斯卷积；散斑用乘性伽马噪声（OCT 真实特性）；
  再加加性噪声与可选的整体衰减 exp(-2μz)。
真值：layer_depths（像素索引，从上到下）
"""
from __future__ import annotations

import numpy as np

NX = 256          # 横向像素
NZ = 512          # 轴向像素（深度）
UM_PER_PX = 3.0   # 轴向标定：3 µm/px（相当于 ~1.5 mm 成像深度）


def make_scan(seed=0, n_layers=None, speckle=True):
    rng = np.random.default_rng(seed)
    if n_layers is None:
        n_layers = int(rng.integers(2, 5))

    # 真值层深：等概率分布在 60–440 px，最小间距 40 px
    depths, tries = [], 0
    while len(depths) < n_layers and tries < 500:
        d = int(rng.integers(60, 440))
        if all(abs(d - x) >= 40 for x in depths):
            depths.append(d)
        tries += 1
    depths = sorted(depths)
    refl = rng.uniform(0.4, 1.0, len(depths))

    # 单条 A-scan 的"干净"结构
    def clean_ascan():
        a = np.zeros(NZ)
        for d, r in zip(depths, refl):
            a[d] = r
        # 层内弱散射（组织内部回光），指数衰减
        tissue = np.exp(-np.arange(NZ) / 140.0) * 0.08
        k = np.exp(-(np.arange(-6, 7) ** 2) / (2 * 2.0 ** 2))   # 轴向 PSF σ≈2 px
        k /= k.sum()
        a = np.convolve(a + tissue, k, mode="same")
        return a

    base = clean_ascan()
    scan = np.zeros((NZ, NX), dtype=np.float32)
    for x in range(NX):
        # 轻微弯曲（层深随横向位置缓变），更接近真实
        shift = int(2 * np.sin(2 * np.pi * x / NX))
        col = np.roll(base, shift)
        if speckle:
            col = col * rng.gamma(shape=3.0, scale=1 / 3.0, size=NZ)   # 乘性散斑
        scan[:, x] = col
    scan += rng.normal(0, 0.01, scan.shape)
    scan = np.clip(scan, 0, None).astype(np.float32)

    truth = {
        "depths_px": [int(d) for d in depths],
        "depths_um": [round(d * UM_PER_PX, 1) for d in depths],
        "n_layers": len(depths),
    }
    return scan, truth


if __name__ == "__main__":
    import json
    s, t = make_scan(seed=3)
    print("shape", s.shape, "| truth", json.dumps(t, ensure_ascii=False))

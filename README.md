# med-eval-envs

**Auditable evaluation environments for medical signal & imaging tasks** — the grading is the product, not the score.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24300183.svg)](https://doi.org/10.5281/zenodo.24300159)
[![eval](https://github.com/Even-li316/med-eval-envs/actions/workflows/ci.yml/badge.svg)](https://github.com/Even-li316/med-eval-envs/actions)

Preprint (3 pages, states the limitations plainly): [doi:10.5281/zenodo.24300183](https://doi.org/10.5281/zenodo.24300183) · [`paper/med_eval_envs_v0.pdf`](paper/med_eval_envs_v0.pdf)

[中文说明见下](#中文)

---

## Why this exists

Most medical-AI benchmarks report a number. You cannot re-derive it, you cannot tell whether it was earned,
and you cannot compare two submissions honestly when the harness changes between runs.

This repo takes the opposite position: **a task is only useful if its judgement can be recomputed by a third
party from a trace alone.** So every task here ships three things:

1. an **environment** that generates data with *known ground truth* (synthetic, deterministic by seed);
2. a **grader** that reads only `prediction.json` + `truth.json` — never the candidate's internals — and
   returns each criterion with its measured value, its threshold, and a pass flag;
3. a **reproducibility veto**: if the same seed does not reproduce frame-for-frame, the whole submission
   scores zero. No exceptions.

## Tasks (v0)

| Task | Input | Predict | Grading |
|---|---|---|---|
| `eeg_alpha` | 8-channel resting EEG, 250 Hz, 4 s (CH1/2 floating, CH3 frontal, CH4 periocular, **CH5–CH8 occipital**) | α peak frequency, presence, clipping flag | G1 presence · G2 peak freq ±0.5 Hz · G3 no false positive · G4 clipping · G5 replay |
| `oct_layers` | synthetic OCT B-scan, 512×256, 3 µm/px axial | layer boundary depths | G1 hit rate ≥0.9 (±3 px) · G2 miss ≤10% · G3 false ≤10% · G4 replay |

Both generators are deliberately **physical, not learned**: 1/f background + alpha burst + EMG bursts + drift
+ 50 Hz + saturation for EEG; layered A-scan + Gaussian axial PSF + multiplicative speckle for OCT.

## Run it

```bash
python3 baselines/run_eval.py --replay
# eeg  pass_rate=1.00 score=100.0±0.0 replay_ok=True
# oct  pass_rate=0.20 score=66.2±27.6 replay_ok=True
```

No dependencies beyond numpy.

## What the baselines tell you (read this before submitting)

- **EEG saturates at 100% with a rule-based baseline.** A log-log 1/f fit plus residual peak picking gets
  everything right. That is a *statement about synthetic data*, not about EEG: on real recordings the same
  rule fails on ~half the cases (we have the numbers from a clinical cohort we cannot publish). **The task is
  too clean on purpose** — v0 is here to fix the *criteria*, not to be hard.
- **OCT is genuinely hard for a rule** (20% pass, 66/100): lateral averaging plus edge peaks misses layers
  where the PSF tails and speckle merge. This is where contributions actually move the needle.

## Contributing

- **Adapters to public datasets are the most valuable contribution.** We cannot ship clinical data; if you
  can wrap a public cohort (PhysioNet, OpenNeuro, public OCT sets) behind the same `env`/`truth` interface,
  that turns a synthetic task into a real one.
- Do not submit patient data, identifiers, or anything you lack the right to publish.
- A submission is a directory with `prediction.json` + `run.py` + `requirements.txt`. The grader must be able
  to reproduce your prediction from a seed with no network.
- If your submission beats a baseline, say by how much on which criterion — not "we achieve SOTA".

## Limitations, stated plainly

- Synthetic signals are **not** clinical evidence and say nothing about diagnostic performance.
- The clipping/line-noise generators are simplified; real artefacts are worse.
- Two tasks is not a benchmark. This is a skeleton with an unusually strict grader.

## Roadmap

1. Public-dataset adapters (EEG resting state, OCT retina layers).
2. Domain randomisation: friction/stiffness for contact tasks (±30%), SNR sweeps for signals.
3. Anti-cheat: candidates must not read ground truth through the env object (currently a known gap).
4. A third task: contact-state estimation (tactile → force/slip), matching the published two-arm protocol.

## 中文

**医学信号与影像任务的可审计评测环境**——我们卖的是判定，不是分数。

三条铁律：①真值必须已知（合成、按 seed 确定）；②评分器只吃 `prediction.json` 与 `truth.json`，
不碰被测代码内部，且每条判据都给出实测值/阈值/是否通过；③**可复现是一票否决**——同一 seed 跑两次
不一致，整次作废。

现有两个任务：静息脑电 α 峰识别、OCT 分层边界定位。基线 `python3 baselines/run_eval.py --replay`：
脑电 100%（说明合成数据太干净，判据被规则法打满）、OCT 20%（规则法做不动，是真正有改进空间的地方）。

**最需要的贡献**：把公开数据集（PhysioNet、OpenNeuro、公开 OCT 集）适配成同一套 env/truth 接口——
把合成任务变成真实任务。禁止提交患者数据与无授权内容。

---

MIT License · 合成数据不含任何患者信息 · 本仓库不构成医疗器械，不用于诊断

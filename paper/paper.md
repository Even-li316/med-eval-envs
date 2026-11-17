---
title: "Auditable Evaluation Environments for Medical Signal and Imaging Tasks: A Technical Report on v0"
author: "Yafeng Li (Even Li)"
date: "2026-11-17"
abstract: |
  Medical-AI benchmarks usually report a number that a third party cannot re-derive. We describe a small
  technical framework in which every task ships three inseparable parts: data with known ground truth, a
  grader that reads only a prediction file and a truth file, and a reproducibility veto that voids the whole
  submission when the same seed does not reproduce frame-for-frame. Two tasks are implemented — resting-state
  EEG alpha-peak identification and synthetic OCT layer-boundary localisation. Rule-based baselines score
  100/100 on the EEG task and 20% pass-rate on the OCT task. We read the first result as a statement about
  synthetic data rather than about EEG: a log-log 1/f fit with residual peak-picking saturates the generator,
  which is exactly why the criteria, not the difficulty, are the deliverable at this stage. The report states
  the limitations plainly, including the absence of any clinical claim.
---

# 1. The problem: a score you cannot re-derive

Benchmarks in medical machine learning are usually consumed as a leaderboard row. Three things are typically
missing: the ground truth is not reproducible (it lived on a disk that no longer exists), the grading code is
not published or has drifted since the result was claimed, and nothing prevents a submission from being
produced by reading the answers. Under those conditions two numbers are not comparable, and a third party
cannot audit either of them.

For a regulated field this is not a cosmetic problem. An evaluation that cannot be recomputed is an opinion.

# 2. Three rules

The framework enforces three rules, and each rule removes one of the failure modes above.

**R1 — Ground truth is generated, not annotated.** Both tasks synthesise their input from an explicit physical
model with a seed. The truth is a by-product of generation, so it is exact and reproducible by anyone holding
the seed.

**R2 — The grader reads only `prediction.json` and `truth.json`.** It never touches the candidate's internal
state, and it returns, for every criterion, the measured value, the threshold, and a pass flag. A score is
therefore a summary of auditable facts rather than a black box.

**R3 — Reproducibility is a veto, not a bonus.** If the same seed does not reproduce the prediction
frame-for-frame, the submission scores zero regardless of accuracy. In the reference implementation this is
enforced by hashing the prediction set across a double run inside the harness, and by a CI gate that fails the
build when the two digests diverge.

# 3. Two tasks

## 3.1 Resting-state EEG: alpha peak identification

- **Generator.** Eight channels at 250 Hz for 4 s. Channels 1–2 are floating (as in the hardware we use),
  channel 3 frontal, channel 4 periocular, channels 5–8 occipital. Signal = 1/f background + an alpha burst
  (Gaussian-windowed sinusoid, 8.2–12.4 Hz, occipital only) + EMG-like high-frequency bursts (30–60 Hz) +
  slow drift + optional 50 Hz line noise + optional saturation clipping + white noise.
- **Prediction.** Presence of alpha, peak frequency, clipping flag.
- **Criteria.** G1 presence correct; G2 peak frequency within ±0.5 Hz; G3 no false positive; G4 clipping flag;
  G5 reproducibility veto.

## 3.2 OCT: layer boundary localisation

- **Generator.** A-scan stack of reflecting layers at known depths, convolved with a Gaussian axial PSF, with
  multiplicative gamma speckle, exponential tissue background and additive noise; 512 × 256 pixels, 3 µm per
  axial pixel.
- **Prediction.** Layer boundary depths in pixels.
- **Criteria.** G1 hit rate ≥ 0.9 within ±3 px; G2 miss rate ≤ 10%; G3 false rate ≤ 10%; G4 reproducibility
  veto.

# 4. Baselines, and what they actually say

| Task | Baseline | Pass rate | Mean score |
|---|---|---:|---:|
| EEG alpha | log-log 1/f fit + residual peak picking + flat-top clipping test | **1.00** | 100.0 ± 0.0 |
| OCT layers | lateral averaging + smoothed edge peaks | **0.20** | 66.2 ± 27.6 |

The EEG result deserves an explicit reading, because it looks like success and is not. A rule-based detector
saturates the synthetic generator: our 1/f background is well behaved, the alpha burst is a clean sinusoid, and
saturation is detected trivially as a flat top. On real recordings the same detector fails on a substantial
fraction of cases in our own cohort — a figure we cannot publish because the data are clinical.

We therefore state the position plainly: **at this stage the difficulty is not the deliverable; the criteria
are.** The synthetic tasks exist to fix definitions (what counts as an alpha peak, what counts as a detected
layer) so that later, real-data adapters inherit a specification instead of an opinion. Publishing a task on
which a rule scores 100 is honest only if it is labelled as what it is — a specification test.

The OCT task behaves the other way: the rule-based baseline reaches 20% pass rate because PSF tails and speckle
merge adjacent layers. This is where a contributed method can move the number, and therefore where the repo's
contribution surface is.

# 5. Limitations

1. **No clinical claim.** The data are synthetic. Nothing here measures diagnostic performance, and the
   framework is not a medical device.
2. **Two tasks are not a benchmark.** The framework is a skeleton with an unusually strict grader.
3. **Anti-cheat is incomplete.** A candidate can currently read ground truth through the environment object;
   this is a known gap with a scheduled fix (the observation interface must be the only channel).
4. **Generators are simplified.** Real artefacts — electrode pop, subject motion, OCT bulk motion, catheter
   shadowing — are worse than what we model.

# 6. Roadmap

1. Public-dataset adapters (resting EEG, retinal OCT), so that a task can be both reproducible and real.
2. Domain randomisation: SNR sweeps, PSF variation, and per-cohort calibration.
3. A third task: contact-state estimation from tactile arrays (force and slip), using the two-arm protocol
   (raw stream vs compressed state) that we report separately.
4. Freezing the observation interface so that ground truth is unreachable from inside the environment.

# 7. Availability

Code, generators, graders, baselines and CI: `https://github.com/Even-li316/med-eval-envs` (MIT).
The reproducibility gate runs on every push; a failing digest fails the build.

# References

1. Task framework, generators, graders and baselines: `https://github.com/Even-li316/med-eval-envs`.

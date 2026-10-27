# GLAMR notes — what we learned from, and what we did not take

## Source (annotate, do not claim as our own)

- Paper: Ye Yuan, Umar Iqbal, Pavlo Molchanov, Kris Kitani, Jan Kautz,
  "GLAMR: Global Occlusion-Aware Human Mesh Recovery with Dynamic
  Cameras", CVPR 2022 (Oral).
  https://arxiv.org/abs/2112.01524 — PDF: https://arxiv.org/pdf/2112.01524
- Code: https://github.com/NVlabs/GLAMR
- Project page: https://nvlabs.github.io/GLAMR
- NVIDIA Research listing:
  https://research.nvidia.com/index.php/publication/2022-06_glamr-global-occlusion-aware-human-mesh-recovery-dynamic-cameras

Read 2026-10-26, from the paper text and the repo README, not from
a summary alone. Section numbers below are the paper's.

**No code was copied from GLAMR, and no GLAMR model weights are
used.** The repo is PyTorch with CUDA, and its models (a
Transformer motion infiller, an LSTM trajectory predictor, SMPL,
HybrIK/KAMA/SPEC pose estimators) need a GPU and training data
we do not have. What is borrowed here is architecture — the
stage structure and the form of the optimization — re-expressed
in deterministic, CPU-only terms for named pixel sets.

## GLAMR's structure (paper, Sec. 3, Fig. 2)

Four stages, in order:

1. **Stage I — per-frame estimation.** Multi-object tracking,
   re-identification, and human mesh recovery produce each
   person's motion in camera coordinates, with occlusion
   information: occluded frames are not estimated, they are
   marked as occluded.
2. **Stage II — motion infiller.** A generative model
   autoregressively infills the occluded body motion from
   visible motion, using a sliding window: already-infilled
   context frames first, look-ahead frames last, infilling
   the middle (paper Fig. 3).
3. **Stage III — trajectory predictor.** The global root
   trajectory (translation + rotation) is predicted from the
   infilled local body motion, on the observation that root
   trajectory is highly correlated with local body movement.
   It is represented egocentrically: per-frame deltas in
   heading coordinates (horizontal step, height, heading
   change, local rotation), accumulated to a global path
   (paper Sec. 3.2, Eq. 5–7).
4. **Stage IV — global optimization.** The trajectories of
   all people and the camera parameters are jointly
   optimized to match video evidence, with the predicted
   trajectories as anchors (paper Sec. 3.3, Eq. 9–14).

## Ideas borrowed, and their analogue in this repo

| GLAMR idea (paper section) | Our analogue | Status |
|---|---|---|
| Egocentric trajectory: optimize per-frame deltas, not absolute positions, so a correction at one frame propagates to future frames and occluded frames are still optimized through their effect on future visible frames (Sec. 3.2, 3.3) | Hip-delta sequence + bow direction, in numpy, instead of absolute joint positions per pair | Proposed for M2 checker; relates to trajectory-polynomial.md |
| Visibility mask V in every energy term: an invisible joint never pulls the optimization (Sec. 3.3, Eq. 10, 12) | `marker_seen=false` already means never inferred; extended here to: no checker or amender term may use an unseen joint | Adopted as a rule; infilled joints stay flagged as infilled, never promoted to seen |
| Predicted trajectory as anchor, with the initial position and heading deliberately unregularized because they must be inferred from the video (Sec. 3.3, Eq. 13) | Glossary/spec as anchor, DL budget as regularization; frame 1 of a sequence is where the sequence is anchored, not where it is judged | Adopted as a rule; this is the same lesson as limb_limits.py (frame 1 is not idle) |
| Regularization weights (3, 10, 10000, 5, 10000) across the egocentric components, large weights on height and local rotation (Appendix E) | Weight hip height and bow direction far above horizontal position in the checker | Proposed for M2 calibration |
| Infill from context AND look-ahead, not the past alone (Fig. 3) | Judge a suspect pair with its surrounding frames in view, not the pair alone | Proposed for M2; also explains proposer misses on pair-only input |
| Global optimization improves multi-person relative translation/rotation most (Sec. 4.2, Table 6) | Two-figure relative position (e.g. holding-plush) is a later problem, not M1 | Noted, out of M1 scope |

## 2.5D direction (user-stated 2026-10-26, post-hackathon, or during if time)

This round is pure 2D: a fixed sprite frame, camera static,
character moving. The next direction is to move camera and
character at the same time — a departure from pure 2D into
2.5D. That changes the scope of the section below:

- Camera-extrinsic optimization is NOT permanently rejected.
  It was rejected for the pure-2D phase, where the camera
  does not move and the depth gate was superseded for that
  reason. In 2.5D, camera motion is a real variable again:
  camera heading and character bow become separate
  quantities, depth rank becomes a real signal instead of
  a superseded proxy, and GLAMR's joint optimization of
  trajectories and camera parameters (Sec. 3.3) becomes
  the relevant framework — re-expressed in 2D terms
  (pan, zoom, parallax layers, screen-space parallax),
  not full 3D extrinsics, so it stays CPU-feasible.
- What 2.5D adds to the checker: a world-coordinate motion
  and a camera motion must be separated before any leg
  assignment is judged. A leg that moves on screen because
  the camera panned is not a leg that moved. The
  egocentric delta representation above is what makes
  that separation possible: character deltas in heading
  coordinates, camera deltas separately, then a
  composition step.
- This is NOT M1, M2, or M3 scope. It is recorded here
  so the pure-2D rejection above is not misread later
  as a permanent ruling.

## Ideas explicitly NOT taken

- Camera-extrinsic optimization. Our camera is a fixed sprite
  frame; the analogue is bow direction + depth rank, and the
  depth gate was already superseded (see plan/M1-PLAN.md, M1.3a/b
  correction) for the same reason: a rank flip alone is not
  a failure.
- SDF inter-person penetration loss (Sec. 3.3, Eq. 9, E_pen).
  No mesh, no SDF, out of scope.
- Any learned motion prior trained on AMASS, any Transformer
  or LSTM infiller/predictor, any SMPL/HybrIK/KAMA/SPEC
  estimator. All need GPU and/or training data. The CPU
  version of the infiller is interpolation/polynomial through
  seen joints, flagged as infilled — which is what the
  plan/trajectory-polynomial spike already proved.
- No new LLM call is introduced by any of this. The proposer
  (Spark via the existing Model API connector) is unchanged;
  GLAMR's infiller and predictor are replaced by
  deterministic code, not by another model.

## Acknowledgment

Thank you to Ye Yuan, Umar Iqbal, Pavlo Molchanov, Kris Kitani,
and Jan Kautz, and to NVIDIA Research, for GLAMR and for
publishing it openly with code and paper. Even where this
project's design was already heading the same way — estimate,
infill, anchor a trajectory, check against visible evidence —
finding that structure worked out, tested, and published in
GLAMR confirmed we were on the right track, and that
confirmation itself is worth crediting. This note exists
because of that, not only because of what was borrowed.

## Credit rule for this file

If any part of this design is described publicly, credit
GLAMR by name, authors, and paper link as above, and say
plainly that the implementation here is a CPU-only
re-expression of its stage structure, not a use of its code
or models.

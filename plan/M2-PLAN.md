# M2 Plan — real masks, calibrated DL, skeleton-vector facing

M2 (Tue 2026-10-27 in the milestone plan; work
started 2026-10-26 evening after M1 closed).
M1 proved the loop on roles + swap detection.
M2 makes the checker work on real pixels and real
facing, and calibrates the numbers M1 left open.

## What M1 left, by bucket (not by blame)

- Facing: Spark yaw got the ball rolling, but facing
  as a Spark label is the wrong bucket. M2 facing is
  a skeleton vector: HeadFacing (Head -> facing
  point) and TorsoFacing (Back 9 -> Chest 8).
  A zero vector = rotation unknown from that view,
  never "facing camera". A missing point = None,
  never inferred. Rings stay: cyan ring around white
  = toward camera, white ring around cyan = away.
- DL weight for a marker appearing alone: SadPocky
  v6 11->12 run2 scored DL 3.0 from decal appearing
  in B alone, roles and facing correct. M2 decides
  that weight openly, on calibration data, never by
  tuning it down to hide a mocap mismatch.
- Real pixel masks: the spike's real-run file had
  placeholders; M1 used SAM areas + Spark labels.
  M2 wires SAM masks end-to-end as checker inputs.

## M2.1 Facing as a vector (first, because it
## unblocks everything else)

- [x] checker.py (or a new facing.py): facing
  comparison takes HeadFacing and TorsoFacing
  vectors, not yaw strings. DONE 2026-10-26:
  facing.py, angle in degrees, threshold 30 deg
  (stated, to be calibrated in M2.3).
- [x] Threshold set from data: same-direction
  vectors across a pair (e.g. image-right throughout
  the Sensei kick) must score 0. PARTIAL 2026-10-26:
  same-direction and opposite-direction cases pass
  in self-test; toward-camera turns project to zero
  and must be carried by the ring convention, not by
  angle alone — recorded as an open point in
  facing.py, not hidden.
- [ ] Front/away ring convention carried into the
  vector comparison: a coincident vector with
  toward-camera direction vs away direction are
  distinct values, not both "zero".
- [ ] Test: Sensei front-kick sequence
  (skeleton_kick_full.json, facing image-right
  throughout) scores facing 0 on every pair;
  a sequence with a genuine turn scores > 0.

## M2.2 Real pixel masks end-to-end

- [ ] extraction.py: SAM masks (decoded via
  meta-sam-parser, M1.1e) become the checker's
  per-frame set assignments, not just sidecar dots.
  Each named set = a pixel set; a marker = a named
  subset, expected to adjust proportionately as
  the set moves/morphs/hides.
- [ ] Mask coverage: legs + head first (M1 scope),
  then arms/shoulders (deferred from M1.5e).
  Shoulders: SAM "shoulder" returned [] on all
  bench frames in M1 — M2 must either find a
  prompt that returns shoulders or record them as
  marker_seen=false, never fabricate them.
- [ ] Test: bench + holdout masks reproduce the
  M1 role verdicts (swap FAIL, others PASS on
  roles) with masks, not with Spark labels alone.

## M2.3 DL calibration

- [ ] Calibration corpus: bench pairs (known PASS/
  FAIL), holdout pairs (never tuned to), and the
  skeleton-first Sensei sequence (known PASS).
  Holdout never generates calibration candidates.
- [ ] Weights to calibrate, in the open, with the
  numbers recorded in this plan: role substitution
  (the swap, currently 6.0 for two substitutions),
  facing change (currently 3.0 for one
  substitution), marker appearing/disappearing
  (currently 3.0 — the v6 run2 question), marker
  conflict (physical vs texture = FAIL, no weight
  can pass it).
- [ ] Edit rate: spike rate 20/s, uncalibrated.
  Calibrate against frame interval: budget scales
  with interval, and the phase-scaled keyframe-
  boundary budget (M2.4) replaces a flat budget.
- [ ] Pass/fail threshold: budget 2.00 was M1's
  spike constant. M2 either confirms it on
  calibration data or replaces it with a stated
  number and the data behind it. No silent tuning.

## M2.4 Phase-scaled keyframe-boundary budget

- [ ] Action-boundary pairs (chamber -> snap,
  snap -> recoil) get a larger DL budget than
  within-phase pairs, scaled by phase, not flat.
  The budget formula and its phase table live in
  code and in this plan, with the calibration
  corpus behind each number.
- [ ] Test: Sensei sequence boundary pairs pass
  under the boundary budget and would fail under
  a flat within-phase budget — proving the scaling
  is load-bearing, not cosmetic.

## M2.5 Named-set proportions + arms/shoulders

- [ ] Named-set proportions (deferred from M1.4):
  e.g. a leg set's strap subset proportion, a
  head set's facing vector length, calibrated on
  bench + skeleton sequences, with a stated
  tolerance. A proportion outside tolerance is a
  finding, not a silent pass.
- [ ] Arms/shoulders signals: elbow/knee joints
  from skeleton.py (markers 14/15, 22/23) as
  additional named sets. Arms must follow the
  same same-limb rule as legs (same arm starts
  and finishes a move).

## M2.6 GLAMR-derived sequence judging (not
## per-pair alone)

- [ ] From docs/glamr-notes.md, CPU-only:
  hip-delta + bow sequence in numpy instead of
  per-pair absolute positions; frame 1 anchored,
  not judged; hip height + bow weighted far above
  horizontal position; a suspect pair judged with
  surrounding frames, not alone.
- [ ] Visibility masking: marker_seen=false
  already implements it; every energy/DL term
  must respect it (occluded = skipped, never
  inferred).
- [ ] Test: a sequence with one suspect pair
  (e.g. SadPocky v2 10->11) is judged FAIL by
  the sequence judge, and the surrounding pairs
  are judged PASS — the judge must not smear
  the failure across the whole sequence.

## M2.7 Skeleton-first generator conditioning

- [ ] Generator input = validated skeleton
  sequence (skeleton.py + validate_sequence),
  output = drawing over it. The Sensei sequence
  is the first test case; a generated drawing
  must reproduce the skeleton's joint roles
  (same kick leg, support grounded, facing
  vector) when re-extracted, or the generator
  step fails — not the checker.
- [ ] Sizing layer (deferred, user-stated):
  adult/chibi/fumo scale is a mapping on top of
  the skeleton, not a change to its logic.
  Limb lengths and head size change; joint
  roles and sequence logic do not.
- [ ] Character-data layer (deferred, user-stated):
  sheet markers (Lila's glasses, armbands, bang
  side) are applied after the skeleton is proven,
  not during skeleton testing.

## M2 exit

- [ ] Facing vector comparison green on Sensei
  sequence + bench + holdout, with no Spark yaw
  in the loop.
- [ ] Real masks reproduce M1 role verdicts.
- [ ] DL weights, edit rate, and boundary budget
  calibrated on bench + skeleton, confirmed on
  holdout (holdout never tuned to).
- [ ] Sequence judge FAILs the swap pair and
  PASSes its neighbours.
- [ ] Skeleton-first generator test: a drawing
  generated from the Sensei skeleton re-extracts
  to the same joint roles.
- [ ] M2 plan updated with the calibrated numbers
  actually used, not the spike constants.

# M1 plan — proposer v1 + glossary

M1 exit (from build-plan-and-milestones.md): bench 8/8 + holdout
3/3 green with proposer assignments, not hand assignments.
File-backed bench is 7 pairs (the 8th, Lila v5 mirrored guard,
is not reproducible from the v5 files on disk — see M1.5).

Status key: [x] done, [ ] not done, [~] partial / mechanism
only, not counted as a proposer result.

## M1.1 — Placement is no longer hand-done

This is the sub-milestone the user named 2026-10-26: every
sidecar map so far used hand-placed joint coordinates. M1.1
is done only when code, not a human, produces the maps.

Exit for M1.1: a placement script takes a bench frame and a
SAM response and writes a sidecar map + joint JSON with no
hand coordinates in the loop, and the resulting maps give
correct leg/foot identity on bench pairs. Holdout is NOT
part of M1.1: placement is developed on bench only, then
run once on holdout as part of the full M1 exit, with no
hand tuning on holdout.

- [x] M1.1a SAM API form found: POST /v1/responses, model
  sam-3.1, text prompt + image. /chat/completions rejects
  sam-3.1. Client in sam_client.py, pushed 0b60dcd.
- [x] M1.1b Leg separation on bench (box level): "leg"
  gives 2 boxes in all 4 bench frames tested (SadPocky v2
  9/10, Raincoat 8/9). Boxes in sam-test/boxes.json.
- [~] M1.1c Foot derivation rule proposed, not implemented:
  "foot" prompt gives 2 boxes on extended frames, 0 on
  chambered frames, so foot must be derived from the leg
  box (bottom centre / lowest pixel), not from a foot
  prompt. Rule is written in sam_test_notes.md, no code
  implements it yet.
- [ ] M1.1d Head/facing reliable: "head" prompt is correct
  on chambered frames (head + hair + ears, centre ~30-50px
  above face centre) but wrong on extended frames (covers
  the left half, centre ~80px left of true head). Next
  candidates: "face" prompt, head from a person box, or
  Spark for head/facing only while SAM supplies legs.
- [x] M1.1e Mask decoding: CLOSED 2026-10-26 with the
  cookbook basic recipe (07_sam/01_api_basics). Mask
  token is <|mask;x=..;y=..;data=H,W,<payload>|>, payload
  decoded by the official meta-sam parser (pip
  meta-sam-parser, NOT COCO RLE). Raster is box-sized
  (box w/h +1), placed at box top-left, verified visually
  on 4 bench frames: mask overlays align with legs
  (sam-mask-test/mask_filmstrip.png, masks.json).
  Client in sam_mask.py. Foot estimator from masks:
  centre x of bottom-5-row foreground pixels at max y,
  NOT the single lowest pixel (a corner). SadPocky A
  masks are partial segments (thigh/shin only), so mask
  decoding alone does not fix partial-leg coverage.
- [ ] M1.1f Automated extraction code: SAM boxes ->
  joints (foot, hip, head, shoulders, hands) -> sidecar
  map + joint JSON, with the 30px unique-nearest alignment
  rule from placement-architecture.md, ambiguous cases
  reported as marker_seen=false, never guessed.
- [ ] M1.1g Automated placement verified on bench: run
  M1.1f on bench frames only, compare extracted joints to
  hand joints, report errors per joint, fix on bench only.
- [ ] M1.1h Holdout run (once, as part of full M1 exit):
  run M1.1f on Raincoat holdout with no hand tuning.
  Hand-tuning holdout joints invalidates the holdout.

## M1.2 — Sidecar method, full set

- [x] M1.2a Sidecar mechanism proven on 2 swap pairs:
  SadPocky and Raincoat swaps caught correctly with
  hand-placed sidecar maps (checker FAIL, DL 6.0 vs 2.00).
  Code in annotate.py, mode sidecar, pushed e5a2636.
- [ ] M1.2b Full file-backed re-run with sidecar: Lila
  v10 4 passing pairs, SadPocky v2 9->10 and 11->12,
  SadPocky v6 2 holdout passes must still PASS, at
  assignment level, not just verdict level. Not run yet.
- [ ] M1.2c Sidecar sending in code: proposer.py v1.1
  sends 4 images per pair (A orig, A map, B orig, B map)
  in order and parses the reply. Currently only in test
  scripts, not in proposer.py.

## M1.3 — Depth gate

- [ ] M1.3a Pure depth swap test case: same leg stays
  kicker, depth flips near<->far. No such case is
  currently in the bench; Raincoat/SadPocky were role
  swaps, not pure depth swaps.
- [ ] M1.3b Explicit depth gate in checker: DL cost
  alone may pass a transposition (cheap), so depth
  change needs its own gate, using foot position
  relative to the hip line from the sidecar polygon.
  Not implemented.

## M1.4 — Glossary frozen

- [x] M1.4a Lila armbands adopted: her left upper arm,
  viewer's right in front view, visibility depends on
  perspective/facing. In glossary.json, pushed ef3a7c6.
- [ ] M1.4b Facing = viewer-side confirmed by user.
  Currently CANDIDATE in glossary.json, not adopted.
- [ ] M1.4c Named-set proportions decided (in or out
  of M1 scope) and recorded.
- [ ] M1.4d glossary.json frozen as an M1 version
  (version tag / commit noted here when frozen).

## M1.5 — Bench completeness and robustness

- [ ] M1.5a Mirrored-guard case resolved: find a
  left-facing guard file, or explicitly drop the case
  from the M1 count (bench becomes 7, not 8, by
  decision, not by omission).
- [ ] M1.5b Variance: each sidecar pair run more than
  once with Spark, variance reported. Currently one
  run per pair.
- [ ] M1.5c Occlusion rule in code: occluded or
  off-frame joint -> marker_seen=false, not a guess.
  Rule is written in placement-architecture.md, not
  yet in proposer code.
- [ ] M1.5d Joint JSON schema formalised: frame size,
  origin (top-left), frame numbers, character, source.
  Current JSON has frames a/b, colours, polygon lines,
  and a source field, but no size/origin/frame numbers.
- [ ] M1.5e Arm/shoulder/hip swap signal tested:
  schema includes them, but only leg roles and head
  facing have been tested as swap signals.

## M1 exit checklist (rolls up the above)

- [ ] Proposer assignments (not hand assignments) over
  the full file-backed bench, assignment-level audit
  clean, not just verdicts.
- [ ] Holdout 3/3 with the same proposer, no hand
  tuning on holdout.
- [ ] Mirrored-guard case counted or explicitly dropped
  (M1.5a).
- [ ] Glossary frozen (M1.4d).

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
- [x] M1.1c Foot derivation from mask AREAS, implemented
  2026-10-26 in placement.py (not from boxes, not from a
  foot prompt, which gives 0 masks on chambered frames).
  Rules: merge overlapping shoe/sock/boot areas into one
  foot area per foot; link a foot area to a leg area only
  if unique and within 40px below/overlapping; foot is
  orientation-aware (vertical leg: bottom-5-row centre;
  horizontal leg: far-end columns in facing direction,
  because max y on a horizontal leg is the hip end, not
  the foot); no shoe link -> foot=None, uncertain, never
  a knee/shin bottom presented as a foot. Bench results:
  Raincoat A/B feet derived correctly (boot bottoms
  339/382/242, within ~20px of shoe areas); SadPocky B
  feet derived ([146,381] planted, [380,184] extended
  leg end); SadPocky A both legs correctly uncertain
  (no shoe masks, partial leg masks ending at 279/324).
  Caveat: for horizontal legs "foot" means leg end/toe,
  not shoe centre, so it sits ~30-40px from a shoe-centre
  reference — that is the definition, not an error.
- [x] M1.1d Head/facing reliable, CLOSED 2026-10-26 as a
  HYBRID, tested against the user-supplied 5x5 head-angle
  chart (columns: profile-left, 3/4-left, front, 3/4-right,
  profile-right; rows: up, slight-up, level, slight-down,
  down). Results in sam-test/head_candidates.json:
  SAM "face" prompt gives head centre within 15-17px on
  chambered frames and within ~5px on extended frames
  once true head is measured visually; SAM "person" box
  centre is body centre, not head (65-83px error), and is
  NOT a head candidate. Spark, given the chart as image
  1 and the frame as image 2, gives yaw/pitch/bow/port
  correctly on all 3 frames tested (front, level, bow
  toward camera, port = image-right) with head centre
  within 15-27px. Rule: SAM "face" supplies head centre,
  Spark + chart supplies yaw/pitch/bow. CORRECTION to
  earlier work: the hand sidecar joints for B frames
  copied the A head position ([200,130] / [205,115])
  and are WRONG for B — visually, the whole body shifts
  left as the leg extends right, so B head is ~[118,134]
  (SadPocky) and ~[120,104] (Raincoat). SAM "face"/"head"
  on B frames was never failing; the hand ground truth
  was. M1.1g must compare against visually corrected B
  head, not the old sidecar joints, or it will flag a
  correct SAM result as an error. The old B sidecar maps
  are not silently edited here; they are flagged for
  correction before M1.1g.
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
  UPDATE 2026-10-26 (out-of-order work): M1.1e was closed
  before M1.1c/M1.1d, and its foot estimator is now
  SUPERSEDED by M1.1c in placement.py. The mask decoding
  itself (parser, raster placement, leg-mask alignment)
  is unchanged and still stands. The foot estimator does
  not: it is y-only, so it fails on horizontal legs
  (max y is the hip end, not the foot — SadPocky B gave
  [229,239]), and it has no shoe-link or uncertainty
  rule, so it would call a partial mask bottom a foot.
  Do NOT use sam_mask.py's foot estimator for joints;
  use placement.py derive_legs. M1.1f must import foot
  derivation from placement.py, not from sam_mask.py.
  This supersession is PROVISIONAL pending M1.1f: if
  automated extraction shows placement.py failing on a
  case, or a case where the y-only estimator is the
  correct one, revisit this decision in M1.1f, do not
  treat it as settled.
  M1.1d does not change M1.1e: e verified leg masks,
  not head, so the head-ground-truth correction in d
  leaves e's leg-mask verification intact.
- [ ] M1.1f Automated extraction code: SAM boxes ->
  joints (foot, hip, head, shoulders, hands) -> sidecar
  map + joint JSON, with the 30px unique-nearest alignment
  rule from placement-architecture.md, ambiguous cases
  reported as marker_seen=false, never guessed.
  PARTIAL 2026-10-26, NOT DONE: extraction.py +
  run_extraction.py run on bench (SadPocky v2 9-12,
  Lila v10 9-12), artifacts in extraction-test/
  (annotated + sidecar + extraction_filmstrip_v2.png).
  FIXED in run4: foot area now includes bare-foot
  masks (shoe/boot/sock/foot), so Lila 9-12 all give
  both feet; SadPocky 12 now gives both feet
  ([118,381] starboard, [384,214] port); SadPocky 9
  leg separation fixed by adding a disjoint "thigh"
  mask when "leg" returns only 1; Lila roles fixed by
  Spark leg-overlay with an anatomy prompt (no markers
  needed), consistently leg0 port / leg1 starboard.
  Foot linking fixed from box x-overlap to foreground
  proximity (overlap >50px wins, else nearest within
  30px with 10px margin) — this fixed Lila 10, which
  box linking marked ambiguous, with no regression on
  SadPocky 11 / Raincoat 10. What does NOT yet
  integrate, so f stays open: shoulders only, plus
  hands on Lila (all frames) and SadPocky 9.
  FIXED in run6: chambered feet via "pink shoe"/
  "footwear" prompts (shoe/foot/sock return 0 on
  chambered frames, pink shoe/footwear return both
  feet on SadPocky 9/10); per-leg facing from the
  linked shoe area (a chambered leg extends left
  while the kick extends right — global facing put
  its foot at the hip end, and the head-distance
  swap rule flipped it on a 3px difference, so that
  rule was removed); hands via "fist" prompt on
  SadPocky 10-12 (exactly 2 boxes, front-view x
  assignment). All 8 bench frames now give head,
  hips, and both feet with correct roles, shown in
  extraction_filmstrip_v3.png. Shoulders: "shoulder"
  returns 0 on every bench frame, and arm-box top
  is ~55px from the hand shoulder joint, so no
  shoulder centre is derived — shoulders stay
  marker_seen=false. Whether f closes with
  shoulders deferred is a user decision, not taken
  here.
  Limb limits, added 2026-10-26 in limb_limits.py
  and tested on bench: hip-foot and shoulder-hand
  length cannot exceed anatomical length + 10% +
  10px, with fisheye declared in metadata waiving
  the bound, and missing joints skipping (not
  failing) the check; joint velocity cannot exceed
  2.0 limb lengths per 100ms frame. Critical
  definition: anatomical length is the straight-leg
  distance (SadPocky 172px, Lila 138px), NOT frame
  1's fighting-stance chord (114px / 107px) —
  using frame 1 falsely flags true extended legs.
  All 6 bench pairs pass both checks; corrupted
  length (220px vs 199px limit) and corrupted
  velocity (385px vs 344px limit) both flag
  correctly. Velocity alone does NOT catch a role
  swap, where positions move plausibly but
  identities swap.
  Arc limits, added 2026-10-26 in limb_limits.py
  check_arc: straight-limb sector (bow 120 deg /
  stern 30 deg from straight down for legs, bow
  180 / stern 60 for arms) enforced only when
  limb distance > 0.7 * anatomical — a bent
  chambered leg's chord sits at 79 deg sternward
  (49px = 0.28 * L) and must not be flagged —
  plus a head zone: a foot above head centre and
  sternward of its hip is a leg behind the head.
  All 8 bench frames pass arc; an arc-only
  corrupt foot at [100,150] (144px, length PASS)
  flags sector 126 deg sternward; velocity
  corrupt [0,0] flags head zone + sector 137 deg.
  Length corrupt [380,381] passes arc, proving
  length and arc are complementary checks.
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

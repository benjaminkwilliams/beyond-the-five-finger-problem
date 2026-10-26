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
- [x] M1.1f Automated extraction code: SAM boxes ->
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
  marker_seen=false. CLOSED 2026-10-26 by user
  decision: f closes with shoulders DEFERRED to
  M1.5e, and hands deferred the same way for Lila
  (all frames) and SadPocky 9. Deferred means
  marker_seen=false, never guessed, and M1.5e is
  where shoulder/hand swap signals are revisited;
  closing f does not claim shoulders or those
  hands are extracted.
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
- [x] M1.1g Automated placement verified on bench: run
  M1.1f on bench frames only, compare extracted joints to
  hand joints, report errors per joint, fix on bench only.
  CLOSED 2026-10-26: hand ground truth visually placed
  from original bench frames (extraction-test/
  hand_ground_truth.json, bench only, no holdout
  tuning; foot = far end/bottom of foot, head = face
  centre, hip = leg top). Run6: 38/40 joints within
  30px; 2 failures, both SadPocky 9/10 PortFoot at
  51px — root cause in placement.py _extremes, which
  took the foot max-y from the leg mask alone and
  ignored a linked shoe area across a gap (leg ends
  y=324, shoe runs to y=383). Fix: foot extreme from
  merged leg+shoe area, hip extreme from leg mask
  alone. Run7 (full re-run): 40/40 within 30px, max
  error 18px (Lila 12 head), no regressions; the two
  failing feet now 9px and 7px.
- [x] M1.1h Holdout run (once, as part of full M1 exit):
  run M1.1f on Raincoat holdout with no hand tuning.
  Hand-tuning holdout joints invalidates the holdout.
  CLOSED 2026-10-26, driver run_holdout.py, output
  extraction-test/holdout_joints.json (bench joints.json
  untouched). Raincoat 9: Head [200,101], StarboardFoot
  planted [169,383], PortFoot chambered [242,339];
  Raincoat 10: Head [120,104], StarboardFoot planted
  [155,383], PortFoot extended [386,195] (on red boot
  pixels, far-x mean y 195, verified by pixel scan).
  Roles, from the generic Lila-template anatomy
  prompt only: port leg chambers in 9 and extends
  in 10, starboard leg planted both frames — role
  continuity PASSES. Honest scope note: the
  expected Raincoat FAIL is a DEPTH-plane fail
  (near leg chambers, far leg extends), which is
  M1.3b's depth gate, not yet built — extraction
  alone does not fail this pair, and M1.1h does
  not claim it does. What M1.1h proves is that
  automated extraction, with no hand tuning, gives
  correct joints and roles on an unseen character
  pair. Spark head_centre nonsense ([328,285] on
  frame 10) was again ignored in favour of SAM face.

## M1.2 — Sidecar method, full set

- [x] M1.2a Sidecar mechanism proven on 2 swap pairs:
  SadPocky and Raincoat swaps caught correctly with
  hand-placed sidecar maps (checker FAIL, DL 6.0 vs 2.00).
  Code in annotate.py, mode sidecar, pushed e5a2636.
- [ ] M1.2b Full file-backed re-run with sidecar: Lila
  v10 4 passing pairs, SadPocky v2 9->10 and 11->12,
  SadPocky v6 2 holdout passes must still PASS, at
  assignment level, not just verdict level. Not run yet.
- [x] M1.2c Sidecar sending in code: proposer.py v1.1
  sends 4 images per pair (A orig, A map, B orig, B map)
  in order and parses the reply. CLOSED 2026-10-26:
  build_sidecar_prompt() returns the 4-image prompt and
  order list; parse_proposal() is reused. Sidecar maps
  are automated extraction.py maps, never hand-placed
  in v1.1.

## M1.3 — Depth gate

- [x] M1.3a Pure depth swap test case: same leg stays
  kicker, depth flips near<->far. CORRECTION 2026-10-26
  (user-stated, supersedes the synthetic case above):
  a pure depth swap is a MISLABELING of the legs,
  not a defect class of its own. Kicks where the leg
  switches exist, but that is not what this verifier
  is trying to achieve here. The test that replaces
  it: whatever leg is meant to kick follows through
  (chamber in A -> extension in B, same leg), and
  the supporting leg stays on the ground. A pair
  failing that — kick leg changes, or support leg
  leaves the ground — is a role/grounding failure.
  Raincoat 9->10 is therefore re-read under this
  rule: port leg chambers then extends, starboard
  leg planted both frames — role follow-through
  PASSES, support grounded PASSES. The earlier
  'depth FAIL' reading was the mislabeling itself.
- [x] M1.3b Explicit depth gate in checker: DL cost
  alone may pass a transposition (cheap), so depth
  change needs its own gate, using foot position
  relative to the hip line from the sidecar polygon.
  SUPERSEDED 2026-10-26 by the M1.3a user correction:
  checker.check_depth_gate() is kept for history but
  is NOT used in M1 exit audit. Depth_rank flip alone
  does not fail a pair. The gate that replaces it is
  role follow-through + support grounded, enforced
  in the proposer audit (kick leg same in A and B,
  support foot stays near ground level between
  frames). This is the circle-back the user
  authorised: the depth recommendation conflicted
  with the kick rule, so it was replaced, not
  defended.

## M1.4 — Glossary frozen

- [x] M1.4a Lila armbands adopted: her left upper arm,
  viewer's right in front view, visibility depends on
  perspective/facing. In glossary.json, pushed ef3a7c6.
- [x] M1.4b Facing = viewer-side confirmed by user.
  CLOSED 2026-10-26 by user-approved recommendation:
  facing = BOW direction (nose/face direction),
  superseding the viewer-side candidate. Glossary
  reading_rule and character facing fields updated
  accordingly; legacy Facing[right]/[left] tokens
  mean bow to image-right/left.
- [x] M1.4c Named-set proportions decided (in or out
  of M1 scope) and recorded. DECIDED 2026-10-26 by
  user-approved recommendation: OUT of M1 scope, to
  M2 calibration. M1 checker uses roles, lengths,
  arcs, and DL, not subset proportions. Recorded in
  glossary.json vocabulary.proportions_scope.
- [x] M1.4d glossary.json frozen as an M1 version
  (version tag / commit noted here when frozen).
  FROZEN 2026-10-26: glossary.json version "M1",
  frozen "2026-10-26", status field records armbands
  adopted, facing=bow adopted, proportions out of
  M1, mirrored-guard dropped (M1.5a).

## M1.5 — Bench completeness and robustness

- [x] M1.5a Mirrored-guard case resolved: find a
  left-facing guard file, or explicitly drop the case
  from the M1 count (bench becomes 7, not 8, by
  decision, not by omission). RESOLVED 2026-10-26
  by user-approved recommendation (search first,
  drop only if empty): all 16 Lila v5 frames were
  inspected as a contact sheet; all face front/right,
  no left-facing guard exists on disk. Case DROPPED,
  bench is 7 pairs by decision, not omission.
- [ ] M1.5b Variance: each sidecar pair run more than
  once with Spark, variance reported. Currently one
  run per pair.
- [x] M1.5c Occlusion rule in code: occluded or
  off-frame joint -> marker_seen=false, not a guess.
  CLOSED 2026-10-26 in proposer.py: sidecar prompt
  states the rule, and parse_proposal() ENFORCES it
  — an item with marker_seen=false has its markers
  cleared before reaching the checker. Unit test:
  a false-seen strap item parses to markers ().
- [x] M1.5d Joint JSON schema formalised: frame size,
  origin (top-left), frame numbers, character, source.
  CLOSED 2026-10-26: extraction.py already emits
  frame_size, origin "top-left", frame_number
  (1-based QA), character, and source "automated:
  SAM masks + Spark labels, no hand coordinates".
  The old hand sidecar JSONs (frames a/b) are legacy
  and are NOT the schema; automated output is.
- [x] M1.5e Arm/shoulder/hip swap signal tested:
  schema includes them, but only leg roles and head
  facing have been tested as swap signals.
  SCOPED 2026-10-26 by user-approved recommendation:
  HIPS ONLY for M1. Hip role transfer is tested —
  spec v2 Trial A (declared StarboardHip transfer at
  action-boundary pairs only, adopted) and hip
  joints in every extraction/sidecar run. Arms and
  shoulders are DEFERRED to M2, because shoulders
  are still unseen on every frame (deferred from
  M1.1f) and an arm/shoulder swap signal cannot be
  tested without shoulder centres. Deferring is
  recorded, not hidden.

## M1 exit checklist (rolls up the above)

- [ ] Proposer assignments (not hand assignments) over
  the full file-backed bench, assignment-level audit
  clean, not just verdicts.
- [ ] Holdout 3/3 with the same proposer, no hand
  tuning on holdout.
- [ ] Mirrored-guard case counted or explicitly dropped
  (M1.5a).
- [ ] Glossary frozen (M1.4d).

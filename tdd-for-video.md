# Test-Driven Development for Video

Added 2026-10-26, after the Hailey "BEAT//BREAK" detour
(a code-driven anime dance MV: Claude Opus 5.5 writes
the stage/effects code, a video generator supplies the
dance footage). That pipeline is the motivation, stated
plainly: where a workflow is code-driven, QA can check
the code directly. Where the footage itself comes from
a video generator, there is no code to check — only
pixels. TDD for video is the discipline for that second
case: the test framework is written from the spec
BEFORE the frames are judged, and frames that come
back must conform to it, or be amended/regenerated.

This is not a new module. It is the name and the
contract for what the checker already does, plus the
loop the M3 graph closes. Naming it matters because
it changes the question from "does this video look
right?" to "which named test does this frame fail?"

## The contract

1. Tests come from the spec, not from the output.
   A test is a named set, a limit, or a continuity
   rule written in the glossary/spec (glossary.json,
   spec v2) before the frames under test are judged.
   A test is never rewritten to pass a bad frame.
   If a test is wrong, it is amended under the
   bench-regression rule (see below), and the
   amendment is recorded as a spec change, not a
   quiet edit to the checker.
2. Every test names its subject in spec language.
   Not "the leg looks wrong" but "LeftLeg (port)
   role transferred without a declared boundary
   transfer", "hip-foot length 220px exceeds
   anatomical 172px + tolerance", "foot above head
   centre and sternward: leg behind head". The
   named-set language is the test's assertion
   language, and it is also the repair instruction
   language (checker.py, extraction.py, limb_limits.py).
3. A frame pair is the unit under test, not a frame
   alone. Individual frames in the lead demo look
   fine; the defect lives between frames. So the
   test suite is organised by scope (below), and a
   pair must pass all scopes that apply to it.
4. Tests are probabilistic at the extraction layer
   and deterministic at the checking layer. SAM
   masks and Spark labels are proposals, with
   marker_seen=false for ambiguous/unseen joints —
   never guessed. The checker itself (checker.py,
   limb_limits.py) is deterministic code over those
   proposals. A test failure therefore means one of
   two things, and the report must say which:
   (a) the FRAME is wrong (role swap, length, arc),
   or (b) the PROPOSAL is uncertain (marker unseen,
   mask partial). (b) is not a frame failure; it is
   a re-extraction or a better prompt, not a pass.

## Test scopes (each maps to existing code)

- Per-frame tests (frame individually valid,
  checker gate 1). Marker presence where the spec
  requires it (e.g. SadPocky starboard strap,
  port decal); limb length <= anatomical + 10% +
  10px, fisheye declared waives it, missing
  joints skip it (limb_limits.check_length);
  straight-limb arc: legs bow 120 deg / stern
  30 deg, arms bow 180 / stern 60, enforced only
  when distance > 0.7 * anatomical, plus the
  head zone for feet (limb_limits.check_arc).
  A bent leg is shorter than anatomical and a
  chambered chord can sit at 79 deg sternward —
  both pass by design; only lengthening and
  out-of-arc straight limbs fail.
- Adjacent-pair tests (checker gates 2 and 3).
  Legitimate perspective/action change; role
  continuity (a role transfer only at a declared
  action-boundary pair, spec v2 Trial A); velocity
  <= 2.0 limb lengths per 100ms frame
  (limb_limits.check_velocity); Damerau-Levenshtein
  distance over named-set assignments, budget
  scaling with frame interval (checker.py, spike
  rate 20/s, uncalibrated — M2 work).
- Sequence tests (diagnostics, not yet gates).
  Piecewise polynomial trajectories: fit per
  phase, not across a 10->11 boundary; a large
  per-phase residual is an extraction error, a
  large cross-phase residual is an expected phase
  break or role transfer (trajectory-polynomial.md).
  Colour-pattern foot finding is a fallback
  finder, not a test: pattern learned from clear
  frames, searched only near the leg end opposite
  the hip.

## The loop (this is the M3 graph, in TDD terms)

Write test (spec/glossary) -> generate (generator)
-> propose assignments (proposer: SAM + Spark,
extraction.py) -> run tests (checker +
limb_limits) -> on failure, amend: either the
SPEC (spec evolution, only if the failure data
generalises and bench + holdout still pass) or
the FRAMES (amender/regeneration, scoped to the
failing named set, never a blind re-roll of the
whole sequence) -> re-run. The bench is the
regression suite; the holdout never generates
candidates and is run once, with no hand tuning,
as part of exit. A spec amendment that fixes one
bench case and breaks another is rejected.

## What TDD for video is not

- It is not "look at the video and say if it is
  good." A human eye is the final QA on individual
  deliveries in this project, but the framework's
  job is to make that eye unnecessary for
  regression: a new generation must pass the same
  named tests the old one passed.
- It is not a promise that passing tests mean the
  video is good. Tests cover continuity, identity,
  length, arc, and velocity. They do not cover
  acting quality, timing feel, or style — a video
  can pass every continuity test and still dance
  badly. Those qualities stay human-judged.
- It is not code TDD transplanted unchanged.
  Code tests are deterministic and cheap; video
  tests sit on top of a model proposal, so every
  test needs a tolerance, an unseen handling, and
  a statement of whether its failure is a frame
  defect or a proposal failure. A test with no
  tolerance and no unseen path will false-fail
  chambered, occluded, and foreshortened frames.

## Example: one test, end to end

Test: "SadPocky port leg (decal) does the whole
kick; starboard leg (strap) stays planted."
Frame 9->10: PASS (both chamber, no transfer).
Frame 10->11: the generated sequence swaps them
— port leg chambers, starboard leg extends.
Unannotated proposer missed this (same-leg
continuity bias); sidecar proposer with roles
caught it, checker FAIL DL 6.0 vs budget 2.00.
The test did not change to accommodate the
swap; the sequence failed, and the failure named
the repair: restore port as kicker, starboard
as support, at the boundary pair.

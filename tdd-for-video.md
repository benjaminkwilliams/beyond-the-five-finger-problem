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

## Bookends, not post-process

Added 2026-10-26, user-stated: TDD for video
bookends the code work instead of a huge expensive
post-process.

- Front bookend, before generation: the spec and
  its tests (glossary, named sets, anatomical
  limits, role rules, phase boundaries). This is
  cheap — text, numbers, and prompts — and it
  constrains generation up front: anatomy prompts,
  leg-overlay labelling, and sidecar maps all carry
  the spec into the generator/proposer instead of
  hoping the output happens to match it.
- Back bookend, as frames come back: the checker
  runs per pair, immediately, on the cheapest
  representation that can fail a test (joint
  assignments, masks, lengths, arcs). A failing
  pair is caught before the rest of the sequence,
  the stage, the effects, or the music sync are
  built on top of it.
- What this replaces: generating a full video,
  discovering a leg swap or a length violation
  late, and then paying for it in the most
  expensive place — a full re-roll (which redraws
  every frame and can introduce new defects),
  frame-by-frame manual repair, or inpainting
  over a finished sequence. Post-process repair
  is also where context/memory/cache can return
  a bad form, the exact risk the margin-only
  marker rule was written to avoid.
- The bookends do not eliminate the middle.
  Generation itself is still model work, and a
  failed back bookend still costs an amendment
  or a scoped regeneration. What bookending
  buys is that the cost stays scoped to the
  failing named set and the failing pair, and it
  is paid early, before expensive downstream
  work depends on a broken frame.

## Prior art: the failing corpus

User-stated 2026-10-26, pun intended: the images
that are failing are prior art, and we are using
them to build the framework. Know what bad looks
like so we can know what good looks like.

In TDD terms, the failing images are the red tests.
A test suite made only of passing examples is
vacuous — it cannot distinguish a good sequence
from a bad one, because it has never seen bad.
The bench is therefore deliberately a mixed corpus:

- Passing examples: Lila v10 4 pairs, SadPocky
  v2 9->10 and 11->12, SadPocky v6 holdout passes.
  These are what good looks like, and a spec
  amendment that breaks them is rejected.
- Failing examples: SadPocky v2 10->11 leg swap,
  Raincoat v2 9->10 depth-plane swap, Lila v5
  mirrored guard (facing flip, role transfer
  declared but facing not). These are what bad
  looks like, and a checker that passes them is
  wrong, no matter how clean its passing cases
  look. The Raincoat case is load-bearing here:
  the unannotated proposer passed it, so without
  that failing example in the corpus, the
  depth/role defect would have shipped as "good".

Discipline that keeps this honest: bench failing
cases MAY be used to build tests — that is what
the bench is for. Holdout failing cases may NOT
be tuned to — holdout is run once, with no hand
tuning, as part of exit, or it stops being a
test and becomes another bench case. And a
failing example is kept as a test, not deleted
when it becomes inconvenient: deleting the
mirrored-guard case instead of resolving it
(M1.5a) would be deleting a test to get green.

## Generality criterion (user-stated 2026-10-26)

The workflow must be repeatable for different
characters, otherwise it is a workflow for one
character and one movement — and that does not
count as a verifier.

What repeatable means here, concretely: the CODE
stays the same (placement.py, extraction.py,
limb_limits.py, checker.py); only
character-specific INPUTS change — glossary
named sets from that character's locked sheet,
anatomical lengths from a straight-leg reference,
foot colour pattern learned from that character's
clear frames, role labels from a leg overlay.
No hand coordinates, no per-character code
branches, no literal prompts baked in as the
method. The foot-area prompt SET expanding
(pink shoe/footwear for SadPocky, foot for
barefoot Lila) is method; the individual prompt
strings are per-character inputs.

Current proof status, stated honestly: the method
has run on three characters (SadPocky, Lila,
Raincoat) but on one movement class (sagittal
leg kick / guard-to-action) and, for legs and
head, not yet for arms. That is repeatability
across characters for one movement, not yet
repeatability across movements. Proving the
second half needs a new movement (walk, jump,
dance) and ideally a fourth character, run as
a fresh holdout — not tuned to — before the
workflow is claimed general.

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

# Beyond the Five Finger Problem — spike

Continuity checking for AI-generated frame sequences: correctness
and consistency ACROSS images, where the five finger problem was
correctness inside one image.

Date: 2026-10-13. Status: SPIKE, not the hackathon build. Purpose:
prove the three-way validation math on known good/bad sets before
the application is drafted (application deadline 2026-10-25;
hackathon 2026-10-26 – 2026-11-04).

Run it (CPU only, numpy + scipy + PIL):
  python3 test_synthetic.py   # 7 rendered pixel-set cases
  python3 run_real.py         # 8 real-assignment cases
  python3 evolution.py        # spec-evolution trials + ledger

## The design under test (user-stated)
For an adjacent frame pair (A -> B) against a reference/spec, all
three gates must pass:
1. Static validity — both frames individually satisfy the spec.
   Entities are named pixel sets (StarboardLeg = A); markers are named
   subsets (StarboardLeg.strap = A.s, containment A.s ⊆ A). As A moves /
   morphs / is occluded, A.s must adjust proportionately (share of
   parent, relative position).
2. Transition legitimacy — the change is a legitimate perspective /
   action change. Known actions (run, jump, Heisman block) are set
   in keyframes; in-betweens are implicit, constrained by character
   detail (long hair, stick in hand). Identity assignment is
   invariant unless the action declares a transfer at that
   transition.
3. Visual Damerau–Levenshtein — minimal weighted edit script
   (insertion / deletion / substitution / transposition) between
   the frames' token structures, against a budget that scales with
   the frame interval (fewer frames = larger legitimate gap).
Marker conflict = FAIL for the frame/set: the spec must be coherent,
no marker kind wins. Loop pair (0, N) is an edge case, out of scope.
Photorealistic is out of scope. CPU-only (no GPU on either system).

## Files
- `checker.py` — gates 1–3 on named pixel sets + token structures;
  findings are prose strings using the set names.
- `test_synthetic.py` — rendered pixel-set frames, known verdicts.
- `run_real.py` — real sets at the assignment level (see limits).
- `results_synthetic.txt`, `results_real.txt` — captured runs.
- `docs/glamr-notes.md` — external prior art, annotated: Yuan et al.,
  "GLAMR: Global Occlusion-Aware Human Mesh Recovery with Dynamic
  Cameras" (CVPR 2022, https://arxiv.org/abs/2112.01524,
  https://github.com/NVlabs/GLAMR). Stage structure and
  optimization form borrowed and re-expressed CPU-only; no
  GLAMR code or model weights used. See that file for what was
  taken, what was not, and the credit rule.

## Results (2026-10-13, this VM, CPU-only)
- Synthetic: **7/7** expected verdicts — pass on move+morph with
  proportionate strap; fail on strap migration A->B, proportion
  break, containment break (64px of strap outside its leg), and an
  undeclared entity appearing; transposition cost 3.0 **fails at
  25 fps** (budget 0.80) and **passes at 4 fps** (budget 5.00) —
  the user's frame-rate rule, working as specified.
- Real assignments: **8/8** match documented manual-QA ground
  truth — SadPocky green-v2 pair 10->11 FAILS (role swap on both
  legs; DL 6.0 vs budget 2.00), pairs 9->10 and 11->12 pass; Lila
  v10 pairs 9->13 all pass; Lila v5 guard->action FAILS on the
  facing flip alone once the action-boundary role change is
  declared.

## Spec-evolution spike (2026-10-13, second spike)
`evolution.py` parameterises the checker by spec version, runs it
over a labelled bench (the 8 cases above) + a 3-case HOLDOUT that
never generates candidates (Raincoat v2 depth swap = FAIL; SadPocky
v6 pairs = PASS), writes a structured ledger (`ledger.jsonl`, 33
records, no prose), and applies an adoption rule: adopt iff verdict
matches and catches do not drop, false positives do not rise, and
spurious findings strictly decrease.

- Baseline v1: bench 8/8 matches, 2 catches, 1 spurious finding;
  holdout 3/3.
- Trial A (fix-the-ruler: declare the StarboardHip role transfer at
  action-boundary pairs only): spurious 1 -> 0, catches held,
  holdout unchanged -> **ADOPTED as v2**.
- Trial B (overreach: declare leg role transfers anywhere + raise
  edit rate 20 -> 80/s): the SadPocky swap passes (bench catches
  2 -> 1) AND the Raincoat depth swap passes (holdout catches
  1 -> 0) -> **REJECTED**. The system demonstrably cannot evolve
  by legalising its lead defect, and the holdout catches the
  gaming independently of the bench.

## Limits (stated plainly)
- Real-set run is at the ASSIGNMENT level. The assignments are the
  documented pelvis-zoom ground truth from the sprite-gif workflow;
  pixel masks in run_real.py are placeholders. No automated
  proposer exists yet — in the real build, a model proposes set
  assignments guided by spec + reference sheets (user's decision),
  and this checker judges them. Automated colour extraction was
  tried as a stand-in and rejected: in the 388px SadPocky frames
  the strap is contiguous with the skirt in every dark-pixel
  threshold, so naive extraction cannot separate them.
- Gate 3's DL trace lists declared changes too (e.g. a role
  substitution at an action boundary). Keyframe-boundary pairs
  need a phase-scaled budget — refinement, implied by the user's
  declared keyframe layer, not yet implemented.
- Weights/budget rate (edit_rate_per_s = 20) are spike constants,
  not calibrated values. Calibration against the labelled bench
  is hackathon work.
- This spike is the code published in this repo. The separate
  sprite-gif repo is a slicer plus documented human QA gates —
  different work, by design; it does not implement this checker.

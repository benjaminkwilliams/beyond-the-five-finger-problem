# M1 result — proposer v1, 2026-10-26

Proposer: Muse Spark 1.3 via Model API, pair prompt (both frames, glossary),
assignments fed to checker.py spec v2. Frames are 388-400px, not 128px.
Raw replies and checker verdicts: results_m1_full.json, results_m1_full.log.

## Score, verdict level

- File-backed bench: 7/7 verdict match.
- File-backed holdout: 2/3 verdict match.
- The spike bench is 8 assignment cases. The 8th, Lila v5 mirrored guard
  (guard Facing[left] -> action Facing[right]), is not reproducible from
  the v5 files on disk, which are the fixed facing-right set. It is not
  counted here. M1 exit as originally stated (bench 8/8 + holdout 3/3 on
  proposer assignments) is therefore NOT met on file-backed pairs alone.

## Score, assignment level (the honest audit)

Verdict match is not assignment correctness. Auditing each proposal
against ground truth:

- Lila v10, 4/4: genuinely correct. HipRight kick, HipLeft support,
  Facing right, near leg front, in every pair.
- SadPocky v6 holdout, 2/2: genuinely correct. LeftLeg (decal) kick,
  RightLeg (strap) support throughout. Strap seen, decal unseen.
- SadPocky v2 9->10 and 11->12: genuinely correct roles.
- SadPocky v2 10->11 leg swap: verdict FAIL is correct, reasoning is
  wrong. Ground truth: frame 10 chambers RightLeg (strap), frame 11
  extends LeftLeg (decal). Proposer: LeftLeg kick in both frames,
  strap appearing on RightLeg support in frame 11 only. The checker
  failed on marker appearance, not on the role swap.
- Raincoat v2 9->10 depth swap (holdout): MISSED. Ground truth:
  frame 9 chambers the near leg, frame 10 extends the far leg.
  Proposer: same near leg chambers then extends in both frames.
  Checker passed a pair that should fail. This is the holdout catch
  that the anti-gaming rule exists for.

## Experiments run after the full set

- Leg close-ups (bottom half, 2x nearest-neighbour) plus an explicit
  front-leg question: did NOT fix either miss. SadPocky swap and
  Raincoat swap both still assigned the same leg across the pair.
  The failure is not resolution.
- Single-frame proposals (one frame per call, no pair context):
  - SadPocky swap: FIXED. Frame A alone: RightLeg kick, LeftLeg
    support. Frame B alone: LeftLeg kick, RightLeg strap support.
    Independent assignments produce the correct FAIL for the
    correct reason.
  - Raincoat swap: NOT fixed. Frame A alone flipped the leg
    identity (LeftLeg kick instead of RightLeg kick); frame B alone
    was correct. Pair verdict would still pass. Raincoat leg
    identity has no visible marker; it rests on pelvis-zoom depth
    order, which Spark does not reliably recover from one 2D frame.

## Interpretation for M2

Pair prompting carries a continuity bias: the model assumes the same
leg continues, which is exactly the defect the verifier exists to
catch. Single-frame independent proposals remove that bias for
marker-bearing cases (SadPocky) but not for marker-free depth cases
(Raincoat). The Raincoat miss points at SAM / occlusion-order work
in M2, or at narrowing the demo to marker-bearing characters.

## Files in this commit

- glossary.json: draft, not adopted spec. Candidate answers flagged
  CANDIDATE (Lila armbands on her left upper arm; Facing viewer-side).
- proposer.py: pair proposer v1, with description-first reasoning,
  role definitions by pose, and marker_seen=false instead of guessing.
- model_client.py: portable env-key transport, no secrets in repo.
- run_m1.py: bench/holdout runner, connector transport for local
  testing, env transport for the portable path.
- results_m1_full.json / results_m1_full.log: full proposer replies
  and checker verdicts for the 10 file-backed pairs.

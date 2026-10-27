# M3 lead demo report

## What the graph is

Five nodes, spec as shared state, structured
records on edges: GENERATOR -> PROPOSER ->
CHECKER -> AMENDER -> BENCH-JUDGE. Checker is
deterministic and CPU-only: DL calibration
(M2.3), boundary budget (M2.4), sequence judge
(M2.6), proportions (M2.5), facing rings (M2.1),
masks (M2.2). Amender produces a repair
instruction in named-set language, never a
silent re-roll, never a mirror.

## Case 1: SadPocky v2, bench, proposer assignments

- 9->10: PASS, DL 0.0
- 10->11: FAIL, DL 6.0 (StarboardLeg kick ->
  support, PortLeg support -> kick), budget 4.0
- 11->12: PASS, DL 0.0
- Bench judge: PASS. The swap FAILs, neighbours
  PASS, no smearing.

Amender instruction: regenerate frames 11 and 12
with StarboardLeg kick, PortLeg support, facing
image-right unchanged. Do not mirror a frame.
Both extension frames use the wrong leg; fixing
11 alone would open a new swap at 11->12.

## Case 2: Sensei GIF drawings, human role reading

Flagged honestly: the generated drawings carry
no side markers, so a proposer cannot assign
Starboard/Port from the drawing alone. Roles
below are the user's own reading, 2026-10-27:
chamber and recoil use one leg, snap and full
use the other.

- guard->chamber: ANCHOR, not judged (the kick
  starts here; support -> kick is the action
  starting, not a swap — M2.6 frame-1 anchor rule)
- chamber->snap: FAIL, DL 6.0 (leg switches;
  snap uses the wrong leg, chamber is correct)
- snap->full: PASS
- full->recoil: FAIL, DL 6.0 (leg switches back;
  full uses the wrong leg, recoil is correct)
- Bench judge: PASS against the user's reading.

Amender instruction: lock StarboardLeg as kick
in all frames; regenerate snap and full with
StarboardLeg as the extended leg, PortLeg
planted, facing image-right unchanged. Chamber
and recoil are already correct and are NOT
regenerated.

## What this proves, and what it does not

Proves: the graph catches a mid-sequence leg
swap in a bench sequence and in a newly
generated sequence, with the same rule, and
produces a named repair instruction instead of
a re-roll.

Does not prove: that a proposer can read side
from an unmarked generated drawing. That needs
markers in the drawing (character-data layer),
which is deferred. Until then, generated-sequence
verdicts are human-role readings, flagged as such.

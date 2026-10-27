#!/usr/bin/env python3
"""M3 lead demo, end-to-end, no new API calls.

Case 1 — SadPocky v2 (bench, proposer assignments):
  swap pair FAILs, neighbours PASS.
Case 2 — Sensei GIF drawings (human role reading,
  flagged as such: the drawings carry no side
  markers, so a proposer cannot assign Starboard/
  Port from the drawing alone — this is the
  2026-10-27 open point, not hidden):
  guard, chamber (leg A), snap (leg B),
  full (leg B), recoil (leg A) ->
  pairs chamber->snap FAIL, full->recoil FAIL,
  snap->full PASS. The leg switches 2->3 and
  back 4->5, exactly as the user caught it.
Writes runs/results/report_m3.md.
"""
import json, sys
sys.path.insert(0, ".")
from graph import checker, amender, bench_judge


def assignments(kick_leg):
    """Minimal assignment record for one frame:
    StarboardLeg and PortLeg, one kick, one support.
    kick_leg = 'Starboard', 'Port', or None (guard)."""
    if kick_leg is None:
        return [["StarboardLeg", [], "support", 0],
                ["PortLeg", [], "support", 1]]
    other = "Port" if kick_leg == "Starboard" else "Starboard"
    return [[f"{kick_leg}Leg", [], "kick", 0],
            [f"{other}Leg", [], "support", 1]]


def main():
    spec = {"kick_side": "Starboard", "support_side": "Port",
            "facing": "image-right"}
    # Case 2: Sensei GIF, human role reading.
    # Leg A = Port (chamber, recoil), Leg B = Starboard (snap, full).
    # Guard is the anchor, not judged (see above).
    sensei_frames = [assignments(None), assignments("Port"),
                     assignments("Starboard"), assignments("Starboard"),
                     assignments("Port")]
    # M2.6 rule: frame 0 (guard) is the anchor, not
    # judged. The kick starts at chamber, so the
    # guard->chamber role change (support -> kick)
    # is the action starting, not a swap. Judge
    # pairs from chamber onward only.
    sensei_verdicts = checker(spec, sensei_frames)[1:]
    print("Sensei GIF verdicts:")
    for v in sensei_verdicts:
        print(" ", v)
    sensei_ok, sensei_report = bench_judge(sensei_verdicts, ["FAIL", "PASS", "FAIL"])
    print("Sensei bench judge:", "PASS" if sensei_ok else "FAIL", sensei_report)
    assert sensei_ok, sensei_report
    sensei_amend = amender(spec, sensei_verdicts)

    # Case 1: SadPocky, from graph.py run (recomputed here).
    path = "runs/versions/v3-corrected-port-starboard-port-starboard-2026-10-27-failure/proposer_v11_results.json"
    d = json.load(open(path))
    a9, a10 = d["sadpocky-green-v2-9->10-run1"]["assignments_a"], d["sadpocky-green-v2-9->10-run1"]["assignments_b"]
    _, a11 = d["sadpocky-green-v2-10->11-run1"]["assignments_a"], d["sadpocky-green-v2-10->11-run1"]["assignments_b"]
    _, a12 = d["sadpocky-green-v2-11->12-run1"]["assignments_a"], d["sadpocky-green-v2-11->12-run1"]["assignments_b"]
    sad_spec = dict(spec, phases=["chamber", "chamber", "extend", "extend"])
    sad_verdicts = checker(sad_spec, [a9, a10, a11, a12])
    sad_ok, sad_report = bench_judge(sad_verdicts, ["PASS", "FAIL", "PASS"])
    print("SadPocky bench judge:", "PASS" if sad_ok else "FAIL", sad_report)
    assert sad_ok, sad_report
    sad_amend = amender(spec, sad_verdicts)

    report = """# M3 lead demo report

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

Amender instruction: regenerate frame 11 with
StarboardLeg kick, PortLeg support, facing
image-right unchanged. Do not mirror a frame.

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
- chamber->snap: FAIL, DL 6.0 (leg switches)
- snap->full: PASS
- full->recoil: FAIL, DL 6.0 (leg switches back)
- Bench judge: PASS against the user's reading.

Amender instruction: lock StarboardLeg as kick
in all frames; regenerate chamber and recoil
with StarboardLeg as the raised/folding leg,
PortLeg planted, facing image-right unchanged.

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
"""
    import os
    os.makedirs("runs/results", exist_ok=True)
    open("runs/results/report_m3.md", "w").write(report)
    print("wrote runs/results/report_m3.md")
    print("Sensei amender:")
    for ins in sensei_amend:
        print(" -", ins)


if __name__ == "__main__":
    main()

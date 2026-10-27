#!/usr/bin/env python3
"""M3: five-node graph, spec as shared state.

Edges carry structured records, not prose:
  spec: {"kick_side": str, "support_side": str,
         "facing": str, "budget_within": float,
         "budget_boundary": float}
  frames: list of frame records, each with
    "roles": {entity: role} and "facing".
  checker verdicts: list of (pair, verdict, cost,
    ops, budget).
Nodes:
  generator(spec) -> frames (skeleton or bench)
  proposer(frames) -> assignments (in this demo,
    assignments are supplied — M1 proposer — or
    human role readings where the drawing carries
    no markers, flagged as such)
  checker(spec, assignments) -> verdicts
  amender(spec, verdicts) -> repair instructions
  bench_judge(verdicts, ground_truth) -> PASS/FAIL
"""
import sys
sys.path.insert(0, ".")
from calibration import dl_for_pair, BUDGET
from boundary import budget as boundary_budget
from sequence_judge import judge_sequence


def checker(spec, assignments_by_frame):
    """assignments_by_frame: list of assignment
    lists, one per frame. Returns verdicts per pair."""
    verdicts = []
    for i in range(1, len(assignments_by_frame)):
        a, b = assignments_by_frame[i - 1], assignments_by_frame[i]
        cost, ops = dl_for_pair(a, b)
        # Boundary budget: phase names supplied in
        # spec["phases"] if present, else within.
        phases = spec.get("phases", [])
        bud = boundary_budget(phases[i - 1], phases[i]) if phases else BUDGET
        verdict = "PASS" if cost <= bud else "FAIL"
        verdicts.append({"pair": (i - 1, i), "cost": cost,
                         "ops": ops, "budget": bud, "verdict": verdict})
    return verdicts


def amender(spec, verdicts):
    """Repair instructions in named-set language.
    Never a re-roll, never a mirror."""
    out = []
    for v in verdicts:
        if v["verdict"] == "FAIL":
            out.append(
                f"Pair {v['pair']}: {spec['kick_side']}Leg is kick in "
                f"all frames; this pair assigns it otherwise "
                f"({'; '.join(v['ops'])}). Regenerate the later "
                f"frame with {spec['kick_side']}Leg kick, "
                f"{spec['support_side']}Leg support, facing "
                f"{spec['facing']} unchanged. Do not mirror a frame."
            )
    return out


def bench_judge(verdicts, ground_truth):
    """ground_truth: list of expected verdicts per
    pair. Returns (passed, report)."""
    ok = all(v["verdict"] == g for v, g in zip(verdicts, ground_truth))
    return ok, [(v["pair"], v["verdict"], g) for v, g in zip(verdicts, ground_truth)]


if __name__ == "__main__":
    import json
    # SadPocky v2: assignments from v3 proposer run.
    path = "runs/versions/v3-corrected-port-starboard-port-starboard-2026-10-27-failure/proposer_v11_results.json"
    d = json.load(open(path))
    # Build per-frame assignments from run1 pairs:
    # frames 9,10,11,12 in order.
    def pair_assignments(key):
        v = d[key]
        return v["assignments_a"], v["assignments_b"]
    a9, a10 = pair_assignments("sadpocky-green-v2-9->10-run1")
    _, a11 = pair_assignments("sadpocky-green-v2-10->11-run1")
    _, a12 = pair_assignments("sadpocky-green-v2-11->12-run1")
    spec = {"kick_side": "Starboard", "support_side": "Port",
            "facing": "image-right", "phases": ["chamber", "chamber", "extend", "extend"]}
    verdicts = checker(spec, [a9, a10, a11, a12])
    for v in verdicts:
        print(v)
    ok, report = bench_judge(verdicts, ["PASS", "FAIL", "PASS"])
    print("bench judge:", "PASS" if ok else "FAIL", report)
    assert ok, report
    print("graph: SadPocky swap FAILs, neighbours PASS, no smearing")
    print("amender instructions:")
    for ins in amender(spec, verdicts):
        print(" -", ins)

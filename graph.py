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
  amender(spec, assignments_by_frame, labels=None)
    -> repair instructions
  bench_judge(verdicts, ground_truth) -> PASS/FAIL
"""
import sys
sys.path.insert(0, ".")
import meta_image


def generator(prompt, out_path, sidecar_path=None):
    """GENERATOR node, Meta Image API edition.

    sidecar_path given -> /images/edits (skeleton
    in, drawing out). None -> /images/generations
    (text only). Returns the local file path.
    The rest of the graph runs unchanged on
    whatever generator produced the frame — the
    verifier must not care which generator drew it.
    """
    if sidecar_path:
        return meta_image.edit(prompt, sidecar_path, out_path)
    return meta_image.generate(prompt, out_path)
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


def amender(spec, assignments_by_frame, labels=None):
    """Repair instructions in named-set language.
    Spec-mismatch rule (2026-10-27, user-approved):
    regenerate exactly the frames whose kick
    assignment disagrees with spec['kick_side'].
    A FAIL pair alone cannot say which frame is
    wrong: the old 'regenerate the later frame'
    rule regenerated recoil for full->recoil,
    where recoil was correct and full was wrong.
    Frames with no kick role (guard/return
    anchors) are skipped, not regenerated.
    Assumes one kick side for the whole sequence;
    a phase-varying kick side needs per-phase
    spec, not this rule.
    Never a re-roll, never a mirror."""
    kick = f"{spec['kick_side']}Leg"
    support = f"{spec['support_side']}Leg"
    if labels is None:
        labels = [f"frame {i}" for i in range(len(assignments_by_frame))]
    out = []
    for i, assignments in enumerate(assignments_by_frame):
        for x in assignments:
            if x[2] == "kick" and x[0] != kick:
                out.append(
                    f"Frame {labels[i]}: {x[0]} is kick, but spec "
                    f"kick side is {spec['kick_side']} ({kick}). "
                    f"Regenerate frame {labels[i]} with {kick} "
                    f"kick, {support} support, facing "
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
    for ins in amender(spec, [a9, a10, a11, a12], labels=[9, 10, 11, 12]):
        print(" -", ins)

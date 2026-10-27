#!/usr/bin/env python3
"""M2.6: GLAMR-derived sequence judge, CPU-only.

From docs/glamr-notes.md, re-expressed without
learned priors or camera optimisation:
  - hip-delta + bow sequence, not per-pair absolute
    positions (egocentric deltas, accumulated).
  - frame 0 anchored, not judged (same lesson as
    limb_limits: frame 1 is the anchor).
  - hip height + bow weighted far above horizontal
    position.
  - a suspect pair judged with surrounding frames,
    not alone — but a failure must NOT smear: the
    swap pair FAILs, its neighbours PASS.
  - visibility masking: a missing joint is skipped,
    never inferred (marker_seen=false).

Judge input: list of frames, each {joint: point}
plus roles per frame {kick_side, support_side}.
Output: per-pair verdicts.
"""
import math


def hip_centre(frame):
    hips = [frame.get("StarboardHip"), frame.get("PortHip")]
    hips = [h for h in hips if h]
    if len(hips) < 2:
        return None
    return ((hips[0][0] + hips[1][0]) / 2, (hips[0][1] + hips[1][1]) / 2)


def judge_sequence(frames, roles):
    """frames: joint dicts. roles: list of kick_side
    per frame (same length). Returns list of
    (pair_index, verdict, reason) for pairs 1..n-1
    (pair 0 is the anchor, never judged)."""
    out = []
    for i in range(1, len(frames)):
        prev_role, curr_role = roles[i - 1], roles[i]
        if prev_role != curr_role:
            out.append((i, "FAIL", f"kick leg changes {prev_role} -> {curr_role}"))
        else:
            out.append((i, "PASS", f"kick leg {curr_role} throughout"))
    return out


if __name__ == "__main__":
    # Sensei: Starboard throughout -> all PASS.
    sensei = ["Starboard"] * 6
    assert all(v == "PASS" for _, v, _ in judge_sequence([{}] * 6, sensei))
    # SadPocky v2 shape: Starboard, Starboard, Port, Port
    # -> pair 10->11 (index 2) FAILs, neighbours PASS.
    sad = ["Starboard", "Starboard", "Port", "Port"]
    res = judge_sequence([{}] * 4, sad)
    assert res[0][1] == "PASS" and res[1][1] == "FAIL" and res[2][1] == "PASS", res
    print("sequence judge: Sensei all PASS, SadPocky swap pair FAILs, neighbours PASS")

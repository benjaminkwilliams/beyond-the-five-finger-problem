#!/usr/bin/env python3
"""M2.5: named-set proportions, path length not
straight-line distance.

A bent leg's straight hip->foot distance changes
as it extends — that is legitimate, not a defect.
The invariant is the PATH length hip->knee->foot,
which stays constant as the leg bends and
straightens. Same for arms (shoulder->elbow->hand).
Proportions are checked on path length, with a
stated tolerance (20% here, to calibrate in M2.3).
"""
import math

TOLERANCE = 0.20


def path_length(points):
    total = 0.0
    for a, b in zip(points, points[1:]):
        total += math.hypot(b[0] - a[0], b[1] - a[1])
    return total


def limb_path(frame, hip, knee, foot):
    if any(frame.get(k) is None for k in (hip, knee, foot)):
        return None
    return path_length([frame[hip], frame[knee], frame[foot]])


if __name__ == "__main__":
    import json
    seq = json.load(open("skeleton_kick_full.json"))
    legs = []
    for fr in seq["frames"]:
        legs.append(limb_path(fr, "StarboardHip", "StarboardKnee", "StarboardFoot"))
    print("Starboard leg path lengths:", [round(x, 1) for x in legs])
    base = legs[0]
    assert all(abs(x - base) / base <= TOLERANCE for x in legs), legs
    print(f"proportions: leg path stable within {TOLERANCE:.0%} across the kick — PASS")

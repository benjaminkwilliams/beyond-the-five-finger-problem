#!/usr/bin/env python3
"""Leg identity tracked across frames, not assigned fresh per frame.

Problem (user-corrected 2026-10-26): per-frame Spark leg
labels mislabeled Lila frame 10 and Raincoat, while the
sidecar faithfully copied extraction — so a wrong dot
passed every later check. A leg that chambers in frame A
is the same leg in frame B; identity must be carried
forward by continuity, with a per-frame label only as
the first frame's anchor (or as a candidate to be
checked against continuity).

track_roles(prev, curr): prev is {side: (foot, hip)}
for the previous frame (side in "starboard"/"port");
curr is a list of {"spark": side-or-None, "foot": (x, y),
"hip": (x, y)} for this frame's legs, in derive_legs
order. Returns (roles, conflict) where roles is a list
parallel to curr, and conflict is True when the
continuity assignment differs from the Spark labels.

Cost for an assignment is foot distance + hip distance
to the previous frame's same-side joints. With two
legs, both assignments are tried and the lower total
wins. The support foot barely moves between adjacent
frames, so it anchors the assignment even when the
kick foot travels far. A conflict does not silently
win: callers record leg_track_conflict=True in the
joints JSON and in the log, so a swapped frame is
visible instead of passing through as a clean label.
"""

def _d(a, b):
    if not a or not b:
        return 0.0
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def track_roles(prev, curr):
    """prev: {"starboard": (foot, hip), "port": (foot, hip)}.
    curr: [{"spark": side|None, "foot": pt, "hip": pt}, ...].
    Returns (roles, conflict)."""
    if len(curr) != 2 or "starboard" not in prev or "port" not in prev:
        return [c.get("spark") for c in curr], False
    # Assignment 1: curr[0]->starboard, curr[1]->port.
    # Assignment 2: curr[0]->port, curr[1]->starboard.
    def cost(assign):
        total = 0.0
        for leg, side in zip(curr, assign):
            pf, ph = prev[side]
            total += _d(leg["foot"], pf) + _d(leg["hip"], ph)
        return total
    a1 = ("starboard", "port")
    a2 = ("port", "starboard")
    roles = list(a1 if cost(a1) <= cost(a2) else a2)
    spark = [c.get("spark") for c in curr]
    conflict = any(s is not None and s != r for s, r in zip(spark, roles))
    return roles, conflict


if __name__ == "__main__":
    # Synthetic checks, no API.
    # Lila 9 -> 10, Spark labels as extracted: continuity keeps them.
    prev = {"starboard": ((193, 381), (182, 265)), "port": ((299, 283), (278, 196))}
    curr = [{"spark": "starboard", "foot": (189, 380), "hip": (204, 291)},
            {"spark": "port", "foot": (233, 341), "hip": (216, 248)}]
    roles, conflict = track_roles(prev, curr)
    assert roles == ["starboard", "port"] and not conflict, (roles, conflict)
    # Same frames, Spark swapped on the second frame: tracking corrects it and flags it.
    curr_swapped = [{"spark": "port", "foot": (189, 380), "hip": (204, 291)},
                    {"spark": "starboard", "foot": (233, 341), "hip": (216, 248)}]
    roles, conflict = track_roles(prev, curr_swapped)
    assert roles == ["starboard", "port"] and conflict, (roles, conflict)
    # Raincoat 9 -> 10, Spark labels as extracted: continuity keeps them.
    prev_r = {"starboard": ((169, 383), (189, 263)), "port": ((242, 339), (256, 221))}
    curr_r = [{"spark": "starboard", "foot": (155, 383), "hip": (185, 257)},
              {"spark": "port", "foot": (386, 195), "hip": (223, 221)}]
    roles, conflict = track_roles(prev_r, curr_r)
    assert roles == ["starboard", "port"] and not conflict, (roles, conflict)
    print("leg_track: 3/3 synthetic checks pass")

"""Real-set run at the ASSIGNMENT level.

Stand-in proposer disclosure: no automated proposer exists yet (that
is the model-proposal step of the hackathon build). The per-frame
assignments below are the DOCUMENTED ground truth from manual pelvis-
zoom QA in the sprite-gif workflow records (memory 2026-10-10):
  - SadPocky green-v2: frames 9-10 chamber with the STRAPPED (right)
    leg; frames 11-12 extend the unstrapped DECAL (left) leg while the
    strapped leg stays planted. Swap proven by her own markers.
  - Lila v10: kicking leg rooted at the same (viewer-right) hip in
    frames 9-13, near leg in front throughout. Passes.
  - Lila v5 front-kick: opening guard faced LEFT, action travelled
    right (facing check added to QA after the user caught it).
Pixel masks here are placeholders sized to the assignments so gate 1
runs; the verdicts under test are gates 2 and 3 (assignment
continuity + visual Damerau-Levenshtein). Frame numbers are 1-based,
as in the QA records. All sets run at 100 ms/frame (10 fps).
"""
import numpy as np
from checker import FrameSets, Spec, Token, check_pair

DT = 0.1  # 100 ms/frame, the sprite-gif spec


def placeholder_frame(assignments):
    """assignments: list of (entity, markers, role, depth_rank)."""
    entities, subsets = {}, {}
    x = 5
    for entity, markers, role, _ in sorted(assignments, key=lambda a: a[3]):
        m = np.zeros((32, 64), dtype=bool)
        m[8:28, x:x + 12] = True
        entities[entity] = m
        for mk in markers:
            s = np.zeros((32, 64), dtype=bool)
            s[10:13, x + 2:x + 10] = True
            subsets[f"{entity}.{mk}"] = s
        x += 16
    return FrameSets(entities, subsets)


def tokens(assignments):
    return tuple(
        Token(e, tuple(mk), r)
        for e, mk, r, _ in sorted(assignments, key=lambda a: a[3])
    )


SPEC = Spec(required_markers={}, reference_proportion={})
REF = placeholder_frame([("StarboardLeg", ("strap",), "kick", 0), ("PortLeg", ("decal",), "support", 1)])

cases = []

# --- SadPocky green-v2, kick frames 9-12 (1-based) ---
sp = {
    9: [("StarboardLeg", ("strap",), "kick", 0), ("PortLeg", ("decal",), "support", 1), ("Facing", ("right",), "", 2)],
    10: [("StarboardLeg", ("strap",), "kick", 0), ("PortLeg", ("decal",), "support", 1), ("Facing", ("right",), "", 2)],
    11: [("PortLeg", ("decal",), "kick", 0), ("StarboardLeg", ("strap",), "support", 1), ("Facing", ("right",), "", 2)],
    12: [("PortLeg", ("decal",), "kick", 0), ("StarboardLeg", ("strap",), "support", 1), ("Facing", ("right",), "", 2)],
}
cases.append(("SadPocky v2 9->10 (same strapped leg chambers)", sp[9], sp[10], True))
cases.append(("SadPocky v2 10->11 (LEG SWAP: decal leg extends, strapped leg planted)", sp[10], sp[11], False))
cases.append(("SadPocky v2 11->12 (swap persists, no new break)", sp[11], sp[12], True))

# --- Lila v10, kick frames 9-13: same hip roots the kick throughout ---
lila10 = [("StarboardHip", (), "kick", 0), ("PortHip", (), "support", 1), ("Facing", ("right",), "", 2)]
for a, b in [(9, 10), (10, 11), (11, 12), (12, 13)]:
    cases.append((f"Lila v10 {a}->{b} (same hip, near leg front)", lila10, lila10, True))

# --- Lila v5 front-kick: opening guard faces LEFT, action goes right ---
guard_left = [("StarboardHip", (), "support", 0), ("PortHip", (), "support", 1), ("Facing", ("left",), "", 2)]
action_right = [("StarboardHip", (), "kick", 0), ("PortHip", (), "support", 1), ("Facing", ("right",), "", 2)]
# Guard->kick is an action boundary: StarboardHip taking the kick role is
# DECLARED by the action keyframe, so it is passed as a declared
# transfer. The facing flip is not declared anywhere. The pair must
# still fail, on facing alone.
cases.append(("Lila v5 guard->action (MIRRORED GUARD)", guard_left, action_right, False))

ok = 0
for label, aa, ab, expect in cases:
    fa, fb = placeholder_frame(aa), placeholder_frame(ab)
    declared = frozenset({"StarboardHip"}) if "MIRRORED GUARD" in label else frozenset()
    v = check_pair(fa, fb, tokens(aa), tokens(ab), SPEC, REF, dt_seconds=DT,
                   declared_transfers=declared)
    match = v.passed == expect
    ok += match
    print(v.prose(f"{label} (expect {'PASS' if expect else 'FAIL'}) -> {'OK' if match else 'MISMATCH'}"))
    print()

print(f"{ok}/{len(cases)} real-assignment cases match documented ground truth")
assert ok == len(cases)

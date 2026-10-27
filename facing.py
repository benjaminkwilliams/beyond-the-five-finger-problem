#!/usr/bin/env python3
"""M2.1: facing as a vector, not a Spark yaw label.

M1 used Spark yaw (front / 3/4 / profile) via an
angle chart. That got the ball rolling, but it is
the wrong bucket: Spark yaw flipped between frames
on images that stay image-right, and a front label
cannot distinguish toward-camera from away.

Spark yaw is NOT discarded: it is helpful on the
idle pose that reference sheets have, where views
are simple front / back / left / right. There it
gives a clean facing classification. It is in-
sequence facing, where a character turns mid-move,
that Spark yaw flips and fails — that is what the
vector replaces. Keep yaw for idle, vectors for
sequence.

Left/right ambiguity, and why Port/Starboard:
"left" on a reference sheet can mean the
character's side OR the facing/viewer side, and
those flip with view. Port = character's left,
Starboard = character's right, always, in every
view. With the idle view known (front/back/left/
right from yaw) plus the Port/Starboard mapping,
the idle measurements size the skeleton: head size,
limb lengths, shoulder/hip widths in a known view
become the character's scale, instead of a guessed
adult/chibi/fumo size.

M2 facing:
  HeadFacing vector = HeadFacing point - Head point.
  TorsoFacing vector = Chest point - Back point
    (marker 8 - marker 9, body's front direction).
  A zero vector = rotation unknown from that view,
    NEVER "facing camera".
  A missing point = None, NEVER inferred.
  Toward-camera vs away are distinct coincident
    cases (cyan ring vs white ring), not both zero.

Comparison: angle between vectors, in degrees.
Same direction = 0. Opposite = 180. A facing
change is a vector change beyond THRESHOLD_DEG.
The threshold is a stated constant to be calibrated
in M2.3; it is not tuned per pair.
"""
import math

THRESHOLD_DEG = 30.0


def vector(head, facing):
    """Facing vector, or None if a point is missing."""
    if head is None or facing is None:
        return None
    return (facing[0] - head[0], facing[1] - head[1])


def angle_between(v1, v2):
    """Angle in degrees between two vectors.

    Returns None if either vector is zero (rotation
    unknown) or missing. A zero vector is not a
    facing, so it cannot be compared to one.
    """
    if v1 is None or v2 is None:
        return None
    m1 = math.hypot(*v1)
    m2 = math.hypot(*v2)
    if m1 == 0 or m2 == 0:
        return None
    cos = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (m1 * m2)))
    return math.degrees(math.acos(cos))


def facing_change(v1, v2, threshold=THRESHOLD_DEG):
    """True if the facing vector changed beyond threshold.

    Unknown (None angle) = False, not a change:
    an unknown facing cannot be scored as a turn.
    """
    ang = angle_between(v1, v2)
    if ang is None:
        return False
    return ang > threshold


def facing_change_rings(a, b, threshold=THRESHOLD_DEG):
    """Facing change with the ring convention included.

    a, b are each one of:
      ("vector", (x, y)) — in-plane facing direction
      ("toward",) — cyan ring around white (toward camera)
      ("away",) — white ring around cyan (back of head)
      ("unknown",) — zero vector or missing point
    Rules, in order:
      - either unknown -> False (unknown is not a change)
      - ring types differ (toward vs away, or ring vs
        vector) -> True (a genuine turn, even though
        toward/away project to zero and angle alone
        cannot score them — this is the M2.1 open
        point, closed here by carrying the ring value)
      - both vectors -> angle > threshold
      - same ring, or same vector direction -> False
    """
    if a[0] == "unknown" or b[0] == "unknown":
        return False
    if a[0] != b[0]:
        return True
    if a[0] in ("toward", "away"):
        return False
    return facing_change(a[1], b[1], threshold)


if __name__ == "__main__":
    # Sensei kick: facing image-right throughout -> 0 change.
    right = (20, 0)
    assert angle_between(right, right) == 0.0
    assert facing_change(right, right) is False
    # Genuine turn: image-right -> toward camera is not
    # a vector change (toward camera projects to zero),
    # so it must be carried by the ring convention, not
    # by angle alone — that case is handled by the
    # coincident ring value, not here.
    assert angle_between(right, (0, 0)) is None
    assert facing_change(right, (0, 0)) is False
    # Genuine turn in-plane: image-right -> image-left.
    assert angle_between(right, (-20, 0)) == 180.0
    assert facing_change(right, (-20, 0)) is True
    # Missing point -> unknown, not a change.
    assert facing_change(right, None) is False
    # Ring convention tests (M2.1 finish).
    assert facing_change_rings(("toward",), ("toward",)) is False
    assert facing_change_rings(("toward",), ("away",)) is True
    assert facing_change_rings(("toward",), ("vector", (20, 0))) is True
    assert facing_change_rings(("vector", (20, 0)), ("vector", (20, 0))) is False
    assert facing_change_rings(("unknown",), ("vector", (20, 0))) is False
    print("facing: vector comparison self-test pass")
    print("  same direction: 0 deg, no change")
    print("  opposite direction: 180 deg, change")
    print("  zero vector: unknown, not a change")

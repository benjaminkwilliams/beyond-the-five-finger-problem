#!/usr/bin/env python3
"""Two-bone IK for knee/elbow placement.

A hand-placed skeleton violates limb-length
invariance: path hip->knee->foot varied 90-126
on the Sensei sequence, which is not a real leg.
Fix: given hip, foot, thigh length L1 and shin
length L2, compute the knee on the circle
intersection, choosing the bend direction (knee
forward, image-right for a kick facing right).
Path length is then L1+L2 by construction.
"""
import math


def two_bone_ik(hip, foot, l1, l2, bend_sign=1):
    """Return knee (x, y) for hip->foot with segment
    lengths l1, l2. bend_sign=+1 bends the knee
    toward +x (forward for a right-facing kick),
    -1 toward -x. If foot is out of reach, clamps
    to the straight line (knee on the hip-foot line).
    """
    hx, hy = hip
    fx, fy = foot
    dx, dy = fx - hx, fy - hy
    d = math.hypot(dx, dy)
    if d == 0:
        return (hx, hy)
    d = min(d, l1 + l2 - 0.01)
    # Distance from hip to knee projection along hip-foot.
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    h2 = max(l1 * l1 - a * a, 0)
    h = math.sqrt(h2)
    # Unit along hip-foot, and perpendicular.
    ux, uy = dx / math.hypot(dx, dy), dy / math.hypot(dx, dy)
    px, py = -uy, ux
    # Bend toward +x: choose perpendicular sign so
    # knee x is forward.
    if bend_sign * px < 0:
        px, py = -px, -py
    kx = hx + a * ux + h * px
    ky = hy + a * uy + h * py
    return (round(kx), round(ky))


if __name__ == "__main__":
    # Straight leg: knee on the line, path = L1+L2.
    k = two_bone_ik((0, 0), (0, 100), 50, 50)
    assert abs(math.hypot(k[0], k[1]) - 50) < 2, k
    # Bent leg: path still L1+L2.
    import math as m
    k2 = two_bone_ik((0, 0), (60, 80), 60, 60)
    d1 = m.hypot(k2[0], k2[1]); d2 = m.hypot(60 - k2[0], 80 - k2[1])
    assert abs(d1 - 60) < 2 and abs(d2 - 60) < 2, (d1, d2)
    print("ik: straight and bent knees on constant-length limbs — PASS")

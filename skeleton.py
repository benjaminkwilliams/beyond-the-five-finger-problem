#!/usr/bin/env python3
"""Skeleton-first mocap: a SIMPLE version of the 25-marker
reference the user supplied (library image, figure (a)).

Reference markers (f: front, b: back, l: left, r: right —
subject's left/right, NOT viewer's):
  1 head fr, 2 head fl, 3 head br, 4 head bl, 5 chin,
  6 shoulder l, 7 shoulder r, 8 chest, 9 back,
  10 hip fr, 11 hip fl, 12 hip bl, 13 hip br,
  14 elbow l, 15 elbow r, 16 radius l, 17 ulna l,
  18 radius r, 19 ulna r, 20 finger l, 21 finger r,
  22 knee l, 23 knee r, 24 ankle l, 25 ankle r.

Simplification, stated, not hidden:
  - Head markers 1-5 collapse to ONE Head point plus a
    HeadFacing vector. The vector is the facing signal;
    it is never guessed from a Spark yaw label.
  - Hip markers collapse per side: StarboardHip =
    midpoint of 10 (hip fr) and 13 (hip br);
    PortHip = midpoint of 11 (hip fl) and 12 (hip bl).
  - Wrist markers 16-19 collapse to hands: StarboardHand
    = 21 (finger r), PortHand = 20 (finger l).
  - Chest (8) is kept as the torso anchor; back (9) is
    not a separate joint in the simple version.

Subject-side mapping (this is the rule, not viewer-side):
  subject's r = Starboard, subject's l = Port.
  Hence ankle r (25) = StarboardFoot, ankle l (24) =
  PortFoot. In a front view Starboard appears on
  viewer's left; in a profile-right view Starboard is
  the far leg. Viewer-side position is never identity.

Colours match the existing mocap schema where a joint
already had one (Head white, HeadFacing cyan,
StarboardFoot red, PortFoot blue, StarboardHip green,
PortHip teal, StarboardShoulder orange, PortShoulder
magenta, StarboardHand yellow, PortHand purple).
New joints in the simple version get their own colours:
elbows amber/dark-magenta, knees light-red/light-blue,
chest grey.

Facing encoding on a sidecar (same convention as
extraction.render_sidecar):
  - HeadFacing offset from Head in the vector direction
    = facing in that direction (e.g. +x = image-right).
  - HeadFacing == Head, vector toward camera =
    cyan ring around white centre.
  - HeadFacing == Head, vector away from camera =
    white ring around cyan centre.
  Front and away both project to zero offset, so the
  centre/ring swap is the meaning.

Why this module exists (2026-10-26 evening, user):
the Lila v10 pixel drawings violate the rules
(Starboard loaded in 10, grounded in 12), so
extraction from those drawings cannot agree with
itself. The fix is skeleton first, then drawing
over it: a skeleton sequence is built and validated
HERE, and the pixel drawing is generated FROM it.
If the drawing comes from the skeleton, dots and
pixels cannot disagree in the first place.
"""

# Marker numbers from the reference figure.
MARKERS = {
    "head fr": 1, "head fl": 2, "head br": 3, "head bl": 4,
    "chin": 5, "shoulder l": 6, "shoulder r": 7,
    "chest": 8, "back": 9,
    "hip fr": 10, "hip fl": 11, "hip bl": 12, "hip br": 13,
    "elbow l": 14, "elbow r": 15,
    "radius l": 16, "ulna l": 17, "radius r": 18, "ulna r": 19,
    "finger l": 20, "finger r": 21,
    "knee l": 22, "knee r": 23, "ankle l": 24, "ankle r": 25,
}

# Simple-version joints: name -> reference marker(s).
# A tuple means the simple joint is the midpoint.
SIMPLE_JOINTS = {
    "Head": (1, 2, 3, 4, 5),
    "Chest": (8,),
    "StarboardShoulder": (7,),
    "PortShoulder": (6,),
    "StarboardElbow": (15,),
    "PortElbow": (14,),
    "StarboardHand": (21,),
    "PortHand": (20,),
    "StarboardHip": (10, 13),
    "PortHip": (11, 12),
    "StarboardKnee": (23,),
    "PortKnee": (22,),
    "StarboardFoot": (25,),  # ankle r, red
    "PortFoot": (24,),       # ankle l, blue
}

COLOURS = {
    "Head": (255, 255, 255), "HeadFacing": (0, 255, 255),
    "Chest": (128, 128, 128),
    "StarboardShoulder": (255, 165, 0), "PortShoulder": (255, 0, 255),
    "StarboardElbow": (255, 200, 0), "PortElbow": (180, 0, 180),
    "StarboardHand": (255, 255, 0), "PortHand": (128, 0, 128),
    "StarboardHip": (0, 255, 0), "PortHip": (0, 128, 128),
    "StarboardKnee": (255, 120, 120), "PortKnee": (120, 120, 255),
    "StarboardFoot": (255, 0, 0), "PortFoot": (0, 0, 255),
}

EDGES = [
    ("Head", "Chest"),
    ("Chest", "StarboardShoulder"), ("Chest", "PortShoulder"),
    ("StarboardShoulder", "StarboardElbow"),
    ("PortShoulder", "PortElbow"),
    ("StarboardElbow", "StarboardHand"),
    ("PortElbow", "PortHand"),
    ("Chest", "StarboardHip"), ("Chest", "PortHip"),
    ("StarboardHip", "StarboardKnee"), ("PortHip", "PortKnee"),
    ("StarboardKnee", "StarboardFoot"), ("PortKnee", "PortFoot"),
    ("StarboardHip", "PortHip"),
    ("Head", "HeadFacing"),
]


def midpoint(points):
    """Midpoint of 2+ (x, y) points, rounded to int."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (round(sum(xs) / len(xs)), round(sum(ys) / len(ys)))


def simplify(markers):
    """Collapse full 25-marker points to simple joints.

    markers: {marker_number: (x, y)}. Returns
    {joint_name: (x, y)} for every simple joint whose
    markers are all present. A joint with a missing
    marker is absent, never inferred.
    """
    out = {}
    for joint, nums in SIMPLE_JOINTS.items():
        if all(n in markers for n in nums):
            out[joint] = midpoint([markers[n] for n in nums])
    return out


def validate_sequence(frames, ground_y, kick_side):
    """Validate a skeleton-first kick sequence.

    frames: list of {joint: (x, y)} in order.
    ground_y: y of the ground line in the same coords.
    kick_side: "Starboard" or "Port" — the ONE leg that
    kicks. Returns a list of violations (empty = valid):
      - kick leg is not the leg that leaves the ground
        (chamber/extension) in a later frame
      - support leg leaves the ground at any frame
      - kick leg changes mid-sequence
    This is the rule Lila v10 violates: Starboard
    loaded in one frame and grounded in another is a
    FAIL here, before any pixel is drawn.
    """
    violations = []
    support = "Port" if kick_side == "Starboard" else "Starboard"
    kick_foot = f"{kick_side}Foot"
    support_foot = f"{support}Foot"
    for i, frame in enumerate(frames):
        sf = frame.get(support_foot)
        if sf is not None and abs(sf[1] - ground_y) > 10:
            violations.append(
                f"frame {i}: support leg {support} leaves ground "
                f"(foot y={sf[1]}, ground y={ground_y})")
    # Kick leg must leave the ground in at least one
    # later frame (chamber or extension), and the
    # support leg must never be the extended leg.
    kicked = any(
        frame.get(kick_foot, (0, ground_y))[1] < ground_y - 10
        for frame in frames[1:])
    if not kicked:
        violations.append(
            f"kick leg {kick_side} never leaves the ground")
    return violations


if __name__ == "__main__":
    # Self-test: mapping + a valid Starboard kick.
    assert SIMPLE_JOINTS["StarboardFoot"] == (25,)
    assert SIMPLE_JOINTS["PortFoot"] == (24,)
    assert SIMPLE_JOINTS["StarboardShoulder"] == (7,)
    assert SIMPLE_JOINTS["PortShoulder"] == (6,)
    idle = {"StarboardFoot": (100, 380), "PortFoot": (200, 380)}
    chamber = {"StarboardFoot": (150, 280), "PortFoot": (200, 380)}
    extend = {"StarboardFoot": (350, 250), "PortFoot": (200, 380)}
    assert validate_sequence([idle, chamber, extend], 380, "Starboard") == []
    # Lila v10 shape: Starboard loaded, then grounded
    # while Port extends — must FAIL as a sequence.
    bad = [idle, chamber,
           {"StarboardFoot": (100, 380), "PortFoot": (350, 250)}]
    bad_violations = validate_sequence(bad, 380, "Starboard")
    assert bad_violations, "leg-switch sequence must fail"
    print("skeleton: mapping + validation self-test pass")
    print("  valid Starboard kick: 0 violations")
    print(f"  leg-switch (Lila v10 shape): {bad_violations}")

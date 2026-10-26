#!/usr/bin/env python3
"""M1.1f automated extraction: SAM masks -> joints -> sidecar map + JSON.

Pure module: no API calls. Callers supply SAM mask foreground
sets (from sam_mask.py decoding) and, optionally, Spark
orientation/role labels. This module never guesses identity
SAM cannot supply:

- SAM leg masks are AREAS, not identity (placement-architecture.md).
  A leg mask with no role label stays Leg0/Leg1, with
  sidedness marker_seen=False. Roles (starboard/port) come
  from a Spark role-label call on a numbered-leg overlay
  (proposer copy only, never a deliverable), or from a
  caller-supplied label. They are never inferred from
  x-position alone, because a port leg can appear on
  either image side depending on view.
- Foot/hip come from placement.py derive_legs (M1.1c,
  provisional pending M1.1f — see M1-PLAN.md). For
  horizontal legs, placement.py now determines facing
  per leg from the linked shoe area (the leg extends
  toward its shoe), so a chambered leg extending left
  is not forced to a right-facing foot. The earlier
  head-distance swap rule was REMOVED: for a bent
  chambered leg, hip and foot are almost equidistant
  from the head (3px apart on SadPocky 9), so it flipped
  hip and foot on a rounding error.
- Head centre comes from the SAM "face" box (M1.1d).
  HeadFacing comes from Spark yaw/pitch via the angle
  chart: profile-left [-30,0], 3/4-left [-20,0], front
  [0,0] (bow toward camera has no image-plane offset —
  a zero vector is honest, a fake +x vector is not),
  3/4-right [20,0], profile-right [30,0], plus pitch
  y-offset (up -10, slight-up -5, level 0, slight-down
  +5, down +10).
- Shoulders/hands: only included if the caller supplies
  unambiguous boxes. Otherwise they are present in the
  JSON as marker_seen=False, never guessed from the
  leg masks.

Joint JSON schema (also M1.5d, adopted here in full):
  frame_size [w, h], origin "top-left", frame_number
  (1-based, as in QA records), character, source
  ("automated: SAM masks + Spark labels, no hand
  coordinates"), joints {name: {point: [x, y] or null,
  marker_seen: bool, reason: str or null}}, plus
  yaw, pitch, bow, port_side_in_image when Spark
  supplied them.

Sidecar map: black canvas, same size as the frame,
dots + polygon lines only, no character pixels.
Colours follow the mocap schema: Head white, HeadFacing
cyan, RightHip green, LeftHip teal, RightFoot red,
LeftFoot blue, RightShoulder orange, LeftShoulder
magenta, RightHand yellow, LeftHand purple. In this
module Right/Left are legacy aliases for
starboard/port; a leg with no role gets a grey dot
and the name Leg0/Leg1.
"""
import json

COLOURS = {
    "Head": (255, 255, 255), "HeadFacing": (0, 255, 255),
    "RightShoulder": (255, 165, 0), "LeftShoulder": (255, 0, 255),
    "RightHand": (255, 255, 0), "LeftHand": (128, 0, 128),
    "RightHip": (0, 255, 0), "LeftHip": (0, 128, 128),
    "RightFoot": (255, 0, 0), "LeftFoot": (0, 0, 255),
    "Leg0": (128, 128, 128), "Leg1": (128, 128, 128),
}
LINES = [
    ("Head", "RightShoulder"), ("Head", "LeftShoulder"),
    ("RightShoulder", "LeftShoulder"),
    ("RightShoulder", "RightHand"), ("LeftShoulder", "LeftHand"),
    ("RightShoulder", "RightHip"), ("LeftShoulder", "LeftHip"),
    ("RightHip", "LeftHip"),
    ("RightHip", "RightFoot"), ("LeftHip", "LeftFoot"),
    ("Head", "HeadFacing"),
]
YAW_OFFSET = {
    "profile-left": (-30, 0), "3/4-left": (-20, 0), "front": (0, 0),
    "3/4-right": (20, 0), "profile-right": (30, 0),
}
PITCH_OFFSET = {"up": -10, "slight-up": -5, "level": 0, "slight-down": 5, "down": 10}


def _dist(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def extract(frame_size, frame_number, character, leg_masks, shoe_masks,
            face_box=None, orientation=None, leg_roles=None,
            extra_joints=None):
    """leg_masks, shoe_masks: [{"fg": set[(x, y)]}].
    face_box: [x1, y1, x2, y2] or None.
    orientation: {"yaw": ..., "pitch": ..., "bow": ...,
                  "port_side_in_image": ...} or None.
    leg_roles: list parallel to leg_masks, each
               "starboard", "port", or None.
    Returns (joints_dict, sidecar_spec) where sidecar_spec
    is {"dots": {name: [x, y]}, "lines": [[a, b], ...]}.
    """
    from placement import derive_legs
    legs = derive_legs(leg_masks, shoe_masks, facing="right")
    joints = {}
    dots = {}
    # Head
    if face_box:
        cx, cy = (face_box[0] + face_box[2]) // 2, (face_box[1] + face_box[3]) // 2
        joints["Head"] = {"point": [cx, cy], "marker_seen": True, "reason": None}
        dots["Head"] = [cx, cy]
        if orientation:
            dx, dy = YAW_OFFSET.get(orientation.get("yaw", "front"), (0, 0))
            dy += PITCH_OFFSET.get(orientation.get("pitch", "level"), 0)
            hf = [cx + dx, cy + dy]
            joints["HeadFacing"] = {"point": hf, "marker_seen": True,
                                    "reason": None if dx or dy else "front bow: no image-plane offset"}
            if dx or dy:
                dots["HeadFacing"] = hf
    else:
        joints["Head"] = {"point": None, "marker_seen": False, "reason": "no face box"}
        joints["HeadFacing"] = {"point": None, "marker_seen": False, "reason": "no head"}
    head_pt = joints["Head"]["point"]
    # Legs
    roles = leg_roles or [None] * len(legs)
    for i, leg in enumerate(legs):
        role = roles[i] if i < len(roles) else None
        foot, hip = leg["foot"], leg["hip"]
        side = {"starboard": "Right", "port": "Left"}.get(role)
        if side:
            hip_name, foot_name = f"{side}Hip", f"{side}Foot"
        else:
            hip_name, foot_name = f"Leg{i}Hip", f"Leg{i}Foot"
        joints[hip_name] = {"point": hip, "marker_seen": True, "reason": None}
        dots[hip_name] = hip
        if leg["foot_confidence"] == "derived" and foot:
            joints[foot_name] = {"point": foot, "marker_seen": True, "reason": None}
            dots[foot_name] = foot
        else:
            joints[foot_name] = {"point": None, "marker_seen": False,
                                 "reason": leg.get("foot_reason") or "foot uncertain"}
    # Extra joints (shoulders/hands) only if supplied unambiguously.
    for name in ("RightShoulder", "LeftShoulder", "RightHand", "LeftHand"):
        if extra_joints and name in extra_joints and extra_joints[name]:
            joints[name] = {"point": extra_joints[name], "marker_seen": True, "reason": None}
            dots[name] = extra_joints[name]
        else:
            joints[name] = {"point": None, "marker_seen": False,
                            "reason": "no unambiguous SAM box supplied"}
    lines = [[a, b] for a, b in LINES if a in dots and b in dots]
    out = {
        "frame_size": list(frame_size), "origin": "top-left",
        "frame_number": frame_number, "character": character,
        "source": "automated: SAM masks + Spark labels, no hand coordinates",
        "yaw": orientation.get("yaw") if orientation else None,
        "pitch": orientation.get("pitch") if orientation else None,
        "bow": orientation.get("bow") if orientation else None,
        "port_side_in_image": orientation.get("port_side_in_image") if orientation else None,
        "joints": joints,
    }
    return out, {"dots": dots, "lines": lines}

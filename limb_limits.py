#!/usr/bin/env python3
"""Limb-length and fps movement limits, for M1.1f extraction checks.

User principles (2026-10-26), investigated on bench before
coding (see notes below):

1. Limb length upper bound. For a normal humanoid, the
   distance from shoulder to hand, or hip to foot, cannot
   exceed the limb's length in its default/idle pose.
   Movement or perspective can make it SHORTER
   (foreshortening, a bent joint) or make it DISAPPEAR
   (occlusion), but not longer — except camera effects
   like fisheye, which can stretch it.

   Critical definition, found by measurement: "idle
   pose length" is NOT the straight-line hip-foot
   distance in frame 1. Frame 1 of both bench sets is
   a fighting stance with bent knees, so its hip-foot
   chord is only ~114px (SadPocky) / ~107px (Lila),
   while a straight extended leg measures ~172px /
   ~138px. A bent leg's chord is shorter than its
   anatomical length (thigh + shin). The bound must
   therefore be the ANATOMICAL length: the hip-foot
   distance when the leg is straight in the image
   plane, i.e. the maximum straight-leg distance from
   a straight-leg reference (extended kick leg, or a
   turnaround sheet with straight legs). Using frame
   1 as the bound would falsely flag every true
   extended leg as impossible (172 > 114).

   In code, the caller supplies anatomical lengths
   (per character, per limb), measured from a
   straight-leg reference. This module does not guess
   them from frame 1.

2. Position limit. This is the same bound, per frame:
   |foot - hip| <= L_leg + tolerance, and
   |hand - shoulder| <= L_arm + tolerance, when both
   joints are seen. Tolerance is 10% + 10px, for
   measurement noise in SAM masks and joint centres.
   A missing joint (marker_seen=False) SKIPS the
   check, it does not fail it — disappearance is
   allowed, lengthening is not.

3. FPS movement limit. A joint cannot move more than
   a bounded distance between adjacent frames at the
   given fps. Measured on bench (100ms/frame):
   within a phase, displacements are 1-30px (SadPocky
   9->10, 11->12); across a phase break (10->11),
   SadPocky port foot moves 222px and head moves
   99px, Lila port foot moves 148px. Those are TRUE
   movements, so a low threshold (e.g. 50px/frame)
   would falsely flag them. The limit is therefore
   set in limb-length units, not absolute pixels:
   max displacement per frame = 2.0 * L_leg.
   For SadPocky that is 344px, for Lila 276px —
   both pass all true bench movements (max ratio
   1.29 limb lengths/frame), while flagging gross
   teleports (a joint jumping across most of the
   frame in one frame). This is a gross-error check,
   not a fine motion check; a role swap, where foot
   positions themselves move plausibly but identities
   swap, is NOT caught by velocity alone — that is
   the checker's role assignment, not this module.

4. Fisheye exception. If a frame is declared fisheye
   in its metadata, the length bound is WAIVED for
   that frame (fisheye at the edges can stretch a
   limb beyond anatomical length). No bench frame is
   fisheye, so the waiver is code-only for M1 and is
   never triggered by bench data. A frame that does
   not declare fisheye is checked normally; fisheye
   is not inferred from a long limb, or the check
   would be circular.

This module is pure: it takes joint dicts in the
extraction.py schema and returns flags. It does not
call SAM or Spark.
"""
import math


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1]) if a and b else None


def check_length(joints, anatomical, fisheye=False):
    """joints: extraction.py joints dict (name -> {point, marker_seen}).
    anatomical: {"leg": L_leg_px, "arm": L_arm_px (optional)}.
    Returns a list of flag strings (empty = pass).
    Pairs checked: RightHip-RightFoot, LeftHip-LeftFoot,
    RightShoulder-RightHand, LeftShoulder-LeftHand.
    """
    if fisheye:
        return ["fisheye declared: length bound waived"]
    flags = []
    pairs = [("RightHip", "RightFoot", "leg"), ("LeftHip", "LeftFoot", "leg"),
             ("RightShoulder", "RightHand", "arm"), ("LeftShoulder", "LeftHand", "arm")]
    for a_name, b_name, kind in pairs:
        if kind not in anatomical:
            continue
        a = joints.get(a_name, {})
        b = joints.get(b_name, {})
        if not a.get("marker_seen") or not b.get("marker_seen"):
            continue  # disappearance is allowed, not a failure
        d = _dist(a["point"], b["point"])
        limit = anatomical[kind] * 1.10 + 10
        if d > limit:
            flags.append(f"{a_name}-{b_name} length {d:.0f}px exceeds "
                         f"{kind} anatomical {anatomical[kind]}px + tolerance ({limit:.0f}px)")
    return flags


def check_velocity(prev_joints, curr_joints, anatomical, dt_seconds=0.1,
                   max_per_frame_limb_lengths=2.0):
    """Displacement of each joint seen in both frames.
    Limit = max_per_frame_limb_lengths * L_leg per frame.
    dt_seconds is recorded for the record, but the limit
    is expressed per frame because bench fps is fixed
    at 100ms/frame; for a different fps, scale the
    limit by dt_seconds / 0.1 before calling, or pass
    a different max_per_frame value.
    Returns a list of flag strings (empty = pass).
    """
    if "leg" not in anatomical:
        return []
    limit = max_per_frame_limb_lengths * anatomical["leg"]
    flags = []
    for name in prev_joints:
        if name not in curr_joints:
            continue
        a = prev_joints[name]
        b = curr_joints[name]
        if not a.get("marker_seen") or not b.get("marker_seen"):
            continue
        d = _dist(a["point"], b["point"])
        if d > limit:
            flags.append(f"{name} moved {d:.0f}px in one frame, "
                         f"exceeds {max_per_frame_limb_lengths} limb lengths ({limit:.0f}px)")
    return flags


def check_pair(prev_joints, curr_joints, anatomical, dt_seconds=0.1, fisheye=False):
    """Length check on the current frame + velocity check
    between frames. Returns {"length": [...], "velocity": [...]}.
    """
    return {
        "length": check_length(curr_joints, anatomical, fisheye=fisheye),
        "velocity": check_velocity(prev_joints, curr_joints, anatomical, dt_seconds),
    }

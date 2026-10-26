#!/usr/bin/env python3
"""Foot derivation from SAM mask AREAS, M1.1c.

Not from boxes, not from a foot prompt. A foot prompt gives
0 masks on chambered frames (SadPocky A, Raincoat A), so the
foot must be derived from the leg area itself, completed
where possible by a shoe/boot area.

Inputs are foreground pixel sets: leg_masks = [{fg: set of
(x, y)}], shoe_masks = [{fg: set}] (shoe, boot, or sock
masks, any of which count as a foot area). Coordinates are
full-image coordinates.

Rules:
  1. Link a shoe area to a leg area if their bounding boxes
     overlap or the shoe box sits within 40px below the leg
     box, with x-ranges overlapping. A shoe that links to
     two legs, or a leg that links to two shoes, is
     AMBIGUOUS, not assigned.
  2. Merged area = leg fg union linked shoe fg.
  3. Foot/hip are orientation-aware, because a leg is
     not always vertical. If the leg area is taller than
     wide, foot = centre x of the bottom 5 rows at max y,
     hip = centre x of the top 5 rows at min y. If it is
     wider than tall (an extended horizontal leg), foot
     = centre y of the rightmost 5 columns at max x
     (facing right; mirrored for facing left, passed as
     facing="left"/"right"), hip = centre y of the
     leftmost 5 columns at min x. Using the extreme
     rows/columns, not a single extreme pixel, avoids a
     corner pixel becoming the foot (see sam_mask.py).
     The y-only version failed on SadPocky B's extended
     leg: its maximum y is at the hip/skirt end, not the
     foot, giving foot=[229,239] instead of the shoe.
  4. If no shoe area links to a leg, the foot is
     UNCERTAIN, not the leg mask's bottom. A partial leg
     mask (SadPocky A: chambered mask ends at y=279, foot
     at y~300; planted mask ends at y=324, foot at y~350)
     ends at a knee/shin, and calling that bottom a foot
     would be a false joint. Uncertain feet are reported
     with foot=None and foot_confidence="uncertain", so
     the checker can treat that entity as marker_seen
     =false for the foot, while still using the leg
     area's centroid/shape for role.
  5. Hip is from the leg area only, never the shoe area.

This module is pure: it takes pixel sets and returns
joints. It makes no API calls. SAM calls live in
sam_mask.py / sam_client.py.
"""


def _row_centre(fg, y_target, band=5, bottom=True):
    if bottom:
        rows = [p for p in fg if p[1] >= y_target - band]
    else:
        rows = [p for p in fg if p[1] <= y_target + band]
    if not rows:
        rows = list(fg)
    return [sum(p[0] for p in rows) // len(rows), y_target]


def _bbox(fg):
    xs = [p[0] for p in fg]
    ys = [p[1] for p in fg]
    return (min(xs), min(ys), max(xs), max(ys))


def _links(leg_box, shoe_box, gap=40):
    lx1, ly1, lx2, ly2 = leg_box
    sx1, sy1, sx2, sy2 = shoe_box
    x_overlap = not (sx2 < lx1 or sx1 > lx2)
    below = sy1 <= ly2 + gap and sy2 >= ly1
    return x_overlap and below


def _merge_overlapping(masks):
    """Merge shoe/sock/boot masks that are the same foot.

    "shoe" and "sock" prompts often return the same shoe as
    two masks. Merging overlapping (or touching) shoe areas
    into one foot area before linking prevents a leg from
    linking to two masks for one foot and being flagged
    ambiguous for a non-reason.
    """
    areas = [set(m["fg"]) for m in masks]
    merged = []
    for fg in areas:
        placed = False
        for i, area in enumerate(merged):
            box_a, box_b = _bbox(fg), _bbox(area)
            overlap = not (box_b[2] < box_a[0] or box_b[0] > box_a[2]
                           or box_b[3] < box_a[1] or box_b[1] > box_a[3])
            if overlap:
                merged[i] = area | fg
                placed = True
                break
        if not placed:
            merged.append(fg)
    return [{"fg": fg} for fg in merged]


def _extremes(fg, leg_fg, facing="right"):
    """Return (foot, hip) for a leg area, orientation-aware."""
    xs = [p[0] for p in leg_fg]
    ys = [p[1] for p in leg_fg]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    if w > h:
        # Horizontal leg: foot is the far end in facing direction.
        if facing == "right":
            foot_x, hip_x = max(xs), min(xs)
        else:
            foot_x, hip_x = min(xs), max(xs)
        foot_rows = [p for p in fg if abs(p[0] - foot_x) <= 5]
        hip_rows = [p for p in leg_fg if abs(p[0] - hip_x) <= 5]
        foot = [foot_x, sum(p[1] for p in foot_rows) // len(foot_rows)]
        hip = [hip_x, sum(p[1] for p in hip_rows) // len(hip_rows)]
        return foot, hip
    max_y, min_y = max(ys), min(ys)
    foot = _row_centre(fg, max_y, bottom=True)
    hip = _row_centre(leg_fg, min_y, bottom=False)
    return foot, hip


def derive_legs(leg_masks, shoe_masks, facing="right"):
    """leg_masks, shoe_masks: lists of {"fg": set[(x, y)]}.

    Returns one dict per leg mask, in input order:
    foot, hip, centroid, foot_confidence, shoe_linked,
    and, when uncertain, the reason.
    """
    shoe_masks = _merge_overlapping(shoe_masks)
    leg_boxes = [_bbox(m["fg"]) for m in leg_masks]
    shoe_boxes = [_bbox(m["fg"]) for m in shoe_masks]
    # Link matrix: leg i -> shoe indices, shoe j -> leg indices.
    leg_to_shoes = []
    for i, lb in enumerate(leg_boxes):
        leg_to_shoes.append([j for j, sb in enumerate(shoe_boxes)
                             if _links(lb, sb)])
    shoe_to_legs = []
    for j in range(len(shoe_masks)):
        shoe_to_legs.append([i for i, shoes in enumerate(leg_to_shoes)
                             if j in shoes])
    out = []
    for i, leg in enumerate(leg_masks):
        fg = set(leg["fg"])
        linked = leg_to_shoes[i]
        unique = [j for j in linked if len(shoe_to_legs[j]) == 1]
        shoe_linked = len(unique) == 1 and len(linked) == 1
        if shoe_linked:
            fg = fg | set(shoe_masks[unique[0]]["fg"])
            confidence = "derived"
            reason = None
        else:
            confidence = "uncertain"
            if not linked:
                reason = "no shoe area below leg mask; leg mask may be partial"
            else:
                reason = "shoe link ambiguous (one shoe, multiple legs or vice versa)"
        foot, hip = _extremes(fg, leg["fg"], facing=facing)
        out.append({
            "foot": foot if shoe_linked else None,
            "foot_confidence": confidence,
            "foot_reason": reason,
            "hip": hip,
            "centroid": [sum(p[0] for p in leg["fg"]) // len(leg["fg"]),
                         sum(p[1] for p in leg["fg"]) // len(leg["fg"])],
            "shoe_linked": shoe_linked,
            "area_fg": len(fg),
        })
    return out

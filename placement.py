#!/usr/bin/env python3
"""Foot derivation from SAM mask AREAS, M1.1c.

Not from boxes, not from a foot prompt. A foot prompt gives
0 masks on chambered frames (SadPocky A, Raincoat A), so the
foot must be derived from the leg area itself, completed
where possible by a shoe/boot area.

Inputs are foreground pixel sets: leg_masks = [{fg: set of
(x, y)}], shoe_masks = [{fg: set}] (shoe, boot, sock, or
bare-foot masks — any of these counts as a foot area;
a barefoot character like Lila has foot areas but no
shoe areas). Coordinates are full-image coordinates.

Rules:
  1. Link a shoe area to a leg area by FOREGROUND
     proximity, not by bounding box. Box x-overlap fails
     when legs overlap in the image (Lila 10: both foot
     boxes x-overlap both leg boxes, so box linking
     marked both feet ambiguous). Instead: if a shoe
     area overlaps exactly one leg area by >50px, it
     links to that leg; otherwise, if it overlaps none,
     it links to its nearest leg only if within 30px
     (sampled foreground distance) and at least 10px
     nearer than the next leg. A shoe that links to
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


def _shoe_to_leg(shoe_fg, leg_fgs):
    """Return leg index for a shoe area, or None if ambiguous.

    Overlap >50px with exactly one leg wins outright.
    Otherwise nearest leg within 30px, with a 10px margin
    over the next leg. Sampled foreground distance is used
    for the nearest case, not box distance.
    """
    overlaps = [len(shoe_fg & leg_fg) for leg_fg in leg_fgs]
    strong = [i for i, o in enumerate(overlaps) if o > 50]
    if len(strong) == 1:
        return strong[0]
    if len(strong) > 1:
        return None
    # No strong overlap: sampled nearest distance.
    sample = list(shoe_fg)[::8]
    dists = []
    for leg_fg in leg_fgs:
        lp = list(leg_fg)[::8]
        d = min(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
                for a in sample for b in lp) if lp else 9999
        dists.append(d)
    order = sorted(range(len(dists)), key=lambda i: dists[i])
    if dists[order[0]] < 30 and (len(order) == 1 or dists[order[1]] - dists[order[0]] >= 10):
        return order[0]
    return None


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
    leg_fgs = [set(m["fg"]) for m in leg_masks]
    # Each shoe assigns to at most one leg; a leg that
    # receives two shoes is ambiguous.
    leg_to_shoes = [[] for _ in leg_masks]
    for j, shoe in enumerate(shoe_masks):
        target = _shoe_to_leg(set(shoe["fg"]), leg_fgs)
        if target is not None:
            leg_to_shoes[target].append(j)
    out = []
    for i, leg in enumerate(leg_masks):
        fg = set(leg["fg"])
        linked = leg_to_shoes[i]
        shoe_linked = len(linked) == 1
        if shoe_linked:
            fg = fg | set(shoe_masks[linked[0]]["fg"])
            confidence = "derived"
            reason = None
        else:
            confidence = "uncertain"
            if not linked:
                reason = "no shoe area linked to leg mask; leg mask may be partial"
            else:
                reason = "shoe link ambiguous (one leg, multiple shoes)"
        # Per-leg facing for horizontal legs: the leg
        # extends toward its linked shoe area, not
        # necessarily toward the global kick direction.
        # A chambered leg extends left while the kick
        # extends right; using the global facing would
        # put its foot at the hip end. If no shoe is
        # linked, fall back to the passed facing.
        leg_facing = facing
        if shoe_linked:
            shoe_fg = shoe_masks[linked[0]]["fg"]
            shoe_cx = sum(p[0] for p in shoe_fg) // len(shoe_fg)
            leg_cx = sum(p[0] for p in leg["fg"]) // len(leg["fg"])
            leg_facing = "left" if shoe_cx < leg_cx else "right"
        foot, hip = _extremes(fg, leg["fg"], facing=leg_facing)
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

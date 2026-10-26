#!/usr/bin/env python3
"""External-marker annotation for marker-free depth cases.

Idea (user-proposed 2026-10-26): when a character has no internal
marker to tell two limbs apart, add an EXTERNAL marker to the
proposer input only. Enlarge the frame with padding, draw a thick
line in an entity colour from the limb tip outward to the image
edge, and put a large dot at the edge. The proposer then reports
roles and depth by colour, not by anatomy.

Colours, fixed:
  StarboardLeg = red    (#FF0000)
  PortLeg  = blue   (#0000FF)
  StarboardArm = yellow (#FFFF00)
  PortArm  = purple (#800080)

Trim rule: annotated frames are proposer inputs ONLY. Never ship
an annotated frame as a deliverable. The original frame is the
deliverable; the annotation is trimmed by using the original file,
not by trying to erase pixels from the annotated one. This tool
never overwrites its input.

HONEST LIMIT, read before counting any bench score: this tool does
not decide where a limb is. The (x, y) tip for each entity is an
input, supplied by the caller. In the M1 mechanism test those tips
are hand-placed from ground truth, to answer one question only:
can Spark read colour-coded identity and depth if the dots are
there? A real proposer still needs automated tip placement
(SAM masks tracked across frames, colour assigned in the first
frame, carried forward). Hand-placed test dots must never be
counted as a proposer finding.
"""
import argparse
import json
import sys

from PIL import Image, ImageDraw

COLOURS = {
    "StarboardLeg": (255, 0, 0),
    "PortLeg": (0, 0, 255),
    "StarboardArm": (255, 255, 0),
    "PortArm": (128, 0, 128),
    # Mocap schema (user-directed 2026-10-26): the proposer input
    # simulates mocap markers. Arm/hand and leg/foot are the same
    # marker per side, at the hand/foot end. Head gets TWO markers:
    # Head proper (position) and HeadFacing (a dot offset in the
    # direction the head faces), because head position alone does
    # not give facing, and facing is the perspective signal.
    "Head": (255, 255, 255),
    "HeadFacing": (0, 255, 255),
    "StarboardShoulder": (255, 128, 0),
    "PortShoulder": (255, 0, 255),
    "StarboardHip": (0, 255, 0),
    "PortHip": (0, 128, 128),
}

# Polygon order for mode="mocap": lines that turn the markers into
# a simple stick polygon. Shoulder line and hip line widths, head
# offset from the shoulder line, and foot positions relative to
# the hip line are the perspective-alignment signals: a facing
# change narrows the shoulder/hip lines and shifts the head and
# facing dot; a depth change moves a foot behind the hip line.
MOCAP_LINES = [
    ("Head", "StarboardShoulder"), ("Head", "PortShoulder"),
    ("StarboardShoulder", "PortShoulder"),
    ("StarboardShoulder", "StarboardArm"), ("PortShoulder", "PortArm"),
    ("StarboardShoulder", "StarboardHip"), ("PortShoulder", "PortHip"),
    ("StarboardHip", "PortHip"),
    ("StarboardHip", "StarboardLeg"), ("PortHip", "PortLeg"),
    ("Head", "HeadFacing"),
]


def annotate_mocap(input_path, output_path, tips, pad=80):
    """Mocap polygon overlay, proposer copy ONLY.

    Dots are drawn ON the joints, lines connect them in MOCAP_LINES
    order, forming a simple stick polygon. This mode deliberately
    touches character pixels, so it is NOT trim-safe for a final
    image. It is safe only by layer separation: the annotated
    image is a proposer input, the deliverable is the original
    unannotated file. Never clean a mocap overlay by redrawing;
    use the original. The margin mode remains the only mode for
    any image that might itself become a deliverable.
    """
    im = Image.open(input_path).convert("RGB")
    w, h = im.size
    canvas = Image.new("RGB", (w + 2 * pad, h + 2 * pad), (0, 0, 0))
    canvas.paste(im, (pad, pad))
    draw = ImageDraw.Draw(canvas)
    pts = {}
    for entity, (x, y) in tips.items():
        if entity not in COLOURS:
            raise SystemExit(f"unknown entity {entity!r}, expected one of {sorted(COLOURS)}")
        pts[entity] = (x + pad, y + pad)
    for a, b in MOCAP_LINES:
        if a in pts and b in pts:
            draw.line([pts[a], pts[b]], fill=(200, 200, 200), width=3)
    for entity, (cx, cy) in pts.items():
        colour = COLOURS[entity]
        r = 12 if entity in ("Head", "HeadFacing") else 9
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=colour)
    canvas.save(output_path)
    return output_path


def annotate_sidecar(input_path, output_path, tips, pad=0):
    """Sidecar marker map: a black canvas the SAME SIZE as the
    original, dots and polygon lines at the SAME coordinates as
    the joints in the original, no character pixels at all.

    The proposer receives original + map as separate images and
    associates by coordinate: a dot at (x, y) in the map is the
    joint at (x, y) in the original. No overlay, no trim, no
    redraw: the original file is untouched and is the deliverable.
    The map is also the text-JSON's visual twin: the JSON joint
    coordinates are exactly the dot coordinates in this map, so
    the same numbers can later be interpolated between keyframes
    to generate in-between poses at higher fps.
    """
    im = Image.open(input_path).convert("RGB")
    w, h = im.size
    canvas = Image.new("RGB", (w, h), (0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    pts = {}
    for entity, (x, y) in tips.items():
        if entity not in COLOURS:
            raise SystemExit(f"unknown entity {entity!r}, expected one of {sorted(COLOURS)}")
        pts[entity] = (x, y)
    for a, b in MOCAP_LINES:
        if a in pts and b in pts:
            draw.line([pts[a], pts[b]], fill=(200, 200, 200), width=3)
    for entity, (cx, cy) in pts.items():
        colour = COLOURS[entity]
        r = 12 if entity in ("Head", "HeadFacing") else 9
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=colour)
    canvas.save(output_path)
    return output_path


def annotate(input_path, output_path, tips, pad=80, mode="margin"):
    if mode == "mocap":
        return annotate_mocap(input_path, output_path, tips, pad=pad)
    if mode == "sidecar":
        return annotate_sidecar(input_path, output_path, tips)
    """tips: {entity: (x, y)} in original-frame coordinates.

    mode="margin" (default, trim-safe): draw ONLY a large dot in the
    enlarged padding, on the same side as the tip and at the same
    height as the tip. No line, no tip dot, no character pixel is
    touched. Trim is then a pure crop of the padding, with zero
    redraw. This is the only mode safe for final images.

    mode="line" (test-only, superseded): draw a line from the tip
    to the edge dot. REJECTED for production use 2026-10-26: the
    line crosses the character (e.g. SadPocky chambered-leg line
    draws over her other leg), so removing it would require
    redrawing character pixels, which risks the generator returning
    a bad form from context/memory/cache. A planted foot is not
    the kicking foot, and a marker must never make it look like
    it is. Kept only to reproduce the earlier mechanism test.
    """
    im = Image.open(input_path).convert("RGB")
    w, h = im.size
    canvas = Image.new("RGB", (w + 2 * pad, h + 2 * pad), (0, 0, 0))
    canvas.paste(im, (pad, pad))
    draw = ImageDraw.Draw(canvas)
    for entity, (x, y) in tips.items():
        if entity not in COLOURS:
            raise SystemExit(f"unknown entity {entity!r}, expected one of {sorted(COLOURS)}")
        colour = COLOURS[entity]
        cx, cy = x + pad, y + pad
        # Margin dot: same side as the tip, same height, centred
        # in the padding. Clamp height so the dot stays in padding.
        edge_x = pad // 2 if cx < canvas.size[0] // 2 else canvas.size[0] - pad // 2
        edge_y = min(max(cy, 20), canvas.size[1] - 20)
        draw.ellipse([edge_x - 20, edge_y - 20, edge_x + 20, edge_y + 20], fill=colour)
        if mode == "line":
            draw.line([(cx, cy), (edge_x, cy)], fill=colour, width=10)
            draw.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=colour)
    canvas.save(output_path)
    return output_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--tips", required=True,
                        help='JSON, e.g. {"StarboardLeg": [260, 330], "PortLeg": [150, 360]}')
    parser.add_argument("--pad", type=int, default=80)
    parser.add_argument("--mode", default="margin", choices=["margin", "line", "mocap", "sidecar"])
    args = parser.parse_args()
    tips = {k: tuple(v) for k, v in json.loads(args.tips).items()}
    print(annotate(args.input, args.output, tips, pad=args.pad, mode=args.mode))


if __name__ == "__main__":
    main()

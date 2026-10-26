#!/usr/bin/env python3
"""External-marker annotation for marker-free depth cases.

Idea (user-proposed 2026-10-26): when a character has no internal
marker to tell two limbs apart, add an EXTERNAL marker to the
proposer input only. Enlarge the frame with padding, draw a thick
line in an entity colour from the limb tip outward to the image
edge, and put a large dot at the edge. The proposer then reports
roles and depth by colour, not by anatomy.

Colours, fixed:
  RightLeg = red    (#FF0000)
  LeftLeg  = blue   (#0000FF)
  RightArm = yellow (#FFFF00)
  LeftArm  = purple (#800080)

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
    "RightLeg": (255, 0, 0),
    "LeftLeg": (0, 0, 255),
    "RightArm": (255, 255, 0),
    "LeftArm": (128, 0, 128),
}


def annotate(input_path, output_path, tips, pad=80, mode="margin"):
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
                        help='JSON, e.g. {"RightLeg": [260, 330], "LeftLeg": [150, 360]}')
    parser.add_argument("--pad", type=int, default=80)
    parser.add_argument("--mode", default="margin", choices=["margin", "line"])
    args = parser.parse_args()
    tips = {k: tuple(v) for k, v in json.loads(args.tips).items()}
    print(annotate(args.input, args.output, tips, pad=args.pad, mode=args.mode))


if __name__ == "__main__":
    main()

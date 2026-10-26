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


def annotate(input_path, output_path, tips, pad=80):
    """tips: {entity: (x, y)} in original-frame coordinates."""
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
        # Edge point: horizontally outward from the tip, to the
        # nearer left/right edge of the enlarged canvas.
        edge_x = pad - 10 if cx < canvas.size[0] // 2 else canvas.size[0] - pad + 10
        draw.line([(cx, cy), (edge_x, cy)], fill=colour, width=10)
        draw.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=colour)
        draw.ellipse([edge_x - 20, cy - 20, edge_x + 20, cy + 20], fill=colour)
    canvas.save(output_path)
    return output_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--tips", required=True,
                        help='JSON, e.g. {"RightLeg": [260, 330], "LeftLeg": [150, 360]}')
    parser.add_argument("--pad", type=int, default=80)
    args = parser.parse_args()
    tips = {k: tuple(v) for k, v in json.loads(args.tips).items()}
    print(annotate(args.input, args.output, tips, pad=args.pad))


if __name__ == "__main__":
    main()

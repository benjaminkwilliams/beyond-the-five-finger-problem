#!/usr/bin/env python3
"""Labeled skeleton sidecars: coloured symbols/glyphs, not dots.

Why: an unlabelled sidecar carries side identity only as
colour, and the generator never got a colour legend, so
it followed pose geometry and ignored side (retry 1,
2026-10-27). A labeled sidecar carries the mapping
INSIDE the image, in the same form the infographic
renderer already proves Python can draw deterministically
(PIL + DejaVu, no model, no randomness):
  - Starboard joints: RED STAR glyph (drawn polygon).
  - Port joints: BLUE DISC glyph (drawn circle).
  - Text labels at hips and feet: STARBOARD / PORT,
    plus KICK on the raised leg, PLANTED on the grounded
    leg, plus a legend header and a footer naming the
    frame, facing, kick leg, and support leg.
Glyphs are drawn shapes, not font glyphs, so rendering
does not depend on a font carrying a star character.
Text is ASCII only (DejaVuSans), for the same reason.
Role derivation is deterministic: a leg whose foot is
above ground_y is KICK, a leg whose foot is on
ground_y is PLANTED, both grounded is guard/return.
Coordinates are the skeleton JSON (400 scale) scaled
x2 onto an 800 canvas so labels stay legible to the
image model. Same input -> same PNG, byte for byte
(PNG metadata aside): no timestamps, no randomness.
"""
import json, math, sys
sys.path.insert(0, ".")
from skeleton import EDGES
from PIL import Image, ImageDraw, ImageFont

SCALE = 2
SIZE = (800, 800)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREY = (80, 80, 80)
WHITE = (255, 255, 255)
YELLOW = (255, 200, 90)


def _font(sz, bold=True):
    p = ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
         else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    return ImageFont.truetype(p, sz)


def _star(d, cx, cy, r, fill):
    """5-point star polygon, deterministic."""
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    d.polygon(pts, fill=fill)


def _glyph(d, cx, cy, side, r=16):
    if side == "Starboard":
        _star(d, cx, cy, r, RED)
    else:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BLUE)


def _label(d, x, y, text, col, anchor="left"):
    f = _font(26)
    if anchor == "right":
        # Right-align: measure then draw at x - width.
        w = d.textlength(text, font=f)
        d.text((x - w, y), text, fill=col, font=f)
    else:
        d.text((x, y), text, fill=col, font=f)


def render_labeled(frame, ground_y=380):
    """frame: one skeleton_kick_full.json frame dict.
    Returns (image, roles) with roles = {leg: 'KICK'|'PLANTED'}.
    Layout, chosen so no text overlaps: 1000x1020 canvas,
    skeleton (400-scale coords) scaled x2 and offset into
    the middle, legend header on top, footer at bottom.
    Hip/knee joints carry glyphs only (star = Starboard,
    disc = Port); feet carry the word labels, because feet
    are far apart and hip labels would collide with each
    other (hips are 20 units apart in the source). The
    chain is still traceable: glyph + colour from hip
    through knee to the labeled foot."""
    OX, OY = 100, 110
    pts = {k: (v[0] * SCALE + OX, v[1] * SCALE + OY) for k, v in frame.items()
           if isinstance(v, list)}
    im = Image.new("RGB", (1000, 1020), (0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((30, 20), "RED STAR = STARBOARD = RIGHT leg",
           fill=RED, font=_font(28))
    d.text((30, 56), "BLUE DISC = PORT = LEFT leg",
           fill=BLUE, font=_font(28))
    for a, b in EDGES:
        if a in pts and b in pts:
            if a.startswith("Starboard") and b.startswith("Starboard"):
                col = RED
            elif a.startswith("Port") and b.startswith("Port"):
                col = BLUE
            else:
                col = GREY
            d.line([pts[a], pts[b]], fill=col, width=5)
    roles = {}
    for side in ("Starboard", "Port"):
        foot_y = frame[f"{side}Foot"][1]
        roles[side] = "KICK" if foot_y < ground_y - 10 else "PLANTED"
    for name, pt in pts.items():
        if name.startswith("Starboard"):
            _glyph(d, pt[0], pt[1], "Starboard")
        elif name.startswith("Port"):
            _glyph(d, pt[0], pt[1], "Port")
        else:
            d.ellipse([pt[0] - 10, pt[1] - 10, pt[0] + 10, pt[1] + 10],
                      fill=(128, 128, 128))
    for side, col in (("Starboard", RED), ("Port", BLUE)):
        foot = pts[f"{side}Foot"]
        fx, fy = foot
        if side == "Starboard":
            # Below the foot, right-aligned: empty space there
            # (the foot is the chain endpoint).
            _label(d, fx - 24, fy + 24, f"{side.upper()} FOOT", col,
                   anchor="right")
            _label(d, fx - 24, fy + 54, roles[side], YELLOW, anchor="right")
        else:
            # Right of the foot: empty space there.
            _label(d, fx + 28, fy - 14, f"{side.upper()} FOOT", col)
            _label(d, fx + 28, fy + 16, roles[side], YELLOW)
    kick_side = [s for s, r in roles.items() if r == "KICK"]
    support_side = [s for s, r in roles.items() if r == "PLANTED"]
    foot_txt = (f"FRAME: {frame['name']} | FACING: right | "
                f"KICK: {kick_side[0].upper() if kick_side else 'NONE'} | "
                f"SUPPORT: {' + '.join(s.upper() for s in support_side)}")
    d.text((30, 980), foot_txt, fill=WHITE, font=_font(20))
    return im, roles


if __name__ == "__main__":
    seq = json.load(open(sys.argv[1] if len(sys.argv) > 1
                          else "skeleton_kick_full.json"))
    for fr in seq["frames"]:
        im, roles = render_labeled(fr, seq.get("ground_y", 380))
        out = f"runs/current/skeleton-labeled-{fr['name']}-sidecar.png"
        im.save(out)
        print(f"{fr['name']}: {roles} -> {out}")

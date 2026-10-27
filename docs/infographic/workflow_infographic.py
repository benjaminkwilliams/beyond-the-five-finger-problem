#!/usr/bin/env python3
"""Workflow infographic, in the style of the user's gist template v1.1:
dark canvas, rounded tinted cards, gist palette, orthogonal
connectors, exact text, legend. Unity-canvas simulation: nodes
with ports, edges routed through gutters, not free-form art.
No image model is used; Pillow + DejaVu only."""
from PIL import Image, ImageDraw, ImageFont

W, H = 2400, 1500
BG = (0, 0, 0)
TXT = (255, 255, 255)
SUB = (185, 191, 189)
# gist dark palette: foreground, tinted fill
PAL = {
    "blue": ((92, 150, 234), (27, 34, 44)),
    "green": ((66, 199, 152), (16, 38, 31)),
    "amber": ((233, 180, 76), (41, 35, 19)),
    "purple": ((185, 135, 239), (33, 28, 41)),
    "teal": ((70, 204, 179), (14, 39, 36)),
    "red": ((242, 107, 107), (43, 29, 28)),
    "neutral": ((185, 191, 189), (23, 23, 21)),
}
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def font(sz, bold=False):
    return ImageFont.truetype(FB if bold else FR, sz)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

def border(fg, fill):
    return tuple((f + fl) // 2 for f, fl in zip(fg, fill))

def card(x, y, w, h, accent, title, lines):
    fg, fill = PAL[accent]
    d.rounded_rectangle([x, y, x + w, y + h], radius=28, fill=fill, outline=border(fg, fill), width=3)
    # port dots: left input, right output (Unity-canvas style)
    d.ellipse([x - 9, y + h // 2 - 9, x + 9, y + h // 2 + 9], fill=fg)
    d.ellipse([x + w - 9, y + h // 2 - 9, x + w + 9, y + h // 2 + 9], fill=fg)
    d.text((x + 28, y + 20), title, font=font(30, True), fill=TXT)
    yy = y + 66
    for ln in lines:
        d.text((x + 28, yy), ln, font=font(22), fill=SUB)
        yy += 32

def edge(points, color, dashed=False, arrow=True):
    if dashed:
        # draw dashed orthogonal segments
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            n = max(1, int(((abs(x2 - x1) + abs(y2 - y1)) // 18)))
            for i in range(n):
                if i % 2:
                    continue
                t1 = i / n; t2 = (i + 1) / n
                d.line([(x1 + (x2 - x1) * t1, y1 + (y2 - y1) * t1),
                        (x1 + (x2 - x1) * t2, y1 + (y2 - y1) * t2)], fill=color, width=4)
    else:
        d.line(points, fill=color, width=4, joint="curve")
    if arrow:
        (x1, y1), (x2, y2) = points[-2], points[-1]
        if x2 > x1:
            d.polygon([(x2, y2), (x2 - 18, y2 - 9), (x2 - 18, y2 + 9)], fill=color)
        elif x2 < x1:
            d.polygon([(x2, y2), (x2 + 18, y2 - 9), (x2 + 18, y2 + 9)], fill=color)
        elif y2 > y1:
            d.polygon([(x2, y2), (x2 - 9, y2 - 18), (x2 + 9, y2 - 18)], fill=color)
        else:
            d.polygon([(x2, y2), (x2 - 9, y2 + 18), (x2 + 9, y2 + 18)], fill=color)

def label(x, y, text, color):
    f = font(21)
    tw = d.textlength(text, font=f)
    d.rounded_rectangle([x - tw / 2 - 12, y - 16, x + tw / 2 + 12, y + 16], radius=14, fill=BG, outline=color, width=2)
    d.text((x - tw / 2, y - 11), text, font=f, fill=TXT)

# Title / subtitle
d.text((80, 50), "BEYOND THE FIVE FINGER PROBLEM", font=font(52, True), fill=TXT)
d.text((80, 120), "One harness engine: spec + tests first, checker per pair, repair in named-set language", font=font(26), fill=SUB)

# Shared state, top span
card(80, 190, 2240, 150, "neutral", "SPEC  —  shared state for every node",
     ["Glossary (glossary.json, M1 frozen)  •  Locked character sheets  •  Bench + holdout, never tuned to holdout  •  Feeds: Generator, Proposer, Checker"])
# Front bookend banner
card(80, 370, 2240, 90, "teal", "FRONT BOOKEND  —  tests written from the spec BEFORE frames are judged",
     ["A test is never rewritten to pass a bad frame. Spec changes go through the bench-regression rule."])

# Main row
y0 = 520
card(80, y0, 380, 260, "blue", "GENERATOR", ["Muse Image /", "any generator", "Draws frames", "from the spec"])
card(530, y0, 380, 260, "blue", "FRAMES  —  pair", ["Frame A, frame B", "Adjacent pair", "is the unit", "under test"])
card(980, y0, 380, 260, "purple", "PROPOSER", ["SAM 3.1 masks", "+ Spark labels", "Sidecar maps", "No hand coords"])
card(1430, y0, 380, 260, "green", "CHECKER", ["Gate 1: individual", "Gate 2: continuity", "Gate 3: visual DL", "Limb + arc limits"])
card(1880, y0, 380, 260, "amber", "AMENDER", ["Repair in", "named-set", "language", "e.g. port leg"])

# Main flow edges (orthogonal, through gutters)
mid = y0 + 130
edge([(460, mid), (530, mid)], PAL["neutral"][0])
edge([(910, mid), (980, mid)], PAL["neutral"][0])
edge([(1360, mid), (1430, mid)], PAL["neutral"][0])
edge([(1810, mid), (1880, mid)], PAL["neutral"][0])
label(495, mid - 34, "draw", PAL["blue"][0])
label(945, mid - 34, "pair", PAL["blue"][0])
label(1395, mid - 34, "assign", PAL["purple"][0])
label(1845, mid - 34, "FAIL", PAL["red"][0])

# Spec feeds are stated in the SPEC card text, not drawn as
# verticals: full-width verticals would cross the front-bookend
# banner and the proposer card. No crossing lines.

# Amender loop back to generator (bottom gutter)
edge([(2070, y0 + 260), (2070, 880), (270, 880), (270, y0)], PAL["amber"][0])
label(1170, 880, "repair instruction  →  regenerate only the failing named set", PAL["amber"][0])

# Back bookend + bench judge + report, bottom row
y1 = 980
card(80, y1, 700, 260, "teal", "BACK BOOKEND",
     ["Checker per pair, as frames return", "Cheapest failing representation first", "No late full re-roll, no frame-by-frame repair"])
card(850, y1, 700, 260, "red", "BENCH-JUDGE", ["Bench 7 pairs + holdout 3", "Passing a failing case is wrong", "Deleting a failing case = deleting a test"])
card(1620, y1, 700, 260, "green", "REPORT  +  DEMO", ["Readable report per pair", "Lead demo: leg swap", "mid-sequence, frames fine"])

edge([(780, y1 + 130), (850, y1 + 130)], PAL["neutral"][0])
edge([(1550, y1 + 130), (1620, y1 + 130)], PAL["neutral"][0])
# Checker down to back bookend
edge([(1620, y0 + 260), (1620, y1)], PAL["green"][0])
label(1620, y1 - 40, "PASS", PAL["green"][0])
# Bench-judge spec evolution (dashed, via left margin gutter, not through proposer)
edge([(1200, y1 + 260), (1200, 1280), (40, 1280), (40, 265), (80, 265)], PAL["red"][0], dashed=True)
label(640, 1260, "spec evolution, only under regression rule", PAL["red"][0])

# Legend + footer
d.line([(80, 1320), (2320, 1320)], fill=(53, 58, 55), width=2)
d.text((80, 1350), "Legend:  solid = data flow   •   dashed = spec evolution (regression rule only)   •   red = fail path   •   ports = Unity-canvas node I/O",
       font=font(22), fill=SUB)
d.text((80, 1400), "Beyond the Five Finger Problem  •  M1 frozen glossary, M3 five-node graph  •  Deterministic render, no image model",
       font=font(22), fill=SUB)

img.save("/home/hatch/workspace/hackathon-spike/docs/infographic/workflow-infographic.png")
print("saved 2400x1500")

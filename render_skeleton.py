#!/usr/bin/env python3
"""Render skeleton sidecars/filmstrip with side-coloured lines.

Same rule as extraction.render_sidecar: Starboard
edges red, Port edges blue, torso/head grey. A leg
crossing in front of the opposite hip must be
followable by colour, not by nearest hip.
"""
import json, sys
sys.path.insert(0, ".")
from skeleton import COLOURS, EDGES
from PIL import Image, ImageDraw

def render_frame(frame, size=(400, 400)):
    pts = {k: tuple(v) for k, v in frame.items() if isinstance(v, list)}
    im = Image.new("RGB", size, (0, 0, 0))
    d = ImageDraw.Draw(im)
    for a, b in EDGES:
        if a in pts and b in pts:
            if a.startswith("Starboard") and b.startswith("Starboard"):
                col = COLOURS["StarboardFoot"]
            elif a.startswith("Port") and b.startswith("Port"):
                col = COLOURS["PortFoot"]
            else:
                col = (80, 80, 80)
            d.line([pts[a], pts[b]], fill=col, width=2)
    for name, pt in pts.items():
        col = COLOURS.get(name, (128, 128, 128))
        d.ellipse([pt[0]-8, pt[1]-8, pt[0]+8, pt[1]+8], fill=col)
    return im

if __name__ == "__main__":
    seq = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "skeleton_test_sequence.json"))
    frames = seq["frames"]
    imgs = []
    for fr in frames:
        im = render_frame(fr)
        im.save(f"runs/current/skeleton-{fr['name']}-sidecar.png")
        imgs.append(im)
    w, h = imgs[0].size
    strip = Image.new("RGB", (w * len(imgs), h + 40), (255, 255, 255))
    d = ImageDraw.Draw(strip)
    for i, im in enumerate(imgs):
        strip.paste(im, (i * w, 0))
        d.text((i * w + 10, h + 10), frames[i]["name"], fill=(0, 0, 0))
    strip.save("runs/current/skeleton-filmstrip.png")
    print(f"rendered {len(imgs)} sidecars + filmstrip")

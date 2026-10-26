#!/usr/bin/env python3
"""SAM 3.1 pixel-mask client, closing M1.1e.

API form (from the cookbook basic recipe, 07_sam/01_api_basics):
  POST https://api.meta.ai/v1/responses, model sam-3.1,
  one short noun phrase + image data URL per request.

Response text contains, per match, a box token and a mask
token: <|mask;x=..;y=..;data=H,W,<payload>|>. The payload is
NOT COCO RLE. It is decoded with the official meta-sam parser
(pip install meta-sam-parser), which implements SAM 3's own
mask codec. The mask raster is box-sized (box width/height
+1) and is placed at the box top-left in full-image
coordinates; that placement was verified visually on bench
frames 2026-10-26 (mask overlays align with the legs).

Joint derivation from a mask (box-level is not enough):
  foot = centre x of the foreground pixels in the bottom
         5 rows of the mask, at the mask's maximum y.
         NOT the single lowest pixel, which is a corner
         (e.g. SadPocky B planted mask lowest pixel is
         x=125, the shoe's left edge, not its centre).
  hip  = centre x of the foreground pixels in the top
         5 rows of the mask, at the mask's minimum y.
  centroid = mean of all foreground pixels.

Auth: META_API_KEY from the environment (portable repo
form). The local test used the connector surrogate with
the same payloads; this file never contains a key.
"""
import base64
import json
import os
import re
import urllib.request

try:
    from meta_sam_parser import SegmentationMask, decode_mask_to_raster
except ImportError:  # pragma: no cover
    raise SystemExit("pip install meta-sam-parser (see 07_sam/01_api_basics)")

BASE = "https://api.meta.ai/v1"
BOX_RE = re.compile(r"<\|box;x1=(\d+);y1=(\d+);x2=(\d+);y2=(\d+);w=(\d+);h=(\d+)\|>")
MASK_RE = re.compile(r"<\|mask;x=(\d+);y=(\d+);data=([^|]+)\|>")


def _row_centre(fg, y_target, band=5, bottom=True):
    rows = [p for p in fg if (p[1] >= y_target - band if bottom else p[1] <= y_target + band)]
    if not rows:
        rows = fg
    return [sum(p[0] for p in rows) // len(rows), y_target]


def sam_masks(image_path, prompt, api_key=None):
    key = api_key or os.environ.get("META_API_KEY")
    if not key:
        raise SystemExit("META_API_KEY is not set in the environment")
    with open(image_path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode()
    payload = {"model": "sam-3.1", "input": [{"role": "user", "content": [
        {"type": "input_text", "text": prompt},
        {"type": "input_image", "image_url": f"data:image/png;base64,{b64}"},
    ]}]}
    req = urllib.request.Request(
        BASE + "/responses", method="POST",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)
    text = data["output"][0]["content"][0]["text"]
    boxes = [(int(a), int(b), int(c), int(d))
             for a, b, c, d, _, _ in BOX_RE.findall(text)]
    out = []
    for (x1, y1, x2, y2), mmatch in zip(boxes, MASK_RE.finditer(text)):
        h, w, payload_str = mmatch.group(3).split(",", 2)
        h, w = int(h), int(w)
        raster = decode_mask_to_raster(
            SegmentationMask(encoding="lossless", width=w, height=h, payload=payload_str))
        fg = [(x1 + (i % w), y1 + (i // w)) for i, v in enumerate(raster) if v]
        if not fg:
            continue
        max_y = max(p[1] for p in fg)
        min_y = min(p[1] for p in fg)
        out.append({
            "box": [x1, y1, x2, y2], "mask_size": [w, h],
            "fg_count": len(fg),
            "foot": _row_centre(fg, max_y, bottom=True),
            "hip": _row_centre(fg, min_y, bottom=False),
            "centroid": [sum(p[0] for p in fg) // len(fg),
                         sum(p[1] for p in fg) // len(fg)],
        })
    return out


if __name__ == "__main__":
    import sys
    print(json.dumps(sam_masks(sys.argv[1], sys.argv[2]), indent=2))

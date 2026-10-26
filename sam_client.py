#!/usr/bin/env python3
"""SAM 3.1 placement client, box level only.

API form found 2026-10-26 by probing Meta Model API:
  POST https://api.meta.ai/v1/responses
  {"model": "sam-3.1", "input": [{"role": "user", "content": [
      {"type": "input_text", "text": "<noun phrase>"},
      {"type": "input_image", "image_url": "data:image/png;base64,..."}]}]}

The /chat/completions endpoint rejects sam-3.1 with
"The model `sam-3.1` is not available on this endpoint. Use /v1/responses."

Response text contains one "<|box;x1=..;y1=..;x2=..;y2=..;w=..;h=..|>"
and one "<|mask;...|>" per match. Boxes are parsed here. Mask
decoding is OPEN: the mask data string (e.g. "46,50,~!!!...") is
not COCO RLE and was not decoded in the 2026-10-26 test, so this
client deliberately returns boxes only and never pretends to have
pixel masks.

Auth: META_API_KEY from the environment (portable repo form).
Locally, the connector surrogate path in the custom connector
helper does the same call with the vault key; this file never
contains a key.
"""
import base64
import json
import os
import re
import urllib.request

BASE = "https://api.meta.ai/v1"
BOX_RE = re.compile(r"<\|box;x1=(\d+);y1=(\d+);x2=(\d+);y2=(\d+);w=(\d+);h=(\d+)\|>")


def sam_boxes(image_path, prompt, api_key=None):
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
    boxes = []
    for m in BOX_RE.finditer(text):
        x1, y1, x2, y2, _w, _h = map(int, m.groups())
        boxes.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2,
                      "cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2,
                      "foot": [(x1 + x2) // 2, y2]})
    return boxes


if __name__ == "__main__":
    import sys
    print(json.dumps(sam_boxes(sys.argv[1], sys.argv[2]), indent=2))

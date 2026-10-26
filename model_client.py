#!/usr/bin/env python3
"""Transport for Meta Model API chat completions, with image input.

No credential lives in this file or in the repo. The key is read only
from META_API_KEY at run time. This is the portable submission path:
the same payload shape is used by the connector test transport in
run_m1.py, which swaps in the registered connector credential instead
of an environment key. Do not add a key, token or surrogate here.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request

BASE = "https://api.meta.ai/v1"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise RuntimeError("redirect refused, verify the endpoint")


def _image_url(path):
    with open(path, "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode("ascii")


def chat(model, prompt, image_paths=(), api_key=None, timeout=120):
    """Send one chat completion. Returns the reply text."""
    key = (api_key or os.environ.get("META_API_KEY", "")).strip()
    if not key:
        raise SystemExit("META_API_KEY is not set in the environment")
    content = [{"type": "text", "text": prompt}]
    for path in image_paths:
        content.append({"type": "image_url", "image_url": {"url": _image_url(path)}})
    payload = {"model": model, "messages": [{"role": "user", "content": content}]}
    request = urllib.request.Request(BASE + "/chat/completions", method="POST")
    request.add_header("Authorization", "Bearer " + key)
    request.add_header("Content-Type", "application/json")
    request.data = json.dumps(payload).encode("utf-8")
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code}: {body[:1000]}", file=sys.stderr)
        raise SystemExit(1)
    choices = data.get("choices", [])
    if not choices:
        raise SystemExit(f"no choices in Model API response: {json.dumps(data)[:500]}")
    return choices[0].get("message", {}).get("content", "")

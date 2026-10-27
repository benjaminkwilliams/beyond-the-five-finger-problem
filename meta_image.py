#!/usr/bin/env python3
"""Meta Image API as a harness GENERATOR node.

Model: muse-image-1.0, via the registered
custom.meta-model-api connection (same base URL
and auth as Spark/SAM, POST /v1/images/*).
Endpoints (from public Meta Model API docs,
verified live here, not from memory):
  POST /v1/images/generations — text prompt in,
    image out. Params: model, prompt, n=1,
    response_format=b64_json, output_format=webp.
  POST /v1/images/edits — prompt + input image(s),
    for image-to-image work (skeleton sidecar in,
    drawing out). Same JSON shape, plus "image"
    as a base64 data URL; if the live API rejects
    that shape, the error is printed and the call
    is reported, not retried with a guessed shape.
This module is the GENERATOR for graph.py: it
returns a local file path, and the rest of the
graph (proposer/checker/amender/bench-judge)
runs unchanged on whatever generator produced
the frame. That is the point — the verifier must
not care which generator drew the frame.
"""
import base64, importlib.util, json, os

spec = importlib.util.spec_from_file_location(
    "meta_model", "/home/hatch/workspace/custom-connectors/custom.meta-model-api/bin/meta_model.py")
mm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mm)

MODEL = "muse-image-1.0"


def _save(data, out_path):
    """data: /images response dict. Returns out_path."""
    item = data["data"][0]
    if "b64_json" in item:
        raw = base64.b64decode(item["b64_json"])
    elif "url" in item:
        raise RuntimeError("url response_format not handled; request b64_json")
    else:
        raise RuntimeError(f"unexpected image payload keys: {list(item.keys())}")
    with open(out_path, "wb") as fh:
        fh.write(raw)
    return out_path


def generate(prompt, out_path, n=1):
    data = mm.call("POST", "/images/generations", {
        "model": MODEL, "prompt": prompt, "n": n,
        "response_format": "b64_json", "output_format": "webp",
    })
    return _save(data, out_path)


def edit(prompt, image_path, out_path):
    """image_path: one path, or a list of paths in order.
    List order is the prompt_builder contract: labeled
    sidecar first, previous-frame drawing second. A single
    string still works (old callers)."""
    paths = [image_path] if isinstance(image_path, str) else image_path
    images = []
    for p in paths:
        with open(p, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode()
        ext = "png" if p.lower().endswith(".png") else "webp"
        images.append({"image_url": f"data:image/{ext};base64,{b64}"})
    data = mm.call("POST", "/images/edits", {
        "model": MODEL, "prompt": prompt,
        "images": images,
        "n": 1, "response_format": "b64_json", "output_format": "webp",
    })
    return _save(data, out_path)


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1]
    if cmd == "generate":
        print(generate(sys.argv[2], sys.argv[3]))
    elif cmd == "edit":
        print(edit(sys.argv[2], sys.argv[3], sys.argv[4]))

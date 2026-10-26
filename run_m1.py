#!/usr/bin/env python3
"""M1 runner: proposer v1 assignments -> checker -> bench/holdout verdicts.

Cases are file-backed pairs from the sprite-gif workflow output, using
388-400px frames (not 128px) so markers are readable. Frame numbers in
case names are 1-based, as in the QA records; file indices are 0-based,
so 1-based frame N is file frame_{N-1:02d}.png.

Scope honesty for M1: the spike bench has 8 assignment cases, but the
8th (Lila v5 mirrored guard, guard Facing[left] -> action Facing[right])
is NOT reproducible from the v5 files on disk, which are the fixed
facing-right set. It is therefore NOT counted in the file-backed
bench score here. It stays an assignment-level case until a
left-facing guard file is located. Counting it from these files
would be a false green.

Spec used: v2 (Trial A adopted). Declared transfer HipRight applies
at action-boundary pairs only. No bench case in this file-backed set
is a boundary pair, so declared transfers are empty here. That is
correct for these 10 pairs: none of them is the guard->action boundary.

Transports:
  connector (default, local test only): the registered connector
    credential, swapped in by authd for api.meta.ai. No key in this file.
  env: model_client.chat with META_API_KEY. This is the portable path.
"""
import argparse
import base64
import json
import sys
import urllib.error
import urllib.request

import numpy as np

sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import add_surrogate_to_request

from checker import FrameSets, Spec, Token, check_pair
from proposer import build_prompt, parse_proposal

BASE = "https://api.meta.ai/v1"
SP = "/home/hatch/workspace/sprite-gif-workflow/output"
DT = 0.1


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise RuntimeError("redirect refused, verify the endpoint")


def connector_chat(model, prompt, image_paths):
    content = [{"type": "text", "text": prompt}]
    for path in image_paths:
        with open(path, "rb") as fh:
            content.append({"type": "image_url", "image_url": {
                "url": "data:image/png;base64," + base64.b64encode(fh.read()).decode("ascii")}})
    payload = {"model": model, "messages": [{"role": "user", "content": content}]}
    request = urllib.request.Request(BASE + "/chat/completions", method="POST")
    request.add_header("Content-Type", "application/json")
    request.data = json.dumps(payload).encode("utf-8")
    add_surrogate_to_request(request, "custom.meta-model-api", allowed_hosts=["api.meta.ai"])
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')[:1000]}", file=sys.stderr)
        raise SystemExit(1)
    choices = data.get("choices", [])
    if not choices:
        raise SystemExit(f"no choices: {json.dumps(data)[:500]}")
    return choices[0].get("message", {}).get("content", "")


def placeholder_frame(assignments):
    entities, subsets = {}, {}
    x = 5
    for entity, markers, role, _ in sorted(assignments, key=lambda a: a[3]):
        m = np.zeros((32, 96), dtype=bool)
        m[8:28, x:x + 12] = True
        entities[entity] = m
        for mk in markers:
            s = np.zeros((32, 96), dtype=bool)
            s[10:13, x + 2:x + 10] = True
            subsets[f"{entity}.{mk}"] = s
        x += 16
    return FrameSets(entities, subsets)


def tokens(assignments):
    return tuple(Token(e, tuple(mk), r) for e, mk, r, _ in sorted(assignments, key=lambda a: a[3]))


def frame_path(folder, one_based):
    return f"{SP}/{folder}/frames/frame_{one_based - 1:02d}.png"


CASES = [
    # name, character, folder, frame_a, frame_b, expected_pass, split
    ("SadPocky v2 9->10", "SadPocky", "sadpocky-green-v2", 9, 10, True, "bench"),
    ("SadPocky v2 10->11 LEG SWAP", "SadPocky", "sadpocky-green-v2", 10, 11, False, "bench"),
    ("SadPocky v2 11->12", "SadPocky", "sadpocky-green-v2", 11, 12, True, "bench"),
    ("Lila v10 9->10", "Lila", "lila-v10", 9, 10, True, "bench"),
    ("Lila v10 10->11", "Lila", "lila-v10", 10, 11, True, "bench"),
    ("Lila v10 11->12", "Lila", "lila-v10", 11, 12, True, "bench"),
    ("Lila v10 12->13", "Lila", "lila-v10", 12, 13, True, "bench"),
    ("Raincoat v2 9->10 DEPTH SWAP", "Raincoat", "generated-v2", 9, 10, False, "holdout"),
    ("SadPocky v6 10->11", "SadPocky", "sadpocky-green-v6", 10, 11, True, "holdout"),
    ("SadPocky v6 11->12", "SadPocky", "sadpocky-green-v6", 11, 12, True, "holdout"),
]

SPEC = Spec(required_markers={}, reference_proportion={})
REF = placeholder_frame([("RightLeg", ("strap",), "kick", 0), ("LeftLeg", ("decal",), "support", 1)])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=["connector", "env"], default="connector")
    parser.add_argument("--model", default="muse-spark-1.3")
    parser.add_argument("--case", default=None, help="substring filter on case name")
    parser.add_argument("--out", default="results_m1.json")
    args = parser.parse_args()

    with open("glossary.json") as fh:
        glossary = json.load(fh)

    if args.transport == "env":
        from model_client import chat as env_chat

        def call(model, prompt, images):
            return env_chat(model, prompt, images)
    else:
        call = connector_chat

    results = []
    for name, character, folder, fa, fb, expected, split in CASES:
        if args.case and args.case not in name:
            continue
        pa = frame_path(folder, fa)
        pb = frame_path(folder, fb)
        prompt = build_prompt(character, glossary)
        print(f"\n=== {name} ({split}, expect {'PASS' if expected else 'FAIL'}) ===", flush=True)
        print(f"frames: {pa} -> {pb}", flush=True)
        reply = call(args.model, prompt, [pa, pb])
        print(f"proposer reply: {reply[:2000]}", flush=True)
        try:
            aa, ab, raw = parse_proposal(reply, character, glossary)
        except Exception as exc:  # noqa: BLE001 - record proposer failure, do not crash the run
            print(f"PROPOSER PARSE FAILURE: {exc}", flush=True)
            results.append({"case": name, "split": split, "expected_pass": expected,
                            "passed": None, "match": False, "error": str(exc), "reply": reply})
            continue
        v = check_pair(placeholder_frame(aa), placeholder_frame(ab),
                       tokens(aa), tokens(ab), SPEC, REF, dt_seconds=DT)
        match = v.passed == expected
        print(v.prose(f"{name} -> {'OK' if match else 'MISMATCH'}"), flush=True)
        results.append({"case": name, "split": split, "expected_pass": expected,
                        "passed": v.passed, "match": match,
                        "assignments_a": [list(a) for a in aa],
                        "assignments_b": [list(a) for a in ab],
                        "gate1": v.gate1, "gate2": v.gate2,
                        "dl_cost": v.dl_cost, "dl_budget": v.dl_budget, "dl_ops": v.dl_ops,
                        "reply": reply})

    with open(args.out, "w") as fh:
        json.dump(results, fh, indent=2)
    for split in ("bench", "holdout"):
        rows = [r for r in results if r["split"] == split]
        if rows:
            print(f"\n{split}: {sum(1 for r in rows if r['match'])}/{len(rows)} match")
    print(f"results written: {args.out}")


if __name__ == "__main__":
    main()

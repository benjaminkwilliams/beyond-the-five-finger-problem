#!/usr/bin/env python3
"""M2.2 first step: SAM masks on disk, end-to-end.

For each bench/holdout frame, run SAM (same
sam_fg as extraction) for leg, shoe, face, fist
prompts and save each mask as a PNG (white = fg)
plus a masks.json index. This is the checker's
real-pixel input: named sets as pixel sets, not
just sidecar dots. Uses Heartbeat (chat ping
every 90s) and RunTimer (telemetry to
runs/telemetry.jsonl).
"""
import json, os, sys
sys.path.insert(0, ".")
import importlib.util
spec = importlib.util.spec_from_file_location("run_extraction", "run_extraction.py")
re_ = importlib.util.module_from_spec(spec); spec.loader.exec_module(re_)
from PIL import Image
from heartbeat import Heartbeat
from telemetry import RunTimer

SP = re_.SP
CASES = [("SadPocky", "sadpocky-green-v2", 9), ("SadPocky", "sadpocky-green-v2", 10),
         ("SadPocky", "sadpocky-green-v2", 11), ("SadPocky", "sadpocky-green-v2", 12),
         ("Lila", "lila-v10", 9), ("Lila", "lila-v10", 10),
         ("Lila", "lila-v10", 11), ("Lila", "lila-v10", 12),
         ("Raincoat", "generated-v2", 9), ("Raincoat", "generated-v2", 10)]
PROMPTS = ["leg", "shoe", "face", "fist"]

def main():
    os.makedirs("runs/current/masks", exist_ok=True)
    hb = Heartbeat("masks-bench-holdout", total_steps=len(CASES))
    timer = RunTimer("masks-bench-holdout", notes="M2.2 SAM masks on disk")
    index = {}
    for character, folder, num in CASES:
        key = f"{character}-{num}"
        path = f"{SP}/{folder}/frames/frame_{num-1:02d}.png"
        hb.tick(f"{key} {path}")
        timer.step_start(key)
        orig = Image.open(path).convert("RGB")
        w, h = orig.size
        index[key] = {"size": [w, h], "masks": {}}
        for pr in PROMPTS:
            try:
                res = re_.sam_fg(path, pr)
            except Exception as e:
                print(f"{key} {pr} error: {e}", flush=True)
                res = []
            for i, m in enumerate(res):
                im = Image.new("L", (w, h), 0)
                px = im.load()
                for (x, y) in m["fg"]:
                    px[x, y] = 255
                out = f"runs/current/masks/{key}-{pr}-{i}.png"
                im.save(out)
                index[key]["masks"][f"{pr}-{i}"] = {"box": m["box"], "file": out}
            print(f"{key} {pr}: {len(res)} masks", flush=True)
        timer.step_end()
    hb.done()
    timer.finish()
    json.dump(index, open("runs/current/masks.json", "w"), indent=2)
    print("saved runs/current/masks.json")

if __name__ == "__main__":
    main()

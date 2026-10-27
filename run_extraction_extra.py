#!/usr/bin/env python3
"""Extra extraction for M1.2b pairs not in run7: Lila 13, SadPocky v6 10-12.
Same code/prompts as run_extraction.py (SadPocky marker prompt, Lila
anatomy prompt), no new tuning. Output: sidecar/annotated files in
runs/current/ with the usual names, joints in extra_joints.json
(bench joints.json untouched)."""
import json, re, sys
sys.path.insert(0, ".")
import importlib.util
spec = importlib.util.spec_from_file_location("run_extraction", "run_extraction.py")
re_ = importlib.util.module_from_spec(spec); spec.loader.exec_module(re_)
from PIL import Image, ImageDraw
from extraction import extract, COLOURS, render_sidecar
CHART = re_.CHART; SP = re_.SP
CASES = [("Lila", "lila-v10", 13), ("SadPocky", "sadpocky-green-v6", 10),
         ("SadPocky", "sadpocky-green-v6", 11), ("SadPocky", "sadpocky-green-v6", 12)]
def _prev_from_joints(joints):
    """Build prev_joints for the next frame from this frame's joints."""
    j = joints.get("joints", {})
    try:
        sf = j["StarboardFoot"]["point"]; sh = j["StarboardHip"]["point"]
        pf = j["PortFoot"]["point"]; ph = j["PortHip"]["point"]
        if sf and sh and pf and ph:
            return {"starboard": (tuple(sf), tuple(sh)), "port": (tuple(pf), tuple(ph))}
    except KeyError:
        pass
    return None

def main():
    out = {}
    prev_by_key = {}
    # Seed Lila tracking from the bench run in the same chain, if present:
    # Lila 13 continues Lila 12, it is not a fresh anchor.
    try:
        _bench = json.load(open("runs/current/joints.json"))
        if "Lila-12" in _bench:
            prev_by_key[("Lila", "lila-v10")] = _prev_from_joints(_bench["Lila-12"])
            print("seeded Lila prev from bench Lila-12", flush=True)
    except Exception as _e:
        print(f"no bench seed for Lila 13: {_e}", flush=True)
    for character, folder, num in CASES:
        path = f"{SP}/{folder}/frames/frame_{num-1:02d}.png"
        print(f"\n=== EXTRA {character} {num} ===", flush=True)
        legs = re_.sam_fg(path, "leg")
        if len(legs) < 2:
            for thigh in re_.sam_fg(path, "thigh"):
                if all(len(thigh["fg"] & leg["fg"]) < 0.1 * len(thigh["fg"]) for leg in legs):
                    legs.append(thigh)
        shoes = []
        for pr in ("shoe", "boot", "sock", "foot", "footwear", "pink shoe"):
            shoes.extend(re_.sam_fg(path, pr))
        faces = re_.sam_fg(path, "face")
        face_box = faces[0]["box"] if faces else None
        print(f"legs={len(legs)} shoes={len(shoes)} face={face_box}", flush=True)
        orient_text = re_.spark(
            "First image is a head-angle chart. Its 5 columns, left to right, are: "
            "profile facing image-left, 3/4 facing image-left, front (facing camera), "
            "3/4 facing image-right, profile facing image-right. Its 5 rows, top to "
            "bottom, are: looking up, slight up, level, slight down, looking down.\n"
            "Second image is a pixel-art character frame, coordinates origin top-left.\n"
            "Answer ONLY, one line per field:\nhead_centre: [x, y]\n"
            "yaw: <profile-left, 3/4-left, front, 3/4-right, profile-right>\n"
            "pitch: <up, slight-up, level, slight-down, down>\n"
            "bow: <where the nose/face points, in image terms>\n"
            "port_side_in_image: <image-left or image-right>", [CHART, path])
        orient = re_.parse_orientation(orient_text)
        print(orient_text, flush=True)
        orig = Image.open(path).convert("RGB"); w, h = orig.size
        overlay = Image.new("RGB", (w, h), (0, 0, 0)); od = ImageDraw.Draw(overlay)
        colours = [(255, 0, 0), (0, 0, 255), (0, 255, 0), (255, 255, 0)]
        for i, leg in enumerate(legs):
            for (x, y) in leg["fg"]:
                od.point((x, y), fill=colours[i % len(colours)])
        overlay_path = f"runs/current/{character}-{num}-leg-overlay.png"; overlay.save(overlay_path)
        roles = [None] * len(legs)
        if len(legs) == 2:
            if character == "SadPocky":
                rp = ("First image is the original character frame. Second image is a leg "
                      "overlay: leg0 in red, leg1 in blue, black elsewhere.\n"
                      "SadPocky: her starboard (right) thigh has a black thigh strap with "
                      "a heart ring; her port (left) thigh has a carrot + small bunny decal.\n"
                      "Answer ONLY:\nleg0: <starboard or port>\nleg1: <starboard or port>")
            else:
                rp = ("First image is the original character frame. Second image is a leg "
                      "overlay: leg0 in red, leg1 in blue, black elsewhere.\n"
                      "Lila is a girl with bare legs and bare feet, no leg markers. Her "
                      "starboard (right) leg connects to the hip on her right side, her "
                      "port (left) leg connects to the hip on her left side. In a "
                      "front-facing view, her right hip is on the image left and her "
                      "left hip is on the image right. Use hip position and body "
                      "anatomy, not markers, to decide.\n"
                      "Answer ONLY:\nleg0: <starboard or port>\nleg1: <starboard or port>")
            rt = re_.spark(rp, [path, overlay_path]); print(f"roles: {rt}", flush=True)
            for line in rt.splitlines():
                mm_ = re.match(r"leg(\d+):\s*(starboard|port)", line.strip())
                if mm_: roles[int(mm_.group(1))] = mm_.group(2)
        extra = {}
        fists = re_.sam_fg(path, "fist")
        if len(fists) == 2 and orient.get("yaw") == "front":
            centres = sorted([((b["box"][0] + b["box"][2]) // 2, (b["box"][1] + b["box"][3]) // 2) for b in fists], key=lambda p: p[0])
            extra = {"StarboardHand": centres[0], "PortHand": centres[1]}
        prev = prev_by_key.get((character, folder))
        joints, sidecar = extract((w, h), num, character, legs, shoes, face_box=face_box, orientation=orient, leg_roles=roles, extra_joints=extra, prev_joints=prev)
        out[f"{character}-{num}"] = joints
        prev_by_key[(character, folder)] = _prev_from_joints(joints)
        if joints.get("leg_track_conflict"): print("LEG TRACK CONFLICT: Spark roles overridden by continuity", flush=True)
        smap = Image.new("RGB", (w, h), (0, 0, 0)); sd = ImageDraw.Draw(smap)
        render_sidecar(sd, sidecar["dots"], sidecar["lines"], coincident=sidecar.get("coincident", ()))
        smap.save(f"runs/current/{folder}-{num}-sidecar.png")
        print(f"joints: {json.dumps(joints['joints'])}", flush=True)
    json.dump(out, open("runs/current/extra_joints.json", "w"), indent=2)
    print("\nsaved runs/current/extra_joints.json")
if __name__ == "__main__":
    main()

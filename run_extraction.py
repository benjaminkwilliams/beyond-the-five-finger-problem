#!/usr/bin/env python3
"""Local test driver for M1.1f extraction (not portable).

Calls SAM (leg, shoe, boot, sock, face) and Spark (orientation
with the angle chart, plus leg-role labelling on a numbered
leg overlay) via the connector surrogate, then runs
extraction.extract, writes sidecar maps + joint JSON, and
draws annotated originals. Output goes to
runs/current/ (local/untracked, like other test strips).

Bench only. Holdout is NOT run here (M1.1h).
"""
import base64
import json
import re
import sys
import urllib.request

sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import add_surrogate_to_request
import importlib.util
spec = importlib.util.spec_from_file_location(
    "meta_model", "/home/hatch/workspace/custom-connectors/custom.meta-model-api/bin/meta_model.py")
mm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mm)
import meta_sam_parser as m
from PIL import Image, ImageDraw, ImageFont
from extraction import extract, COLOURS, render_sidecar

BASE = "https://api.meta.ai/v1"
CHART = "/home/hatch/workspace/user/media_library/image/fe/fe2de5df81968ef0dd9d234fea1c9e1adddad52e750c2eb8035b4077ef035ccd.png"
SP = "/home/hatch/workspace/sprite-gif-workflow/output"


def sam_fg(path, prompt):
    with open(path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode()
    payload = {"model": "sam-3.1", "input": [{"role": "user", "content": [
        {"type": "input_text", "text": prompt},
        {"type": "input_image", "image_url": f"data:image/png;base64,{b64}"}
    ]}]}
    data = mm.call("POST", "/responses", payload)
    text = data["output"][0]["content"][0]["text"]
    boxes = [(int(a), int(b), int(c), int(d)) for a, b, c, d, _, _ in re.findall(
        r"<\|box;x1=(\d+);y1=(\d+);x2=(\d+);y2=(\d+);w=(\d+);h=(\d+)\|>", text)]
    out = []
    for (x1, y1, x2, y2), match in zip(boxes, re.finditer(
            r"<\|mask;x=(\d+);y=(\d+);data=([^|]+)\|>", text)):
        h, w, payload_str = match.group(3).split(",", 2)
        h, w = int(h), int(w)
        raster = m.decode_mask_to_raster(m.SegmentationMask(
            encoding="lossless", width=w, height=h, payload=payload_str))
        fg = {(x1 + (i % w), y1 + (i // w)) for i, v in enumerate(raster) if v}
        out.append({"fg": fg, "box": [x1, y1, x2, y2]})
    return out


def spark(prompt, images):
    content = [{"type": "text", "text": prompt}]
    for p in images:
        with open(p, "rb") as fh:
            content.append({"type": "image_url", "image_url": {
                "url": "data:image/png;base64," + base64.b64encode(fh.read()).decode()}})
    payload = {"model": "muse-spark-1.3", "messages": [{"role": "user", "content": content}]}
    req = urllib.request.Request(BASE + "/chat/completions", method="POST",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    add_surrogate_to_request(req, "custom.meta-model-api", allowed_hosts=["api.meta.ai"])
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.load(r)
    return data["choices"][0]["message"]["content"]


def parse_orientation(text):
    out = {}
    prev_by_key = {}
    for line in text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


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
    import os
    os.makedirs("extraction-test", exist_ok=True)
    cases = [
        ("SadPocky", "sadpocky-green-v2", 9), ("SadPocky", "sadpocky-green-v2", 10),
        ("SadPocky", "sadpocky-green-v2", 11), ("SadPocky", "sadpocky-green-v2", 12),
        ("Lila", "lila-v10", 9), ("Lila", "lila-v10", 10),
        ("Lila", "lila-v10", 11), ("Lila", "lila-v10", 12),
    ]
    all_results = {}
    prev_by_key = {}
    for character, folder, num in cases:
        path = f"{SP}/{folder}/frames/frame_{num-1:02d}.png"
        print(f"\n=== {character} {num} {path} ===", flush=True)
        legs = sam_fg(path, "leg")
        if len(legs) < 2:
            # SadPocky 9: "leg" returns only the planted leg;
            # the chambered leg comes back as "thigh" and is
            # disjoint (0px overlap) from the leg mask.
            for thigh in sam_fg(path, "thigh"):
                if all(len(thigh["fg"] & leg["fg"]) < 0.1 * len(thigh["fg"])
                       for leg in legs):
                    legs.append(thigh)
        shoes = []
        # Foot area = shoe/boot/sock/foot/footwear/pink
        # shoe. Lila is barefoot, so shoe prompts return 0
        # and "foot" is the only foot-area prompt that
        # works for her; SadPocky chambered feet (9/10)
        # are found by "pink shoe"/"footwear" when
        # shoe/foot/sock return 0. Merging in placement.py
        # deduplicates overlapping foot areas.
        for pr in ("shoe", "boot", "sock", "foot", "footwear", "pink shoe"):
            shoes.extend(sam_fg(path, pr))
        faces = sam_fg(path, "face")
        face_box = faces[0]["box"] if faces else None
        print(f"legs={len(legs)} shoes={len(shoes)} face_box={face_box}", flush=True)
        orient_text = spark(
            "First image is a head-angle chart. Its 5 columns, left to right, are: "
            "profile facing image-left, 3/4 facing image-left, front (facing camera), "
            "3/4 facing image-right, profile facing image-right. Its 5 rows, top to "
            "bottom, are: looking up, slight up, level, slight down, looking down.\n"
            "Second image is a pixel-art character frame, coordinates origin top-left.\n"
            "Answer ONLY, one line per field:\nhead_centre: [x, y]\n"
            "yaw: <profile-left, 3/4-left, front, 3/4-right, profile-right>\n"
            "pitch: <up, slight-up, level, slight-down, down>\n"
            "bow: <where the nose/face points, in image terms>\n"
            "port_side_in_image: <image-left or image-right>",
            [CHART, path])
        orient = parse_orientation(orient_text)
        print(orient_text, flush=True)
        # Role labelling: numbered leg overlay, proposer copy only.
        orig = Image.open(path).convert("RGB")
        w, h = orig.size
        overlay = Image.new("RGB", (w, h), (0, 0, 0))
        od = ImageDraw.Draw(overlay)
        colours = [(255, 0, 0), (0, 0, 255), (0, 255, 0), (255, 255, 0)]
        for i, leg in enumerate(legs):
            for (x, y) in leg["fg"]:
                od.point((x, y), fill=colours[i % len(colours)])
        overlay_path = f"runs/current/{character}-{num}-leg-overlay.png"
        overlay.save(overlay_path)
        roles = [None] * len(legs)
        if len(legs) == 2:
            if character == "SadPocky":
                role_prompt = (
                    "First image is the original character frame. Second image is a leg "
                    "overlay: leg0 in red, leg1 in blue, black elsewhere.\n"
                    "SadPocky: her starboard (right) thigh has a black thigh strap with "
                    "a heart ring; her port (left) thigh has a carrot + small bunny decal.\n"
                    "Answer ONLY:\nleg0: <starboard or port>\nleg1: <starboard or port>")
            else:
                role_prompt = (
                    "First image is the original character frame. Second image is a leg "
                    "overlay: leg0 in red, leg1 in blue, black elsewhere.\n"
                    "Lila is a girl with bare legs and bare feet, no leg markers. Her "
                    "starboard (right) leg connects to the hip on her right side, her "
                    "port (left) leg connects to the hip on her left side. In a "
                    "front-facing view, her right hip is on the image left and her "
                    "left hip is on the image right. Use hip position and body "
                    "anatomy, not markers, to decide.\n"
                    "Answer ONLY:\nleg0: <starboard or port>\nleg1: <starboard or port>")
            role_text = spark(role_prompt, [path, overlay_path])
            print(f"roles: {role_text}", flush=True)
            for line in role_text.splitlines():
                mm_ = re.match(r"leg(\d+):\s*(starboard|port)", line.strip())
                if mm_:
                    roles[int(mm_.group(1))] = mm_.group(2)
        # Hands via "fist" prompt: SadPocky hands are
        # fists and "fist" returns exactly 2 boxes on
        # bench frames; "shoulder" returns 0 everywhere,
        # so shoulders stay marker_seen=false (arm box
        # top is ~55px from the hand shoulder joint, not
        # a shoulder centre). Hand sidedness is assigned
        # by image x only when yaw is front: starboard
        # (her right) hand is image-left, port hand is
        # image-right. Otherwise hands stay unlabeled.
        extra = {}
        fists = sam_fg(path, "fist")
        if len(fists) == 2 and orient.get("yaw") == "front":
            centres = sorted(
                [((b["box"][0] + b["box"][2]) // 2, (b["box"][1] + b["box"][3]) // 2)
                 for b in fists], key=lambda p: p[0])
            extra = {"StarboardHand": centres[0], "PortHand": centres[1]}
        prev = prev_by_key.get((character, folder))
        joints, sidecar = extract((w, h), num, character, legs, shoes,
                                  face_box=face_box, orientation=orient, leg_roles=roles,
                                  extra_joints=extra, prev_joints=prev)
        all_results[f"{character}-{num}"] = joints
        prev_by_key[(character, folder)] = _prev_from_joints(joints)
        if joints.get("leg_track_conflict"): print("LEG TRACK CONFLICT: Spark roles overridden by continuity", flush=True)
        # Sidecar map
        smap = Image.new("RGB", (w, h), (0, 0, 0))
        sd = ImageDraw.Draw(smap)
        render_sidecar(sd, sidecar["dots"], sidecar["lines"], coincident=sidecar.get("coincident", ()), coincident_away=sidecar.get("coincident_away", False))
        smap.save(f"runs/current/{character}-{num}-sidecar.png")
        # Annotated original
        ann = orig.copy()
        ad = ImageDraw.Draw(ann)
        if face_box:
            ad.rectangle(face_box, outline=(0, 255, 255), width=3)
        for name, pt in sidecar["dots"].items():
            col = COLOURS.get(name, (128, 128, 128))
            ad.ellipse([pt[0]-6, pt[1]-6, pt[0]+6, pt[1]+6], fill=col, outline=(255, 255, 255), width=1)
            ad.text((pt[0]+8, pt[1]-6), name, fill=col)
        ann.save(f"runs/current/{character}-{num}-annotated.png")
        print(f"joints: {json.dumps(joints['joints'])}", flush=True)
    json.dump(all_results, open("runs/current/joints.json", "w"), indent=2)
    print("\nsaved runs/current/joints.json")


if __name__ == "__main__":
    main()

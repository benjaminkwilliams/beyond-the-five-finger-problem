#!/usr/bin/env python3
"""Generic starboard-kick workflow runner.

One workflow, any humanoid character. The code takes NO
character-specific branches: everything that differs
between characters lives in the profile JSON.

Profile schema (profiles/*.json):
  name: run label, used only for output naming
  spec: {kick_side, support_side, facing} — the shared
    spec the checker judges against
  character_desc: full character line for the prompt
    ("Character: ..."), supplied by the profile, never
    by this code or prompt_builder
  outfit_desc: single outfit noun for the previous-frame
    continuity line ("same {outfit_desc}"), e.g. "gi"
  style_desc: rendering style, e.g. "anime". Optional
    in code (None = no style line), required in
    practice for a cold start: with no previous frame
    and no style line, the first frame defaults to
    whatever the generator prefers (photorealistic in
    the generic v1 Sensei run), and the chain then
    carries that style forward. Style was never in
    prompt-v3; v11's anime look came only from
    previous-frame anime drawings.
  skeleton_file: skeleton JSON with frames in order,
    each frame a joint dict with a "name" (guard,
    chamber, snap, full, recoil, return for a kick).
    SIZING IS A PROFILE INPUT: a chibi/fumo/adult
    character supplies its own scaled skeleton file;
    this runner never scales joints itself, because
    the idle-measurement sizing layer is not built
    yet. Supplying the neutral adult skeleton for a
    non-adult character is a profile error, not a
    code branch.
  frames: frame names in sequence order

Modes:
  --dry-run (default): render labeled sidecars from
    the skeleton file, build all frame inputs with
    prompt_builder (prompt-v4), write inputs.json.
    No API calls. Previous-frame paths in inputs are
    the planned output paths, in sequence order.
  --generate: dry-run, then call meta_image.edit
    sequentially: guard from its sidecar alone, each
    later frame from [its sidecar, previous generated
    frame]. Times each call, writes manifest.json
    and a filmstrip (pair verdicts UNVERIFIED until
    a human eye ruling — this runner never assigns
    Starboard/Port from an unmarked drawing).

Sidecar roles are validated, not assumed: for each
frame, the sidecar's KICK side must equal spec
kick_side, or (guard/return) there must be no KICK
side. A mismatch fails loudly instead of generating
a frame the checker would FAIL.
"""
import argparse, json, os, sys, time

sys.path.insert(0, ".")
from prompt_builder import build_input, TEMPLATE_VERSION
from render_skeleton_labeled import render_labeled


def load_profile(path):
    with open(path) as fh:
        prof = json.load(fh)
    for key in ("name", "spec", "character_desc", "outfit_desc",
                "skeleton_file", "frames"):
        assert key in prof, f"profile missing {key}"
    return prof


def build_run(prof, out_dir):
    """Render sidecars, validate roles, build inputs. Returns (frames, inputs)."""
    os.makedirs(os.path.join(out_dir, "sidecars"), exist_ok=True)
    with open(prof["skeleton_file"]) as fh:
        seq = json.load(fh)
    skel_frames = {f["name"]: f for f in seq["frames"]}
    ground_y = seq.get("ground_y", 380)
    spec = prof["spec"]
    frames_out = []
    inputs = {}
    prev_out = None
    for name in prof["frames"]:
        assert name in skel_frames, f"skeleton missing frame {name}"
        fr = skel_frames[name]
        im, roles = render_labeled(fr, ground_y)
        sidecar = os.path.join(out_dir, "sidecars", f"{name}.png")
        im.save(sidecar)
        kick_sides = [s for s, r in roles.items() if r == "KICK"]
        if kick_sides:
            assert kick_sides == [spec["kick_side"]], (
                f"{name}: sidecar KICK {kick_sides} != spec kick "
                f"{spec['kick_side']} — refusing to generate a "
                "frame the checker would FAIL")
            kick, support = spec["kick_side"], spec["support_side"]
        else:
            kick, support = "NONE", "NONE"
        frame_spec = dict(spec, kick_side=kick, support_side=support)
        inp = build_input(frame_spec, name, sidecar, prev_out,
                          character_desc=prof["character_desc"],
                          outfit_desc=prof["outfit_desc"],
                          style_desc=prof.get("style_desc"))
        inputs[name] = inp
        frames_out.append({"name": name, "sidecar": sidecar,
                           "roles": roles, "output": os.path.join(out_dir, f"{name}.webp")})
        prev_out = frames_out[-1]["output"]
    with open(os.path.join(out_dir, "inputs.json"), "w") as fh:
        json.dump({"template_version": TEMPLATE_VERSION,
                   "profile": prof["name"], "inputs": inputs},
                  fh, indent=2)
    return frames_out, inputs


def filmstrip(frames_out, out_path, verdicts=None):
    """Generic filmstrip: drawing row, sidecar row, pair verdicts.
    Verdicts default to UNVERIFIED — never PASS a frame
    this runner has not had eye-ruled."""
    from PIL import Image, ImageDraw, ImageFont
    verdicts = verdicts or ["UNVERIFIED"] * (len(frames_out) - 1)
    COL, H = 400, 1180
    W = COL * len(frames_out)
    img = Image.new("RGB", (W, H), "black")
    d = ImageDraw.Draw(img)

    def font(size, bold=True):
        for path in (f"/usr/share/fonts/truetype/dejavu/DejaVuSans-{'Bold' if bold else ''}.ttf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
        return ImageFont.load_default()

    def centered(x0, y, text, f, color="white"):
        w = d.textlength(text, font=f)
        d.text((x0 + (COL - w) / 2, y), text, font=f, fill=color)

    def fit(path, box_w, box_h):
        im = Image.open(path).convert("RGB")
        im.thumbnail((box_w, box_h), Image.LANCZOS)
        return im

    for i, fr in enumerate(frames_out):
        x0 = i * COL
        centered(x0, 10, f"{i + 1} {fr['name']}", font(30))
        dr = fit(fr["output"], COL - 20, 400)
        img.paste(dr, (x0 + (COL - dr.width) // 2, 55))
        d.text((x0 + 8, 465), "RED STAR = STARBOARD = RIGHT leg", font=font(15, False), fill="red")
        d.text((x0 + 8, 485), "BLUE DISC = PORT = LEFT leg", font=font(15, False), fill="#3366FF")
        sc = fit(fr["sidecar"], COL - 60, 330)
        img.paste(sc, (x0 + (COL - sc.width) // 2, 515))
        centered(x0, 855, str(fr["roles"]), font(13, False), "#CCCCCC")
        centered(x0, 885, fr["name"].upper(), font(28), "#FFC107")
    for i, verdict in enumerate(verdicts):
        bx = (i + 1) * COL
        name = f"{frames_out[i]['name']}->{frames_out[i + 1]['name']}"
        color = "#FFC107" if verdict == "UNVERIFIED" else "white"
        w1 = d.textlength(name, font=font(20, False))
        w2 = d.textlength(verdict, font=font(24))
        d.text((bx - (w1 + w2 + 16) / 2, 950), name, font=font(20, False), fill="white")
        d.text((bx - (w1 + w2 + 16) / 2 + w1 + 16, 948), verdict, font=font(24), fill=color)
    img.save(out_path)
    print("saved", out_path, img.size)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("profile")
    ap.add_argument("--out", required=True)
    ap.add_argument("--generate", action="store_true")
    args = ap.parse_args()
    prof = load_profile(args.profile)
    frames_out, inputs = build_run(prof, args.out)
    for fr in frames_out:
        print(f"{fr['name']}: roles={fr['roles']} sidecar={fr['sidecar']}")
    if not args.generate:
        print(f"dry-run done: {args.out}/inputs.json (no API calls)")
        return
    from meta_image import edit
    manifest = []
    prev = None
    for fr in frames_out:
        images = [fr["sidecar"]] + ([prev] if prev else [])
        # build_input already listed these in order; reuse its prompt
        prompt = inputs[fr["name"]]["prompt"]
        t0 = time.time()
        edit(prompt, images, fr["output"])
        dt = time.time() - t0
        size = os.path.getsize(fr["output"])
        print(f"{fr['name']}: {dt:.1f}s -> {fr['output']} ({size} bytes)")
        manifest.append({"frame": fr["name"], "seconds": round(dt, 1),
                         "output": fr["output"], "bytes": size})
        prev = fr["output"]
    with open(os.path.join(args.out, "manifest.json"), "w") as fh:
        json.dump({"profile": prof["name"],
                   "template_version": TEMPLATE_VERSION,
                   "frames": manifest}, fh, indent=2)
    filmstrip(frames_out, os.path.join(args.out, "filmstrip.png"))


if __name__ == "__main__":
    main()

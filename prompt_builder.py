#!/usr/bin/env python3
"""Deterministic generation-input builder.

The retry-1 failure was a prompt-data failure, not a
model mystery: the sidecar carried no colour legend,
no previous frame, and no character continuity, and
the prompt was hand-written per call, so no two calls
were the same input. This module fixes that: given a
spec, a frame name, a labeled sidecar, and optionally
a previous-frame drawing, it builds the EXACT prompt
and image list, the same way, every time. Same inputs
-> same prompt string -> same image list order. No
timestamps, no randomness, no per-call wording drift.
Template version is stamped in the prompt so a future
change is visible in the record, not silent.
"""
import os

TEMPLATE_VERSION = "prompt-v4"  # v4: generic character (no Sensei default, outfit_desc drives the previous-frame line); v3: NONE-kick handling for guard/return (both feet planted); v2: full torso BACKWARDS

# Fixed phase wording per frame name. Written once, reused
# verbatim; never reworded per call.
PHASE_TEXT = {
    "guard": ("standing guard stance, both feet planted, "
              "fists up in guard"),
    "chamber": ("one leg planted on the ground, the other knee "
                "raised high in a chambered kick position with "
                "the foot tucked under, fists up in guard"),
    "snap": ("one leg planted on the ground with the knee "
             "slightly bent, the other leg snapping forward "
             "in a front kick, hips pushed forward, fists up "
             "in guard"),
    "full": ("one leg planted on the ground, the other leg "
             "extended straight forward in a full front kick, "
             "torso moving backwards for balance, "
             "fists up in guard"),
    "recoil": ("one leg planted on the ground, the other leg "
               "folding back to a chambered position after a "
               "kick, fists up in guard"),
    "return": ("returning to a standing guard stance after a "
               "kick, the kicking foot coming down behind to "
               "the ground, both feet planted, fists up in guard"),
}


def build_input(spec, frame_name, sidecar_path, previous_frame_path=None,
                character_desc=None, outfit_desc="outfit", style_desc=None):
    """spec: {kick_side, support_side, facing}.
    Returns {"prompt": str, "images": [sidecar, previous?]}.
    Image order is fixed: sidecar first (pose + labels),
    previous frame second (identity continuity). The prompt
    says so explicitly, in the same words, every time.

    Generic-character rule (prompt-v4): NOTHING in this
    module names a character, an outfit, or a hairstyle.
    character_desc and outfit_desc come from the caller's
    character profile (see profiles/*.json, run by
    run_kick.py). The old v3 default ("black gi, black
    hair") and the hard-coded "same gi" previous-frame
    line were Sensei leaking into the builder: a non-gi
    character would have been told to keep a gi it does
    not wear. With character_desc=None the default is
    deliberately bare ("single character, flat black
    background") — a profile must supply the rest.
    Regression: build_input with character_desc set to
    the old v3 default and outfit_desc="gi" reproduces
    the v3 prompt exactly, except the version stamp.
    Style is also a profile input, not a builder
    default: style_desc=None adds no style line (the
    v3 behaviour). A profile that needs a style must
    name it — v11's anime look was never in the prompt
    at all, it was carried implicitly by previous-frame
    anime drawings, which is why a fresh guard with no
    previous frame defaulted to photorealistic in the
    generic v1 run. Sensei's profile therefore sets
    style_desc="anime"; without it, "same output" is
    unachievable from a cold start."""
    kick = spec["kick_side"]
    support = spec["support_side"]
    phase = PHASE_TEXT[frame_name]
    lines = [
        f"[{TEMPLATE_VERSION}] REFERENCE IMAGES, IN ORDER:",
        ("1. Labeled skeleton sidecar (black background). "
         "Read its labels. Do NOT copy labels, text, or "
         "symbols into the drawing."),
        ("   - RED STAR glyph = STARBOARD = the character's "
         "RIGHT leg."),
        ("   - BLUE DISC glyph = PORT = the character's "
         "LEFT leg."),
        (f"   - The leg marked KICK in the sidecar is the "
         f"kicking leg: {kick.upper()}. The leg marked "
         f"PLANTED stays on the ground: {support.upper()}.")
        if kick.upper() != "NONE" else
        ("   - No kicking leg in this frame: both feet "
         "stay planted on the ground."),
        ("   - Follow the leg from its HIP glyph, through "
         "its KNEE glyph, to its FOOT glyph. A leg is the "
         "hip it hangs from, not where its foot lands on "
         "screen."),
    ]
    if character_desc is None:
        character_desc = "single character, flat black background"
    images = [sidecar_path]
    if previous_frame_path:
        lines.append(
            "2. Previous frame drawing: the SAME character, "
            f"same face, same hair, same {outfit_desc}, same "
            "background. Keep this character exactly; do not "
            f"change face, hair, {outfit_desc} colour, or "
            "background.")
        images.append(previous_frame_path)
    lines += [
        f"DRAW THIS FRAME: {phase}.",
        (f"Kicking leg: {kick} (red star). Support leg: "
         f"{support} (blue disc), planted on the ground.")
        if kick.upper() != "NONE" else
        "Kicking leg: none. Both feet planted on the ground.",
        f"Facing: {spec.get('facing', 'image-right')}.",
        f"Character: {character_desc}.",
    ] + ([f"Style: {style_desc}."] if style_desc else []) + [
        "Drawing itself: no text, no labels, no symbols, "
        "no background other than flat black.",
    ]
    return {"prompt": "\n".join(lines), "images": images}


if __name__ == "__main__":
    import json, sys
    # Usage: prompt_builder.py [profile.json]
    # A profile supplies spec/character_desc/outfit_desc;
    # with no profile, prints a generic snap input (no
    # character named, no previous frame). Sensei runs
    # go through run_kick.py + profiles/sensei.json.
    if len(sys.argv) > 1:
        prof = json.load(open(sys.argv[1]))
        spec = prof["spec"]
        out = build_input(spec, "snap", "skeleton-labeled-snap-sidecar.png",
                          character_desc=prof["character_desc"],
                          outfit_desc=prof["outfit_desc"],
                          style_desc=prof.get("style_desc"))
    else:
        out = build_input({"kick_side": "Starboard", "support_side": "Port",
                           "facing": "image-right"}, "snap",
                          "skeleton-labeled-snap-sidecar.png")
    print(out["prompt"])
    print("IMAGES:", out["images"])

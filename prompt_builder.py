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

TEMPLATE_VERSION = "prompt-v1"

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
             "fists up in guard, slight forward lean"),
    "recoil": ("one leg planted on the ground, the other leg "
               "folding back to a chambered position after a "
               "kick, fists up in guard"),
    "return": ("returning to a standing guard stance after a "
               "kick, the kicking foot coming down behind to "
               "the ground, both feet planted, fists up in guard"),
}


def build_input(spec, frame_name, sidecar_path, previous_frame_path=None,
                character_desc=("black gi, black hair, flat black "
                                "background, single character")):
    """spec: {kick_side, support_side, facing}.
    Returns {"prompt": str, "images": [sidecar, previous?]}.
    Image order is fixed: sidecar first (pose + labels),
    previous frame second (identity continuity). The prompt
    says so explicitly, in the same words, every time."""
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
         f"PLANTED stays on the ground: {support.upper()}."),
        ("   - Follow the leg from its HIP glyph, through "
         "its KNEE glyph, to its FOOT glyph. A leg is the "
         "hip it hangs from, not where its foot lands on "
         "screen."),
    ]
    images = [sidecar_path]
    if previous_frame_path:
        lines.append(
            "2. Previous frame drawing: the SAME character, "
            "same face, same hair, same gi, same background. "
            "Keep this character exactly; do not change face, "
            "hair, gi colour, or background.")
        images.append(previous_frame_path)
    lines += [
        f"DRAW THIS FRAME: {phase}.",
        (f"Kicking leg: {kick} (red star). Support leg: "
         f"{support} (blue disc), planted on the ground."),
        f"Facing: {spec.get('facing', 'image-right')}.",
        f"Character: {character_desc}.",
        "Drawing itself: no text, no labels, no symbols, "
        "no background other than flat black.",
    ]
    return {"prompt": "\n".join(lines), "images": images}


if __name__ == "__main__":
    import json, sys
    spec = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else {
        "kick_side": "Starboard", "support_side": "Port",
        "facing": "image-right"}
    out = build_input(spec, "snap",
                      "runs/current/skeleton-labeled-snap-sidecar.png",
                      "runs/current/media-generation-m2-7-sensei-chamber-drawing-0-59ee03eb-5082-4937-aeb9-f902d48c6d67.webp")
    print(out["prompt"])
    print("IMAGES:", out["images"])

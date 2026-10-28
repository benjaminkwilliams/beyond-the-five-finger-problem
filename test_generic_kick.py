#!/usr/bin/env python3
"""Unit tests for the generic kick workflow. No API calls.

Checks the generality contract, not one character:
- prompt_builder with no profile names no outfit: the
  generic default contains no "gi", and the previous-
  frame line uses whatever outfit_desc the caller
  passes (gi for Sensei, kimono for a test character,
  etc.), with no per-character branches.
- Repeat build is byte-identical (determinism).
- run_kick.build_run on profiles/sensei.json renders
  sidecars, validates sidecar KICK == spec kick_side
  for the four moving frames, NONE for guard/return,
  and builds inputs in sequence order with the
  previous-frame path chaining correctly.
Run: python3 test_generic_kick.py
"""
import json, os, sys, tempfile

sys.path.insert(0, ".")
from prompt_builder import build_input
from run_kick import load_profile, build_run

SPEC = {"kick_side": "Starboard", "support_side": "Port", "facing": "image-right"}


def test_no_default_outfit():
    out = build_input(SPEC, "snap", "sidecar.png")
    assert "gi" not in out["prompt"], out["prompt"]
    assert "Character: single character, flat black background." in out["prompt"]


def test_outfit_substitution():
    for outfit in ("gi", "kimono", "uniform"):
        out = build_input(SPEC, "snap", "sidecar.png", "prev.webp",
                          character_desc="test character", outfit_desc=outfit)
        assert f"same {outfit}" in out["prompt"]
        assert f"{outfit} colour" in out["prompt"]
        assert "same gi" not in out["prompt"] or outfit == "gi"


def test_style_line():
    # No style = no style line (v3 behaviour, regression-safe).
    out = build_input(SPEC, "snap", "sidecar.png")
    assert "Style:" not in out["prompt"]
    # A profile style adds exactly one line, nothing else named.
    out = build_input(SPEC, "snap", "sidecar.png",
                      character_desc="x", outfit_desc="gi", style_desc="anime")
    assert "Style: anime." in out["prompt"]


def test_determinism():
    a = build_input(SPEC, "snap", "sidecar.png", "prev.webp",
                    character_desc="x", outfit_desc="gi")
    b = build_input(SPEC, "snap", "sidecar.png", "prev.webp",
                    character_desc="x", outfit_desc="gi")
    assert a == b


def test_sensei_profile_dry_run():
    prof = load_profile("profiles/sensei.json")
    assert prof["spec"]["kick_side"] == "Starboard"
    with tempfile.TemporaryDirectory() as td:
        frames, inputs = build_run(prof, td)
        assert [f["name"] for f in frames] == prof["frames"]
        # Roles: moving frames kick Starboard, anchors none.
        for f in frames:
            if f["name"] in ("guard", "return"):
                assert not any(r == "KICK" for r in f["roles"].values()), f
            else:
                assert f["roles"]["Starboard"] == "KICK", f
                assert f["roles"]["Port"] == "PLANTED", f
        # Previous-frame chaining: guard has 1 image, others 2,
        # and each previous path is the prior frame's output.
        assert inputs["guard"]["images"] == [frames[0]["sidecar"]]
        for i in range(1, len(frames)):
            assert inputs[frames[i]["name"]]["images"][1] == frames[i - 1]["output"]
        # Prompt carries the profile, not a builder default.
        assert prof["character_desc"] in inputs["snap"]["prompt"]
        assert "same gi" in inputs["snap"]["prompt"]


if __name__ == "__main__":
    test_no_default_outfit()
    test_outfit_substitution()
    test_style_line()
    test_determinism()
    test_sensei_profile_dry_run()
    print("test_generic_kick: all PASS (no API calls)")

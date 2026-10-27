#!/usr/bin/env python3
"""M1.2b / M1.5b driver: proposer v1.2 sidecar re-run, twice (variance).

For each pair, sends 4 images (A orig, A sidecar, B orig, B sidecar)
to Spark with proposer.build_sidecar_prompt, parses with
parse_proposal, and audits assignments against expected roles:
- Lila v10 pairs: port = kick, starboard = support.
- SadPocky v2 9->10: starboard chambers in both frames (kick=starboard
  in chamber sense), port = support; 11->12: port = kick (extended),
  starboard = support.
- SadPocky v6 10->11, 11->12: port = kick, starboard = support.
- SadPocky v2 10->11: EXPECTED FAIL (leg swap): port extends in B
  after starboard chambered in A — audit records whether proposer
  catches the role change, checker DL/depth are reported, not hidden.
- Raincoat 9->10 (holdout, already run in M1.1h for extraction):
  port chambers then extends, starboard planted; depth gate is
  reported separately (depth_rank from proposer).

Sidecar maps and originals come from runs/current/ (copied from the
v2 archive; extraction is not re-run for a prompt-only re-run),
holdout for Raincoat, and new extraction for Lila 13 / SadPocky v6
frames, run by run_extraction_v11_extra.py if needed — this driver
does NOT extract, it only proposes from existing maps).

Runs each pair TWICE for M1.5b variance (2x, user-approved).
Output: runs/current/proposer_v11_results.json + log.
"""
import json, sys
sys.path.insert(0, ".")
import importlib.util
spec = importlib.util.spec_from_file_location("run_extraction", "run_extraction.py")
re_ = importlib.util.module_from_spec(spec); spec.loader.exec_module(re_)
from proposer import build_sidecar_prompt, parse_proposal
from checker import visual_dl, Token
# NOTE 2026-10-26: checker.py is used for DL (gate 3) only.
# check_depth_gate is NOT imported: it is superseded by the
# user correction (depth flip = mislabeling, not a defect).
# numpy 2.5.4 is installed in .venv-sam (see
# requirements-venv.txt) so checker imports cleanly.

SP = re_.SP
GLOSS = json.load(open("glossary.json"))

PAIRS = [
    # (character, folder, num_a, num_b, expected_kick_leg)
    ("Lila", "lila-v10", 9, 10, "StarboardHip"),
    ("Lila", "lila-v10", 10, 11, "StarboardHip"),
    ("Lila", "lila-v10", 11, 12, "StarboardHip"),
    ("Lila", "lila-v10", 12, 13, "StarboardHip"),
    ("SadPocky", "sadpocky-green-v2", 9, 10, "StarboardLeg"),
    ("SadPocky", "sadpocky-green-v2", 10, 11, "SWAP"),
    ("SadPocky", "sadpocky-green-v2", 11, 12, "PortLeg"),
    ("SadPocky", "sadpocky-green-v6", 10, 11, "PortLeg"),
    ("SadPocky", "sadpocky-green-v6", 11, 12, "PortLeg"),
    ("Raincoat", "generated-v2", 9, 10, "PortLeg"),
]

def main():
    results = {}
    for character, folder, na, nb, exp in PAIRS:
        for run in (1, 2):
            key = f"{folder}-{na}->{nb}-run{run}"
            print(f"\n=== {key} expected kick={exp} ===", flush=True)
            try:
                prompt, order = build_sidecar_prompt(character, GLOSS)
                images = []
                for num in (na, nb):
                    images.append(f"{SP}/{folder}/frames/frame_{num-1:02d}.png")
                    images.append(f"runs/current/{folder}-{num}-sidecar.png")
                # order is A orig, A sidecar, B orig, B sidecar — images built in that order
                text = re_.spark(prompt, images)
                print(text[:1000], flush=True)
                a, b, raw = parse_proposal(text, character, GLOSS)
                print(f"parsed A={a} B={b}", flush=True)
                # audit: kick leg per frame
                def kick_leg(frame):
                    for ent, markers, role, depth in frame:
                        if role == "kick":
                            return ent
                    return None
                ka, kb = kick_leg(a), kick_leg(b)
                tokens_a = tuple(Token(ent, markers, role) for ent, markers, role, _ in a)
                tokens_b = tuple(Token(ent, markers, role) for ent, markers, role, _ in b)
                dl_cost, dl_ops = visual_dl(tokens_a, tokens_b)
                results[key] = {"kick_a": ka, "kick_b": kb, "expected": exp,
                                "depth_findings": "ignored-superseded",
                                "dl_cost": dl_cost, "dl_ops": dl_ops,
                                "assignments_a": [list(x) for x in a],
                                "assignments_b": [list(x) for x in b]}
            except Exception as e:
                print(f"ERROR {key}: {e}", flush=True)
                results[key] = {"error": str(e)}
    json.dump(results, open("runs/current/proposer_v11_results.json", "w"), indent=2)
    print("\nsaved runs/current/proposer_v11_results.json")

if __name__ == "__main__":
    main()

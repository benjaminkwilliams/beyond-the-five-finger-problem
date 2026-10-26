"""Spec-evolution spike: bench-parameterised spec versions, a
structured ledger, amendment trials, and an adoption rule.

Bench (candidate-generating) cases are the 8 real-assignment pairs
from run_real.py. Holdout cases NEVER generate candidates; they are
reported against every spec version to catch ruler-loosening:
  - Raincoat recreate generated-v2, pair 9->10: depth-plane swap
    (frame 9 chambers the near leg, frames 10-11 extend the far leg;
    pelvis-zoom proven, memory 2026-10-10). Expected FAIL.
  - SadPocky green-v6 pairs 10->11 and 11->12: the DECAL leg does
    the whole kick, strapped leg planted throughout. Expected PASS.

A SpecVersion carries: role transfers declared at action-boundary
pairs, role transfers declared anywhere, and the DL edit rate.
Amendment kinds must be declared (fix-the-ruler vs fix-the-world).
Adoption rule (bench only): adopt iff verdict matches do not drop,
catches do not drop, false positives do not rise, AND spurious
findings (gate-2 flags on a change the record says is legitimate)
strictly decrease. Holdout is reported, never optimised.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np
from checker import FrameSets, Spec, Token, check_pair

DT = 0.1
BASE_SPEC = Spec(required_markers={}, reference_proportion={})


def placeholder_frame(tokens):
    entities, subsets = {}, {}
    x = 5
    for t in tokens:
        m = np.zeros((32, 96), dtype=bool)
        m[8:28, x:x + 12] = True
        entities[t.entity] = m
        for mk in t.markers:
            s = np.zeros((32, 96), dtype=bool)
            s[10:13, x + 2:x + 10] = True
            subsets[f"{t.entity}.{mk}"] = s
        x += 16
    return FrameSets(entities, subsets)


REF = placeholder_frame((Token("StarboardLeg", ("strap",), "kick"), Token("PortLeg", ("decal",), "support")))


@dataclass
class Case:
    name: str
    tokens_a: tuple
    tokens_b: tuple
    expected_pass: bool
    boundary: bool = False
    legit_entities: frozenset = frozenset()  # gate-2 flags on these = spurious
    split: str = "bench"


def T(entity, markers=(), role=""):
    return Token(entity, tuple(markers), role)


# ---------------- bench cases ----------------
sp9 = (T("StarboardLeg", ("strap",), "kick"), T("PortLeg", ("decal",), "support"), T("Facing", ("right",)))
sp11 = (T("PortLeg", ("decal",), "kick"), T("StarboardLeg", ("strap",), "support"), T("Facing", ("right",)))
lila = (T("StarboardHip", (), "kick"), T("PortHip", (), "support"), T("Facing", ("right",)))
guard_l = (T("StarboardHip", (), "support"), T("PortHip", (), "support"), T("Facing", ("left",)))
kick_r = (T("StarboardHip", (), "kick"), T("PortHip", (), "support"), T("Facing", ("right",)))

BENCH = [
    Case("SadPocky v2 9->10", sp9, sp9, True),
    Case("SadPocky v2 10->11 LEG SWAP", sp9, sp11, False),
    Case("SadPocky v2 11->12", sp11, sp11, True),
    Case("Lila v10 9->10", lila, lila, True),
    Case("Lila v10 10->11", lila, lila, True),
    Case("Lila v10 11->12", lila, lila, True),
    Case("Lila v10 12->13", lila, lila, True),
    Case("Lila v5 guard->action MIRRORED GUARD", guard_l, kick_r, False,
         boundary=True, legit_entities=frozenset({"StarboardHip"})),
]

# ---------------- holdout cases ----------------
rc9 = (T("StarboardLeg", (), "kick"), T("PortLeg", (), "support"), T("Facing", ("right",)))
rc10 = (T("PortLeg", (), "kick"), T("StarboardLeg", (), "support"), T("Facing", ("right",)))
sp6 = (T("PortLeg", ("decal",), "kick"), T("StarboardLeg", ("strap",), "support"), T("Facing", ("right",)))
HOLDOUT = [
    Case("Raincoat v2 9->10 DEPTH SWAP (holdout)", rc9, rc10, False, split="holdout"),
    Case("SadPocky v6 10->11 (holdout)", sp6, sp6, True, split="holdout"),
    Case("SadPocky v6 11->12 (holdout)", sp6, sp6, True, split="holdout"),
]


@dataclass
class SpecVersion:
    name: str
    transfers_boundary: frozenset = frozenset()
    transfers_anywhere: frozenset = frozenset()
    edit_rate_per_s: float = 20.0


def evaluate(version: SpecVersion, cases, ledger):
    rows = []
    for c in cases:
        declared = set(version.transfers_anywhere)
        if c.boundary:
            declared |= set(version.transfers_boundary)
        v = check_pair(
            placeholder_frame(c.tokens_a), placeholder_frame(c.tokens_b),
            c.tokens_a, c.tokens_b, BASE_SPEC, REF, dt_seconds=DT,
            edit_rate_per_s=version.edit_rate_per_s,
            declared_transfers=frozenset(declared),
        )
        spurious = sum(1 for f in v.gate2 if any(f.startswith(e + ":") for e in c.legit_entities))
        rows.append((c, v, spurious))
        ledger.append({
            "spec": version.name, "case": c.name, "split": c.split,
            "expected_pass": c.expected_pass, "passed": v.passed,
            "dl_cost": v.dl_cost, "dl_budget": v.dl_budget,
            "gate1": v.gate1, "gate2": v.gate2, "ops": v.dl_ops,
            "spurious": spurious,
        })
    return rows


def metrics(rows):
    return {
        "matches": sum(1 for c, v, _ in rows if v.passed == c.expected_pass),
        "catches": sum(1 for c, v, _ in rows if not c.expected_pass and not v.passed),
        "false_pos": sum(1 for c, v, _ in rows if c.expected_pass and not v.passed),
        "spurious": sum(s for _, _, s in rows),
        "n": len(rows),
    }


def main():
    ledger: list[dict] = []
    v1 = SpecVersion("v1")
    v2 = SpecVersion("v2", transfers_boundary=frozenset({"StarboardHip"}))
    v3 = SpecVersion("v3-candidate",
                     transfers_boundary=frozenset({"StarboardHip"}),
                     transfers_anywhere=frozenset({"StarboardLeg", "PortLeg"}),
                     edit_rate_per_s=80.0)

    print("=== Baseline v1 ===")
    b1 = metrics(evaluate(v1, BENCH, ledger))
    h1 = metrics(evaluate(v1, HOLDOUT, ledger))
    print(f"bench:   {b1}")
    print(f"holdout: {h1}")

    print("\n=== Trial A (fix-the-ruler): v1 -> v2, declare StarboardHip role")
    print("    transfer at action-boundary pairs only ===")
    b2 = metrics(evaluate(v2, BENCH, ledger))
    h2 = metrics(evaluate(v2, HOLDOUT, ledger))
    print(f"bench:   {b2}")
    print(f"holdout: {h2}")
    adopt_a = (b2["matches"] >= b1["matches"] and b2["catches"] >= b1["catches"]
               and b2["false_pos"] <= b1["false_pos"] and b2["spurious"] < b1["spurious"])
    print(f"ADOPTION RULE: {'ADOPT v2' if adopt_a else 'REJECT v2'} "
          f"(spurious findings {b1['spurious']} -> {b2['spurious']}, catches held at {b2['catches']})")

    print("\n=== Trial B (fix-the-ruler, overreach): v2 -> v3-candidate,")
    print("    declare leg role transfers ANYWHERE + raise edit rate 20 -> 80/s ===")
    b3 = metrics(evaluate(v3, BENCH, ledger))
    h3 = metrics(evaluate(v3, HOLDOUT, ledger))
    print(f"bench:   {b3}")
    print(f"holdout: {h3}")
    adopt_b = (b3["matches"] >= b2["matches"] and b3["catches"] >= b2["catches"]
               and b3["false_pos"] <= b2["false_pos"] and b3["spurious"] < b2["spurious"])
    print(f"ADOPTION RULE: {'ADOPT v3' if adopt_b else 'REJECT v3'} "
          f"(bench catches {b2['catches']} -> {b3['catches']}, "
          f"holdout catches {h2['catches']} -> {h3['catches']})")

    with open("ledger.jsonl", "w") as fh:
        for rec in ledger:
            fh.write(json.dumps(rec) + "\n")
    print(f"\nLedger written: ledger.jsonl ({len(ledger)} structured records, no prose)")


if __name__ == "__main__":
    main()

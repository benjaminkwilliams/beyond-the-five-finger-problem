"""Synthetic tests: rendered pixel-set frames with known verdicts."""
import numpy as np
from checker import FrameSets, Spec, Token, check_pair

H = W = 96


def box(x0, y0, x1, y1):
    m = np.zeros((H, W), dtype=bool)
    m[y0:y1, x0:x1] = True
    return m


def make_frame(ax=10, ay=30, aw=16, ah=40, bx=50, strap_on="A", strap_frac=0.18):
    """RightLeg=A (left on canvas), LeftLeg=B. strap = horizontal band
    across the top of its parent leg; decal = small patch on B."""
    A = box(ax, ay, ax + aw, ay + ah)
    B = box(bx, ay, bx + aw, ay + ah)
    subs = {}
    sh = max(2, int(ah * strap_frac))
    if strap_on == "A":
        subs["RightLeg.strap"] = box(ax + 2, ay + 4, ax + aw - 2, ay + 4 + sh)
    elif strap_on == "B":
        subs["LeftLeg.strap"] = box(bx + 2, ay + 4, bx + aw - 2, ay + 4 + sh)
    subs["LeftLeg.decal"] = box(bx + 4, ay + ah - 12, bx + 9, ay + ah - 7)
    return FrameSets({"RightLeg": A, "LeftLeg": B}, subs)


def tokens(frame, order=("RightLeg", "LeftLeg"), roles=None):
    roles = roles or {"RightLeg": "support", "LeftLeg": "kick"}
    out = []
    for name in order:
        markers = tuple(sorted(k.split(".", 1)[1] for k in frame.subsets if k.startswith(name + ".")))
        out.append(Token(name, markers, roles.get(name, "")))
    return tuple(out)


SPEC = Spec(
    required_markers={"RightLeg": ("strap",), "LeftLeg": ("decal",)},
    reference_proportion={},
)
ref = make_frame()
SPEC.reference_proportion = {
    "RightLeg.strap": float(np.count_nonzero(ref.subsets["RightLeg.strap"])) / float(np.count_nonzero(ref.entities["RightLeg"])),
    "LeftLeg.decal": float(np.count_nonzero(ref.subsets["LeftLeg.decal"])) / float(np.count_nonzero(ref.entities["LeftLeg"])),
}

results = []


def run(label, fa, fb, ta, tb, dt, expect_pass):
    v = check_pair(fa, fb, ta, tb, SPEC, ref, dt_seconds=dt)
    ok = v.passed == expect_pass
    results.append(ok)
    print(v.prose(f"{label} (expect {'PASS' if expect_pass else 'FAIL'}) -> {'OK' if ok else 'MISMATCH'}"))
    print()


# 1. PASS: A moves and morphs taller; strap adjusts proportionately.
fa = make_frame()
fb = make_frame(ax=16, ah=46)
run("synthetic pass (move+morph, proportionate strap)", fa, fb, tokens(fa), tokens(fb), 0.1, True)

# 2. FAIL migration: strap jumps from RightLeg to LeftLeg.
fb = make_frame(strap_on="B")
tb = tokens(fb)
run("synthetic strap migration A->B", fa, fb, tokens(fa), tb, 0.1, False)

# 3. FAIL proportion: A grows 40 -> 66px tall, strap keeps absolute size.
fb = make_frame(ah=66, strap_frac=0.106)
run("synthetic proportion break (leg grows, strap does not)", fa, fb, tokens(fa), tokens(fb), 0.1, False)

# 4. FAIL containment: strap shifted partly outside its parent.
fb = make_frame()
bad = np.zeros_like(fb.subsets["RightLeg.strap"])
bad[30:38, 2:14] = True  # x 2..14 while leg A starts at x=10
fb.subsets["RightLeg.strap"] = bad
run("synthetic containment break (strap outside leg)", fa, fb, tokens(fa), tokens(fb), 0.1, False)

# 5. Transposition (depth order swaps, assignments unchanged):
#    FAIL at 25 fps (small interval, budget 0.8), PASS at 4 fps (budget 5).
fa = make_frame()
fb = make_frame()
ta = tokens(fa)
tb = tokens(fb, order=("LeftLeg", "RightLeg"))
run("synthetic transposition @25fps", fa, fb, ta, tb, 0.04, False)
run("synthetic transposition @4fps", fa, fb, ta, tb, 0.25, True)

# 6. FAIL insertion at normal rate: an undeclared entity appears.
fb = make_frame()
fb.entities["Candle"] = box(80, 10, 86, 22)
tb = tokens(fb) + (Token("Candle", (), "background"),)
run("synthetic undeclared entity appears @10fps", fa, fb, tokens(fa), tb, 0.1, False)

print(f"{sum(results)}/{len(results)} synthetic cases match expected verdicts")
assert all(results)

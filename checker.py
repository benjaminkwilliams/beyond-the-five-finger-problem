"""
Spike: three-way validation core for generated frame sequences.

Design (user-stated 2026-10-13):
  A frame pair (A -> B), adjacent frames only, must pass THREE gates
  against a reference/spec:
    1. Static validity: both frames individually satisfy the spec.
       Entities are named pixel sets; markers are named subsets
       (RightLeg = A, RightLeg.strap = A.s, containment A.s <= A).
       As an entity moves / morphs / is occluded, its subsets must
       adjust proportionately (share of the parent set, relative
       position inside it).
    2. Transition legitimacy: the change A -> B must be a legitimate
       perspective/action change. Identity assignment (which entity
       carries which marker, which entity fills which action role)
       is invariant unless the spec's action declares a transfer at
       that transition. Centroid motion is bounded by a speed limit
       scaled by the frame interval.
    3. Visual Damerau-Levenshtein: the minimal weighted edit script
       (insertion / deletion / substitution / transposition) between
       the two frames' token structures must fit a budget that
       SCALES WITH THE FRAME INTERVAL (the user's frame-rate rule:
       fewer frames = larger legitimate gap, more frames = smaller).

  Marker conflict rule: no marker kind wins. The spec's assignment
  must be coherent; a conflict is a FAIL for the frame / frame set.

Scope (user-stated): stylised / limited-detail generated animation.
Photorealistic is out of scope. CPU-only: all operations here are set
arithmetic on masks and a small dynamic program.

Tokens: a frame's token structure is an ordered tuple (front-to-back
depth order from the spec) of entity tokens. An entity token carries
its name, its marker signature, and its action role. The token string
is what the visual Damerau-Levenshtein runs over, and the operation
trace is what becomes the prose finding (named sets exist so changes
can be expressed in prose / prompts).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

# ---------------------------------------------------------------- sets


@dataclass
class FrameSets:
    """Pixel-set assignments for one frame (the proposer's output)."""

    entities: dict[str, np.ndarray]  # name -> bool mask
    subsets: dict[str, np.ndarray]  # "Entity.marker" -> bool mask

    def parent_of(self, subset_name: str) -> str:
        return subset_name.split(".", 1)[0]


def containment_violations(frame: FrameSets) -> dict[str, int]:
    """Pixels of each subset lying outside its parent entity."""
    out = {}
    for name, mask in frame.subsets.items():
        parent = frame.entities[frame.parent_of(name)]
        out[name] = int(np.count_nonzero(mask & ~parent))
    return out


def proportion(frame: FrameSets, subset_name: str) -> float:
    parent = frame.entities[frame.parent_of(subset_name)]
    denom = int(np.count_nonzero(parent))
    if denom == 0:
        return 0.0
    return int(np.count_nonzero(frame.subsets[subset_name])) / denom


def relative_centroid(frame: FrameSets, subset_name: str) -> tuple[float, float]:
    """Subset centroid in parent-bbox-relative coordinates (0..1)."""
    parent = frame.entities[frame.parent_of(subset_name)]
    sub = frame.subsets[subset_name]
    pys, pxs = np.where(parent)
    if len(pys) == 0 or np.count_nonzero(sub) == 0:
        return (0.0, 0.0)
    sys_, sxs = np.where(sub)
    x0, x1 = pxs.min(), max(pxs.max(), pxs.min() + 1)
    y0, y1 = pys.min(), max(pys.max(), pys.min() + 1)
    return ((sxs.mean() - x0) / (x1 - x0), (sys_.mean() - y0) / (y1 - y0))


def centroid(mask: np.ndarray) -> tuple[float, float]:
    ys, xs = np.where(mask)
    if len(ys) == 0:
        return (0.0, 0.0)
    return (float(xs.mean()), float(ys.mean()))


# ------------------------------------------------------------- gate 1


@dataclass
class Spec:
    required_markers: dict[str, tuple[str, ...]]  # entity -> markers it must carry
    reference_proportion: dict[str, float]  # "Entity.marker" -> share in reference
    proportion_tolerance: float = 0.35  # relative deviation allowed
    rel_centroid_tolerance: float = 0.30


def gate1_static(frame: FrameSets, spec: Spec, ref_frame: FrameSets) -> list[str]:
    """Both-frames-individually-valid check. Returns prose findings."""
    findings = []
    for name, px in containment_violations(frame).items():
        if px > 0:
            findings.append(f"{name}: {px}px lie outside parent {frame.parent_of(name)} (containment)")
    for entity, markers in spec.required_markers.items():
        for m in markers:
            key = f"{entity}.{m}"
            if key not in frame.subsets or np.count_nonzero(frame.subsets[key]) == 0:
                findings.append(f"{key}: required marker missing")
    for key, ref_p in spec.reference_proportion.items():
        if key in frame.subsets and key in ref_frame.subsets:
            p = proportion(frame, key)
            if ref_p > 0 and abs(p - ref_p) / ref_p > spec.proportion_tolerance:
                findings.append(
                    f"{key}: proportion {p:.3f} vs reference {ref_p:.3f} "
                    f"(no proportionate adjustment)"
                )
            rc = relative_centroid(frame, key)
            rr = relative_centroid(ref_frame, key)
            drift = math.hypot(rc[0] - rr[0], rc[1] - rr[1])
            if drift > spec.rel_centroid_tolerance:
                findings.append(f"{key}: relative position drift {drift:.2f} inside parent")
    return findings


# -------------------------------------------- tokens + visual DL (gate 3)


@dataclass(frozen=True)
class Token:
    entity: str
    markers: tuple[str, ...] = ()
    role: str = ""  # action role this entity fills in this frame

    def __str__(self) -> str:
        m = ",".join(self.markers)
        return f"{self.entity}[{m}]@{self.role}" if self.role else f"{self.entity}[{m}]"


# weighted operation costs: identity-bearing changes are expensive,
# small pose drift is not represented in tokens at all (it is gate 2's
# centroid/proportion territory).
COST = {"insertion": 2.0, "deletion": 2.0, "substitution": 3.0, "transposition": 3.0}


def _sub_cost(a: Token, b: Token) -> float:
    return 0.0 if a == b else COST["substitution"]


def visual_dl(a: tuple[Token, ...], b: tuple[Token, ...]):
    """Damerau-Levenshtein (optimal string alignment) with op trace.

    Returns (weighted_cost, ops) where ops are prose strings.
    """
    n, m = len(a), len(b)
    INF = float("inf")
    # dp[i][j] = cost of turning a[:i] into b[:j]; back[i][j] = (kind, prev_i, prev_j)
    dp = [[INF] * (m + 1) for _ in range(n + 1)]
    back: list[list[tuple | None]] = [[None] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    for i in range(1, n + 1):
        dp[i][0] = dp[i - 1][0] + COST["deletion"]
        back[i][0] = ("del", i - 1, 0)
    for j in range(1, m + 1):
        dp[0][j] = dp[0][j - 1] + COST["insertion"]
        back[0][j] = ("ins", 0, j - 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            c = dp[i - 1][j - 1] + _sub_cost(a[i - 1], b[j - 1])
            if c < dp[i][j]:
                dp[i][j] = c
                back[i][j] = ("sub" if a[i - 1] != b[j - 1] else "match", i - 1, j - 1)
            c = dp[i - 1][j] + COST["deletion"]
            if c < dp[i][j]:
                dp[i][j] = c
                back[i][j] = ("del", i - 1, j)
            c = dp[i][j - 1] + COST["insertion"]
            if c < dp[i][j]:
                dp[i][j] = c
                back[i][j] = ("ins", i, j - 1)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                c = dp[i - 2][j - 2] + COST["transposition"]
                if c < dp[i][j]:
                    dp[i][j] = c
                    back[i][j] = ("trans", i - 2, j - 2)
    ops: list[str] = []
    i, j = n, m
    while i > 0 or j > 0:
        step = back[i][j]
        if step is None:
            break
        kind, pi, pj = step
        if kind == "sub":
            ops.append(f"substitution: {a[pi]} -> {b[pj]}")
        elif kind == "del":
            ops.append(f"deletion: {a[pi]} disappears")
        elif kind == "ins":
            ops.append(f"insertion: {b[pj]} appears")
        elif kind == "trans":
            ops.append(f"transposition: {a[pi]} and {a[pj + 1]} swap order")
        i, j = pi, pj
    ops.reverse()
    return dp[n][m], ops


# ---------------------------------------------------------------- pair


@dataclass
class PairVerdict:
    passed: bool
    gate1: list[str] = field(default_factory=list)
    gate2: list[str] = field(default_factory=list)
    dl_cost: float = 0.0
    dl_budget: float = 0.0
    dl_ops: list[str] = field(default_factory=list)

    def prose(self, label: str) -> str:
        head = "PASS" if self.passed else "FAIL"
        lines = [f"{label}: {head} (DL cost {self.dl_cost:.1f} vs budget {self.dl_budget:.2f})"]
        for f in self.gate1:
            lines.append(f"  gate1: {f}")
        for f in self.gate2:
            lines.append(f"  gate2: {f}")
        for op in self.dl_ops:
            lines.append(f"  gate3 op: {op}")
        return "\n".join(lines)


def check_pair(
    fa: FrameSets,
    fb: FrameSets,
    tokens_a: tuple[Token, ...],
    tokens_b: tuple[Token, ...],
    spec: Spec,
    ref_frame: FrameSets,
    dt_seconds: float,
    max_speed_px_per_s: float = 4000.0,
    edit_rate_per_s: float = 20.0,
    declared_transfers: frozenset[str] = frozenset(),
) -> PairVerdict:
    """Full three-way validation for one adjacent pair."""
    v = PairVerdict(passed=True)
    v.gate1 = gate1_static(fa, spec, ref_frame) + gate1_static(fb, spec, ref_frame)
    # Gate 2: identity assignment continuity + bounded motion.
    assign_a = {t.entity: (t.markers, t.role) for t in tokens_a}
    assign_b = {t.entity: (t.markers, t.role) for t in tokens_b}
    for entity in sorted(set(assign_a) ^ set(assign_b)):
        if entity not in declared_transfers:
            v.gate2.append(f"{entity}: entity appears/disappears with no declared transfer")
    for entity in sorted(set(assign_a) & set(assign_b)):
        if assign_a[entity] != assign_b[entity] and entity not in declared_transfers:
            v.gate2.append(
                f"{entity}: assignment changed {assign_a[entity]} -> {assign_b[entity]} "
                f"with no declared transfer"
            )
    for entity in sorted(set(fa.entities) & set(fb.entities)):
        ca, cb = centroid(fa.entities[entity]), centroid(fb.entities[entity])
        dist = math.hypot(cb[0] - ca[0], cb[1] - ca[1])
        if dist > max_speed_px_per_s * dt_seconds:
            v.gate2.append(
                f"{entity}: centroid moved {dist:.0f}px in {dt_seconds:.3f}s "
                f"(over speed bound {max_speed_px_per_s * dt_seconds:.0f}px)"
            )
    # Gate 3: visual Damerau-Levenshtein vs interval-scaled budget.
    v.dl_cost, v.dl_ops = visual_dl(tokens_a, tokens_b)
    v.dl_budget = edit_rate_per_s * dt_seconds
    v.passed = not v.gate1 and not v.gate2 and v.dl_cost <= v.dl_budget
    return v

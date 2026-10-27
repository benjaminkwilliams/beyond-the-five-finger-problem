#!/usr/bin/env python3
"""M2.4: phase-scaled keyframe-boundary budget.

Within-phase pairs: budget 2.00 (M1 constant).
Action-boundary pairs (chamber -> snap, snap ->
recoil, etc.): budget 4.00 — larger, because a
legitimate phase change moves more, but still
BELOW the swap cost (6.00), so a boundary budget
cannot pass a swap. That is the load-bearing test:
boundary budget 4.0 < swap 6.0.
Phases are named per frame in the sequence; a
pair whose phases differ is a boundary pair.
"""
WITHIN_BUDGET = 2.00
BOUNDARY_BUDGET = 4.00
SWAP_COST = 6.00


def budget(phase_a, phase_b):
    return BOUNDARY_BUDGET if phase_a != phase_b else WITHIN_BUDGET


if __name__ == "__main__":
    assert budget("chamber", "chamber") == 2.00
    assert budget("chamber", "snap") == 4.00
    assert BOUNDARY_BUDGET < SWAP_COST, "boundary budget must not pass a swap"
    print("boundary: within 2.00, boundary 4.00, swap 6.00 still fails — PASS")

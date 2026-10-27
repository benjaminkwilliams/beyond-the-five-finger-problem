# Beyond the Five Finger Problem — submission summary

- Title: Beyond the Five Finger Problem
- Track: Indie Developer Track, theme Build for Your World
- Repo (public): https://github.com/benjaminkwilliams/beyond-the-five-finger-problem
- Submission due: Nov 4, 2026, 9:00 PM ET / 8:00 PM CT
- Demo video: 3 minutes, scripted from the M3 lead demo
  (runs/results/report_m3.md) — recorded after freeze.

## Problem

Generative models draw individual frames that look fine
while the sequence is broken: a leg swaps mid-kick, a
guard mirrors, a facing flips. No current tool checks a
sequence for continuity — it checks frames, or it checks
vibes. The failure mode is invisible to per-frame QA.

## Engine

ONE harness engine for creative-generation and
programming/agent work, with the VERIFIER as the star
module. Five nodes, spec as shared state, structured
records on edges: GENERATOR -> PROPOSER -> CHECKER ->
AMENDER -> BENCH-JUDGE.

## Generators

(A) Muse media pipeline. (B) Meta Image API
muse-image-1.0 via meta_image.py, dispatched by
graph.generator(): generations (text only) and sidecar
edits (skeleton in, drawing out); guard generation
12.6s, snap edit 21.9s, both full-size checked. The
verifier is generator-agnostic — proposer, checker,
amender, and bench-judge run unchanged on either
generator's frames.

## Verifier

Three-way validation for ADJACENT frame pairs only:
(1) both frames individually valid against the spec,
(2) legitimate perspective/action change,
(3) visual Damerau-Levenshtein distance, budget
scaling with frame interval. "Code" = formal set
definitions: an entity is a pixel set, a marker is a
named subset. Marker conflict = FAIL, no marker kind
wins. Extraction is a MODEL PROPOSAL guided by the
glossary; the checker is deterministic and CPU-only
(no GPU, 2 CPU cores). Photorealistic scale is out
of scope.

Calibrated weights (M2.3, in the open): role
substitution 3.0, facing change 3.0, marker appearing
alone 1.0, marker changing identity 3.0, budget 2.00
within-phase, 4.00 at an action boundary (swap 6.00
still fails).

## Lead demo

A leg swap mid-sequence where individual frames look
fine and the sequence is broken. SadPocky v2 10->11
FAILs at DL 6.0, neighbours PASS, no smearing. The
same rule caught a swap in a newly generated Sensei
kick (chamber->snap and full->recoil FAIL), with an
amender instruction naming the leg to lock instead
of a re-roll.

## Debugging artifact

docs/infographic/workflow-debug-v2.png (2000x6514
vertical, Spec at top, final output at bottom) is the
what-calls-what map of the harness: every node, API,
and service with first-line kind tags.

## Judging-criteria mapping

- Impact 30%: sequence continuity is the gap between
  "looks fine" and "moves right" for every generative
  video/frame tool, not just this character set.
- Meta tooling 25%: built on Meta Model API — Spark
  1.3 as proposer, SAM 3.1 for real pixel masks, Meta
  Image API muse-image-1.0 as a second generator node.
- Technical Depth 20%: set-based checker math,
  calibrated DL, boundary budgets, GLAMR-derived
  sequence judging, skeleton-first generation.
- Demo 25%: the M3 lead demo, runnable from the repo
  (demo_m3.py), plus the 3-minute video.

## Honest limits (stated in the repo, not hidden)

- Generated drawings carry no side markers, so a
  proposer cannot assign Starboard/Port from an
  unmarked drawing — generated-sequence verdicts are
  human role readings until markers are in the drawing.
- Drawing over a sidecar is loose conditioning, not a
  lock; the lock is the checker + amender loop.
- Edit rate 20/s is uncalibrated; arms/shoulders
  checker integration and sizing/character-data layers
  are deferred.

## Portal field list

Status 2026-10-27: portal field list still UNRESOLVED
— portal failed to load 5x on Oct 26, and no portal
check was run in this packaging pass (M4 blocker if
it still fails on re-check before Nov 3). Do not claim
a field list that has not been read from the portal.

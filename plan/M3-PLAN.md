# M3 — Graph loop + lead demo + freeze (Wed 2026-10-28, 9:30 AM milestone)

Five-node graph, spec as shared state, structured
records on edges. Nodes:
  GENERATOR — produces frames from a skeleton
    (Sensei sequence) or supplies bench frames.
  PROPOSER — model proposal of per-frame set
    assignments (M1: Spark + sidecar dots).
  CHECKER — deterministic, CPU-only: calibration
    DL (M2.3), boundary budget (M2.4), sequence
    judge (M2.6), proportions (M2.5), facing rings
    (M2.1), masks (M2.2).
  AMENDER — takes a checker FAIL and produces a
    repair instruction in named-set language
    (never a silent re-roll, never a mirror).
    For a role swap: "StarboardLeg is kick in
    all frames; frame N assigns it support —
    regenerate frame N with StarboardLeg kick,
    PortLeg support, facing unchanged."
  BENCH-JUDGE — verdict vs ground truth on bench
    + holdout, never tuned to holdout.

Exit criteria:
- [x] Graph runs end-to-end on SadPocky v2 9-12:
  swap pair FAILs, neighbours PASS, no smearing.
  DONE 2026-10-27, demo_m3.py, commit e6efeaf.
- [x] Graph runs on the Sensei GIF drawings:
  2->3 and 4->5 role changes FAIL (the swap
  the user caught 2026-10-27), with an amender
  instruction naming the leg to lock.
  DONE 2026-10-27, demo_m3.py. Guard is the
  anchor, not judged (M2.6 rule).
- [x] Readable report in runs/results/report_m3.md.
- [x] Repo freeze recorded: commit + push, freeze
  state in this plan. FREEZE 2026-10-27:
  Follow-up 2026-10-27 (post-freeze, recorded,
  not silent): Meta Image API added as a
  GENERATOR node (meta_image.py + graph.
  generator()). muse-image-1.0 confirmed on the
  account; /images/generations verified live
  (guard, 12.6s) and /images/edits verified live
  (snap from skeleton sidecar, 21.9s; first JSON
  shape rejected with a clear error — `image`
  only for multipart — corrected to
  images[].image_url per the live error). The
  verifier runs unchanged on either generator.
  remote main e6efeaf, M1 closed, M2 closed,
  M3 graph + demo green. Further work goes to
  M4 packaging or a new plan, not silent edits
  to frozen code.

Follow-up 2026-10-27 (post-freeze, recorded,
not silent): amender fixed to the spec-mismatch
rule, user-approved. graph.amender() used to
say "regenerate the later frame" per FAIL pair,
which regenerated recoil for full->recoil, where
recoil was correct and full was wrong. New rule:
regenerate exactly the frames whose kick
assignment disagrees with spec kick_side, anchors
(no kick role) skipped. Sensei: snap + full.
SadPocky: 11 AND 12 — both extension frames use
the wrong leg, so fixing 11 alone would open a
new swap at 11->12. Demo asserts both targets.
Assumes one kick side per sequence; phase-varying
kick side needs per-phase spec.

Correction 2026-10-27 (user, recorded, not
silent): product success is ALL pairs PASS.
A bench-judge PASS on an expected FAIL/PASS/
FAIL pattern is a checker-accuracy test only —
it proves the checker detects a known swap, it
is NOT a passing generation. A generation with
any FAIL pair is failed output, however
accurately the checker caught it. The Sensei
filmstrip v5 is therefore a FAILED output, not
a passing demo. The retry loop (not yet built)
must run until all pairs PASS or hit its cap
and report failure; it must never ship FAILs
as a pass.

Retry loop 2026-10-27 (user-approved, single
retry for the proof run): graph.retry_loop()
with product_verdict() — PASS iff every judged
pair PASSes. Attempt 0 is the original frames;
each retry regenerates ONLY spec-mismatching
frames via fix_frame, then re-checks; stops on
first all-PASS or when retries run out, never
loosening the checker. Synthetic test: fix that
corrects -> PASS at attempt 1; no-op fix ->
FAIL after 1 retry. Sensei retry 1 (Meta Image
edits from skeleton sidecars, 12.2s snap, 11.6s
full): frames changed, but side is NOT
verifiable from unmarked drawings — geometry
matches the sidecar in both old and new frames,
so a PASS cannot be certified from the drawing
alone. That gap, not the loop, is now the
blocker for a closed loop: markers in the
drawing (character-data layer) or a human eye
reading per retry.

Open, recorded 2026-10-27: generated drawings
carry no side markers, so a proposer cannot
assign Starboard/Port from the drawing alone —
the Sensei GIF verdict is by human role reading,
not by proposer assignment, until markers are
in the drawing (character-data layer, deferred).

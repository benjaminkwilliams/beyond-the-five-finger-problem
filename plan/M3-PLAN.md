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

Diagnostic correction 2026-10-27 (user):
leg identity is read by HIP CHAIN, not foot
screen position. A leg is the hip it hangs
from, followed hip->knee->foot. Frame 2
(chamber): image hip chains match the sidecar
chains. Frame 3 (snap): they do not — the
image extended leg hangs from the Port hip
while the sidecar extends the Starboard hip.
Foot image-right in both cases, which is why
a foot-position reading passes a wrong frame.
Spark yaw is NOT this check: yaw is facing
direction only (idle sheets), identical for
chamber and snap (both image-right), and it
was never run on the Sensei frames.
Retry-1 payload audit (meta_image.edit):
POST /v1/images/edits, muse-image-1.0, prompt
text + skeleton sidecar PNG ONLY. Missing:
no colour legend (prompt never said red =
Starboard, blue = Port; sidecar carries no
labels), no chamber frame for continuity, no
character sheet. Result dissociation proves
the point: retry geometry followed the sidecar
while side identity did not change — pose is
conditioned, identity is not constrained.

Labeled sidecars + Python-built input 2026-10-27
(user-directed): render_skeleton_labeled.py draws
the skeleton with coloured glyphs instead of dots —
red star = Starboard, blue disc = Port — plus a
legend header, STARBOARD/PORT FOOT + KICK/PLANTED
labels at the feet, and a footer naming frame,
facing, kick, support. Hip/knee joints carry glyphs
only (hip word labels collided: hips are 20 units
apart in the source). prompt_builder.py (prompt-v1)
builds prompt + image list deterministically: same
inputs -> same prompt string, verified by repeat
build; fixed order [labeled sidecar, previous frame
drawing], fixed phase wording, legend repeated in
words, hip-chain instruction in words. meta_image.
edit() now takes a list of images. Retry 2 (snap
13.8s, full 13.3s, sequential: full used retry-2
snap as previous frame): previous-frame context
DID move identity — the chamber yellow sleeve
carried into both retry-2 frames. Side still
needs the user's hip reading; filmstrip v7 marks
retry pairs UNVERIFIED, not PASS.

Eye verdict 2026-10-27 (user, via main chat):
filmstrip v6 retry-1 snap and retry-1 full both
read STARBOARD, not Port. This closes the
UNVERIFIED block on SIDE IDENTITY for the
retry-1 frames only. It does NOT by itself make
any pair PASS — pair verdicts still come from
the checker. With retry-1 side certified, the
checker on the retry-1 sequence (guard, chamber,
retry-1 snap, retry-1 full, recoil) gives
chamber->snap PASS, snap->full PASS, full->recoil
PASS, all cost 0.0, product verdict PASS on leg
roles as encoded. Caveat, stated not hidden:
that checker run encodes leg roles only, so it
does not judge identity drift in the retry-1
full frame (barefoot vs shod elsewhere). Retry-2
(v7) side identity is NOT covered by this
verdict and stays open pending the user's hip
reading on v7.

CORRECTION 2026-10-27 — WITHDRAWN, do not
treat commit 861a501 as settled: the user
states the widget tap was NOT a verdict made
after seeing the frames — he had not seen them
in the main chat. The retry-1 Starboard verdict
above is therefore WITHDRAWN pending his visual
check of the retry frames now posted in the main
chat. Filmstrip v8, built on that verdict, is
likewise withdrawn and must not be cited as
certified. Current status, until he rules from
the images: retry-1 side identity OPEN /
UNVERIFIED, retry-2 side identity OPEN /
UNVERIFIED. Do not record either as correct or
incorrect, and do not build any certification,
checker encoding, or filmstrip on a verdict
that has not been made from the images.

Open, recorded 2026-10-27: generated drawings
carry no side markers, so a proposer cannot
assign Starboard/Port from the drawing alone —
the Sensei GIF verdict is by human role reading,
not by proposer assignment, until markers are
in the drawing (character-data layer, deferred).

Main-chat work, recorded here 2026-10-28 (this side chat stopped at
113e0af; the work below happened in main chat, not here, and is
recorded here so this thread does not redo or contradict it):

- Remote tip moved 113e0af -> 8470f71, pushed from main chat on
  the user's /push 2026-10-27 evening, byte-for-byte verified there:
  2024f35 prompt_builder v2/v3, 8470f71 docs/submission refresh.
  The SUBMISSION.md refresh is therefore no longer main chat's
  uncommitted edit — it is committed. The old "do not commit/push
  over it" note is superseded by that push.
- prompt_builder v2 (2024f35): full phase "slight forward lean"
  replaced by "torso moving backwards for balance", used live for
  sensei-full-torso-back-v1.webp (Meta Image edit, 19.9s, 1600x1600,
  labeled full sidecar + retry2 snap as previous frame).
- prompt_builder v3 (same commit): NONE-kick branch for guard/return
  — both feet planted, no kicking leg — used live for
  sensei-guard-match-v1.webp and sensei-return-match-v1.webp
  (12.9s / 12.6s, chamber / recoil-match as identity references).
- Frame 5 regenerated as sensei-recoil-match-v1.webp (12.9s,
  labeled recoil sidecar + torso-back full as previous frame;
  character override was input-only at that time, not a builder
  edit). User approved frame 5, then asked for frames 1 and 6 to
  match frames 2-5 — that is the v11 lineup.
- v11 lineup (filmstrip sensei-kick-filmstrip-v11.png, 2400x1180,
  verified on disk): guard-match, chamber, retry2 snap,
  torso-back full, recoil-match, return-match. Character look
  (short spiky black hair, black gi, shod) is consistent across
  v11 by the user's read — that is a look-consistency approval,
  NOT a side-identity certification.
- GIF: sensei-kick-v11-200ms-v1.gif, 6 frames, 200ms each,
  1600x1600, looping, verified on disk. Loop seam still jumps:
  guard-match and return-match are different drawings.
- Hip zoom v2 (sensei-hip-zoom-v2.png, 1410x2484, Oct 28 07:44,
  builder runs/current/build_hip_zoom_v2.py): chamber (known
  Starboard-kick reference), retry2 snap (current frame 3),
  torso-back v1 full (current frame 4), same crop box, labeled.
  It shows, without certifying: in both snap and full the extended
  leg is the front/upper leg, support behind and below, distinct
  trouser seam, parallel to chamber's layout. That alone does not
  settle hip chain.
- STANDING STATUS, unchanged by the main-chat work: side identity
  for frames 3 (snap) and 4 (full) is OPEN / UNVERIFIED pending the
  user's hip-chain ruling. That is the one question blocking the
  9:30 AM Oct 28 M3 gate. Do not record v11, the GIF, or hip zoom
  v2 as a side certification, and do not build a checker encoding
  or PASS filmstrip on them.

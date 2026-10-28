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

User ruling + verification, 2026-10-28 (v11, frames 2-5 Starboard):
User, after seeing v11 in this chat, ruled frames 2 to 5 all show
Starboard side movement. Verified here at full size (1600x1600 each)
against the actual files, by front/back order, not foot position:
- Frame 2 chamber: moving leg front/upper, knee right, foot tucked
  centre; support leg behind, vertical, planted at bottom.
- Frame 3 retry2 snap: moving leg front/upper, extended straight
  right; support leg behind/below, knee slightly bent, planted.
- Frame 4 torso-back full: same layout as snap, extended
  front/upper, support behind/below, planted.
- Frame 5 recoil-match: moving leg front/upper, folded, knee
  right, foot tucked centre; support leg behind, planted.
No frame switches front/back order across 2->5. Honest limit:
drawings carry no side markers, so "Starboard" here rests on
near-side = subject's right in a right-facing profile, continuity
with the chamber reference (previously hip-agreed), and the user's
eye ruling — not on a proposer assignment.
Checker run on the v11 encoding (guard NONE, chamber/snap/full/
recoil Starboard kick, return NONE): judged pairs chamber->snap
PASS cost 0.0, snap->full PASS cost 0.0, full->recoil PASS cost 0.0;
amender mismatches none. Raw guard->chamber and recoil->return
are cost 3.0 (role support<->kick) and are excluded as action
start/end anchors per the M2.6 anchor rule — that anchor
exclusion is still provisional, not a new user certification.
Frames 3 and 4 are therefore no longer UNVERIFIED: they are
user-certified Starboard on v11. This supersedes the
"frames 3/4 OPEN" status in the main-chat-work note above.

Generic starboard-kick workflow, 2026-10-28 (prompt-v4 + run_kick.py):
- prompt_builder prompt-v4: no Sensei default. character_desc
  and outfit_desc come from the profile; generic default is
  bare ("single character, flat black background"). Previous-
  frame line uses outfit_desc, not hard-coded "gi".
  Regression verified: with old v3 default + outfit="gi"
  + style=None, v4 prompt == v3 prompt for all 6 frames
  except the version stamp; image order identical.
  Unit tests: test_generic_kick.py, all PASS, no API calls.
- run_kick.py + profiles/sensei.json: profile supplies spec
  (Starboard/Port, image-right), character_desc, outfit_desc
  ("gi"), style_desc, skeleton_file, frame order. Runner
  renders labeled sidecars, validates sidecar KICK == spec
  kick (NONE for guard/return) before generating, builds
  inputs sequentially (guard sidecar alone, each later
  frame sidecar + previous generated frame), calls
  meta_image.edit, writes manifest + filmstrip with pair
  verdicts UNVERIFIED until eye-ruled. No per-character
  code branches. Sizing is a profile input: a non-adult
  character must supply its own scaled skeleton file;
  the idle-measurement sizing layer is still not built.
- Generic v1 run (runs/current/sensei-generic-v1, 75.7s):
  FAILED the "same output" test in one visible way:
  photorealistic man, not anime Sensei. Cause found:
  style was never in prompt-v3 — v11's anime look came
  only from previous-frame anime drawings, and a cold-
  start guard with no previous frame defaulted to the
  model's photorealistic bias. Leg order and identity
  consistency in v1 were otherwise correct (front/upper
  moving leg 2-5, support planted, same face/gi/hair).
  v1 is retained as evidence of the gap, not a
  deliverable.
- Fix: style_desc added to prompt_builder (one "Style:
  ..." line, only when a profile supplies it) and to
  profiles/sensei.json ("anime"). v3 regression with
  style=None still PASSes.
- Generic v2 run (runs/current/sensei-generic-v2, 77.8s:
  guard 12.2, chamber 12.8, snap 11.3, full 12.5, recoil
  14.5, return 14.5): anime, black gi, short spiky black
  hair, shod, flat black background, 1584x1616 frames.
  Assistant full-size reading: guard/return both planted;
  chamber/snap/full/recoil moving leg front/upper, support
  behind/below and planted, no front/back order switch
  across 2-5 — same class as v11. Differences from v11,
  honestly: no yellow sleeve (v2 is all black gi, cleaner
  against the profile), face is a fresh anime reading,
  not a pixel copy — the image model is nondeterministic,
  so "same output" means same sequence, same leg order,
  same character class, not byte-identical drawings.
  Checker on that reading: chamber->snap, snap->full,
  full->recoil all PASS cost 0.0, amender empty (same
  as v11 encoding). Filmstrip in v2 dir is UNVERIFIED:
  v2 side identity is NOT user-certified yet — it
  needs the user's hip-chain ruling from the v2
  filmstrip, like v11 did. Do not cite v2 as certified
  until he rules.

User verification, 2026-10-28 — generic v2 VERIFIED:
The user marked the generic v2 sequence as verified, after
seeing its filmstrip and 200ms GIF in this chat. This
supersedes the "v2 side identity is NOT user-certified
yet" status in the generic-workflow note above.
Frames 2-5 (chamber, snap, full, recoil) are now
user-certified Starboard on the generic run, same as
v11: moving leg front/upper, support behind/below and
planted, no front/back order switch. Checker on that
encoding (already run): chamber->snap, snap->full,
full->recoil all PASS cost 0.0, amender empty.
Guard/return remain NONE-kick anchors, excluded per
the provisional M2.6 anchor rule, not newly certified
as kick frames. The generic workflow (prompt-v4,
run_kick.py, profiles/sensei.json, test_generic_kick.py)
was pushed on this verification.

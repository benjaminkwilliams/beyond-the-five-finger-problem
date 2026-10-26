# Trajectory, colour-pattern, and polynomial paths (2026-10-26)

User-directed principles, tested on bench extraction
(SadPocky v2 9-12, Lila v10 9-12, joints in
extraction-test/joints.json, grid in
extraction-test/trajectory_grid.png).

## 1. Hip-foot opposition

For a normal humanoid character, the foot/shoe/sock is
on the OPPOSITE side of the leg from the hip. That is
already the leg-extremes rule in placement.py, but it
is now stated as a principle, not an implementation
accident: a leg has two ends, hip end and foot end,
and they are opposite. A foot candidate that is not
at the leg end opposite the hip is not a foot, even
if a prompt returned it.

## 2. Colour-pattern inference over multiple images

A foot/shoe/sock has a pixel colour PATTERN that is
consistent across frames for one character, even when
a SAM prompt fails on a particular frame. Learn the
pattern from frames where the foot is clear (extended),
then find it in frames where the prompt fails
(chambered), constrained by (1): search near the leg
end opposite the hip, not over the whole image.

Tested: SadPocky extended foot pattern (pink-ish:
R>G+30, B>G+20) found in the chambered frame at
[150,276] (chambered foot, expected box centre
~[153,285]) and [199,360] (planted foot, expected
~[209,363]) — within ~10px each. Colour alone is
NOT unique: the same pattern also matches 1,514
pixels in the head/ear region (y<200). Colour +
leg-end-opposite-hip together disambiguate; colour
alone does not. Mean colour over a foot mask does
NOT work: the mean [191,181,208] matches 5,829
pixels across the image. Use a pattern (a colour
relation, not a mean), and use it only near the
leg end.

This is the mechanism that would have found
SadPocky chambered feet before "pink shoe"/
"footwear" prompts were discovered — and it remains
the fallback when a prompt returns 0.

## 3. Stacked mocap polygons on a grid = a path

Stack the sidecar polygons from successive frames on
one grid, in frame coordinates, and each joint dot
traces a path. That path is NOT one polynomial over
a whole sequence. Fitted degree-2 polynomials over
SadPocky 9-12 and Lila 9-12 give:

- Hips and planted feet: max residual <10-20px —
  smooth within a phase, polynomial-like.
- Kicking (port) foot: max residual 46-51px (x and
  y) — the path breaks at the phase change
  (chamber 9-10, extension 11-12). The foot does
  not travel along one curve; it stays, then jumps
  to a new curve.
- Head x (SadPocky): residual 30px — the whole body
  shifts left at extension, another phase break.
- Starboard foot y (SadPocky): residual 34px — its
  role changes (chambered in 9-10, planted in
  11-12), so its path also breaks.

Conclusion: movement is PIECEWISE polynomial, with
breaks at action boundaries and role transfers —
the same boundaries spec v2 already treats
specially (HipRight role transfer at action-boundary
pairs only). A large polynomial residual is therefore
a DIAGNOSTIC, not necessarily an extraction error:
it flags a phase break or a role swap. A small
residual with a dot far from its neighbours flags
an extraction error. Do not fit one polynomial
across a phase break and call the residual a failure,
and do not fit degree 3 to 4 points and call
residual 0 a success — that is overfitting, not a
path.

## 4. Relation to the FFT spike (2026-10-22)

This is the same idea as the layered + Fourier
spike, restated in trajectory terms: represent each
joint's path as a continuous function through
keyframes (there, 1D FFTs per component/layer
boundary; here, polynomials per joint per phase),
and generate in-betweens as slices of that
function. The difference is scope: the FFT spike
was unadopted because it generates frames never
drawn, in tension with the drawn-frames-only rule.
Trajectory polynomials as a CHECKER diagnostic
and as a colour-pattern foot finder do NOT
generate frames — they check extracted dots and
find missing ones. That use is adopted here; the
generative use remains unadopted until the user
reconciles it, as before.

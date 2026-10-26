# SAM placement test, 2026-10-26 (bench frames only)

API: POST /v1/responses, model sam-3.1, text prompt + image.
Boxes only. Mask strings were returned but NOT decoded (format
is not COCO RLE; header looks like [height, width] of the box
region, body is a 94-char alphabet stream). Do not claim pixel
masks until that format is decoded and verified against a box.

Prompts tried on SadPocky v2 frames 9/10 and Raincoat frames 8/9:
"leg", "foot", "head". Full box list in sam-test/boxes.json
(local test output, not committed with the filmstrip).

## What separated

- "leg": 2 boxes in ALL 4 frames. Legs separate, even where
  they touch. This is the core placement signal, and it works.
- "foot": 2 boxes in both B (extended) frames, 0 boxes in both
  A (chambered) frames. Feet are not reliably promptable when
  tucked/overlapping. Foot position must therefore be derived
  from the leg box (bottom centre), not from a separate foot
  prompt, at least on chambered frames.
- "head": 1 box in both A frames, roughly correct (head + hair
  + ears, centre ~30-50px above the face centre). 1 box in
  both B frames, WRONG: it covers the left half of the image,
  centre ~80px left of the true head. Head placement from SAM
  alone is not trustworthy on extended frames.

## What this means for automated placement

- Leg identity by SAM leg boxes alone is not enough: boxes
  are partial segments (thigh, shin), not whole legs, and box
  bottoms are ~20-40px off hand-placed foot tips. A leg box
  gives a region, not a joint. Joint extraction still needs a
  rule: e.g. foot = lowest pixel of the leg region, hip = top
  centre, then track regions across frames by overlap.
- Head + facing cannot come from the "head" prompt as-is on
  B frames. Alternatives to test next: "face" prompt, or head
  from the person box, or Spark for head/facing only while SAM
  supplies legs. Do not hand-fix head boxes on holdout.
- Mask decoding is the next technical step if pixel-accurate
  feet/hips are needed. Until then, report box-level only.

## Cost note

SAM image price per Model API page: $2.50 / 1,000 images.
The 12 calls in this test (4 frames x 3 prompts) are negligible
against the $150 hackathon credit, but a full proposer that
calls SAM per prompt per frame should batch prompts, not call
once per joint.

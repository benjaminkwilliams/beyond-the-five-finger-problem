# Placement architecture: SAM boxes + mocap dots (adopted 2026-10-26)

Two layers, neither alone is enough. User-supplied mocap form
(25 markers, diagram 2026-10-26) is the expansion template.

## Layer 1: SAM boxes — areas, not identity

SAM prompts return boxes for areas: head, torso, arm, hand,
hip, leg, foot. A box says "a leg is here". It does NOT say
which leg. Tested 2026-10-26: "leg" gives 2 boxes in all 4
bench frames, "foot" only on extended frames, "head" fails
on extended frames. See sam_test_notes.md.

## Layer 2: mocap dots — sided identity + context

Sidecar dots give what boxes cannot: right vs left, head
position vs head facing (white vs cyan vector), and the
polygon context (shoulder line, hip line, foot-to-hip).
A dot labels the box it aligns with: red foot dot + leg box
= StarboardLeg, blue foot dot + leg box = PortLeg, and so on.
The checker uses labelled boxes, never raw SAM boxes.

Current dot set (sidecar schema): Head, HeadFacing,
Starboard/Port Shoulder, Starboard/Port Hand, Starboard/Port Hip,
Starboard/Port Foot. Expansion template, from the user-supplied
25-marker form, when more dots are needed: chin, chest,
back, elbow l/r, radius l/r, ulna l/r, finger l/r, knee l/r,
ankle l/r, head front/left/back/right. Add dots only when a
case needs them; every added dot is another colour and
another association to get wrong.

## Alignment rule (measured 2026-10-26, bench frames)

Hand foot dots vs SAM leg boxes, 8 feet:
- Strict containment (dot inside box): 3 of 8.
- Within 20px tolerance: 5 of 8.
- Within 30px tolerance: 8 of 8, each foot uniquely nearest
  to one leg box (SadPocky A is the tightest: chambered foot
  24px from its box, planted foot 26px from its box).

Rule adopted: assign a dot to its nearest box of the matching
area type within 30px, only if that assignment is unique.
If two dots compete for one box, or a dot is farther than
30px from every matching box, the assignment is AMBIGUOUS,
not guessed. If a dot has no box at all, marker_seen=false.

Why tolerance is needed: SAM leg boxes are partial segments
(thigh, shin), not whole legs, so feet routinely sit just
outside their leg box. Strict containment would discard
correct feet.

## 2D projection / occlusion rules

Projected 2D images of 3D movement mean boxes overlap or
hide, depending on perspective. Rules:

- Overlap does not merge entities. Two leg boxes that
  overlap are still two legs if each has a distinct sided
  dot within tolerance. Overlap alone is not a swap.
- Hidden means hidden. If a limb's box is absent, or its
  dot cannot be placed because the joint is occluded, report
  marker_seen=false for that entity. Do not infer a hidden
  leg's role from the visible leg alone.
- Depth from overlap: the box/limb drawn over another at
  their crossing is the near one. This is a signal for the
  depth gate, not a replacement for it (see M1 gaps: a pure
  depth swap, same role, is not yet gated by DL cost alone).
- A box with no dot is an unlabeled area, not an entity.
  A dot with no box is an ungrounded claim, not a finding.
  Both cases are reported, neither is silently dropped or
  silently assigned.

## Bounded contexts

Foot, Shoe, and Sock are the SAME bounded context for
movement tracking: one foot area, not three entities.
placement.py already implements this by merging
overlapping shoe/sock/boot masks into one foot area
before linking to a leg. A sock changing colour, a shoe
changing style, or a boot vs shoe prompt difference does
not create a new entity; it is still the foot area at
the end of that leg.

## Out of scope for this phase

The following movement is explicitly NOT tracked in this
phase (user-stated 2026-10-26):

- A character walking, slipping on the floor, and
  falling, where the starboard leg moves superior to
  the torso (above torso level) causing the starboard
  shoe to come off and continue upward while the
  character lies on the ground.

Why it is out: it breaks the bounded context above
(the shoe becomes a detached, independently moving
object, not a foot area), it inverts the leg-torso
hierarchy (leg superior to torso), and it requires
tracking a detached object through a fall. None of
that is in the bench, the glossary, or the checker
for M1. If it ever enters scope, it needs its own
case, its own detached-object entity, and its own
bench pair — it must not be folded into the foot
area by accident.

## What is still hand-done

All dot coordinates in sidecar-test/ are hand-placed from
ground truth. The architecture above is the target for
automated placement (SAM boxes + dot extraction), not a
claim that automation exists yet. Holdout discipline:
develop placement on bench only, run once on holdout.

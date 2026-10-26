#!/usr/bin/env python3
"""Proposer v1 (M1): Spark proposes per-frame set assignments for a pair.

Input: two frame images, a character, and the glossary.
Output: assignments for frame A and frame B in the checker's vocabulary:
each assignment is (entity, markers, role, depth_rank), plus Facing.

The proposer does not check anything. It only proposes. The checker
in checker.py judges the proposal. A marker the model cannot see is
reported as marker_seen=false, never guessed: guessing a sided marker
is worse than missing one, because a mirrored marker is a FAIL.

Prompt discipline, from the spike lessons:
- Entity names are the character's own right/left, never image sides.
- Facing is image direction (candidate, flagged in the glossary).
- The same entity that starts a move must finish it, unless the pair
  is an action boundary with a declared transfer. The proposer is told
  which pairs are boundaries; it does not declare transfers itself.
- SadPocky strap vs skirt: separate by position/shape, not colour.
"""
import json

PROMPT_TEMPLATE = """You are a frame assignment proposer for an animation continuity checker.
You do NOT judge whether the pair passes or fails. You only report what you see, in the exact vocabulary below.

Character: {character}
Glossary (JSON): {glossary}

Two frames follow, in order: frame A, then frame B. They are adjacent frames of one kick action.
For EACH frame, report, in depth order (near leg first, depth_rank 0, then far leg, depth_rank 1):
- every entity in the glossary entity list for this character, exactly once
- its markers, from the glossary marker list for that entity, only if you can actually see them in that frame
- its action role: "kick" for the leg doing the kick, "support" for the planted leg, "" for Facing
- marker_seen: true only if you can see that marker in that frame; false if you cannot see it, even if you expect it to be there
- facing: "left" or "right", the direction she faces in the image

Roles, defined by pose, not by extension alone:
- "kick" = the ACTIVE leg of the kick action. In a chamber frame that leg is bent, knee raised, foot tucked. In an extension frame that leg is straight out to the side. The active leg is the same leg in both frames of a normal kick.
- "support" = the PLANTED leg bearing weight, foot on the ground, leg mostly vertical.
- A chamber frame has no extended leg yet. Do not assign "kick" to the planted leg just because it is in front, and do not assign "kick" to whichever leg looks longest.

Rules:
- Entity names Right/Left are the character's own right/left, NEVER image left/right. Track identity across the pair: the leg that chambers in frame A is the same leg in frame B unless the action visibly changes legs.
- {hard_case}
- If a marker is too small to see at this resolution, say marker_seen=false. Do not guess its leg.
- First, in the "description" field, describe in two sentences what each leg is doing in each frame (bent/chambered, planted, or extended) and which markers you can actually see. Then give the assignments. Reasoning first, assignments second.
- Output JSON ONLY, no prose outside the JSON, no markdown fences, exactly this shape:
{{"description": "...", "frame_a": [{{"entity": "...", "markers": ["..."], "marker_seen": true, "role": "...", "depth_rank": 0}}], "frame_b": [...], "facing_a": "right", "facing_b": "right"}}
Include a Facing entry in each frame list with role "" and depth_rank 2, and markers ["right"] or ["left"] matching facing_a / facing_b.
Depth: depth_rank 0 is the near (front) leg, drawn in front of the other leg. The active kicking leg is the near leg in the bench kick frames.
"""


def build_prompt(character, glossary):
    char = glossary["characters"][character]
    hard = char.get("hard_case", "Report only what you can see.")
    return PROMPT_TEMPLATE.format(
        character=character, glossary=json.dumps(char), hard_case=hard)


def parse_proposal(text, character, glossary):
    """Parse and validate a proposer reply. Returns (assignments_a, assignments_b, raw)."""
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError(f"no JSON object in proposer reply: {text[:300]}")
    data = json.loads(text[start:end + 1])
    char = glossary["characters"][character]
    allowed = set(char["entities"])
    out = []
    for key in ("frame_a", "frame_b"):
        frame = []
        seen = set()
        for item in data[key]:
            entity = item["entity"]
            if entity not in allowed:
                raise ValueError(f"unknown entity {entity!r} in {key}")
            if entity in seen:
                raise ValueError(f"duplicate entity {entity!r} in {key}")
            seen.add(entity)
            markers = tuple(m for m in item.get("markers", [])
                            if m in char.get("markers", {}).get(entity, ()))
            # Facing carries its direction as a marker in the checker vocabulary.
            if entity == "Facing":
                markers = (data.get("facing_a" if key == "frame_a" else "facing_b"),)
            frame.append((entity, markers, item.get("role", ""),
                          int(item.get("depth_rank", 0))))
        missing = allowed - seen
        if missing:
            raise ValueError(f"missing entities {sorted(missing)} in {key}")
        frame.sort(key=lambda a: a[3])
        out.append(frame)
    return out[0], out[1], data

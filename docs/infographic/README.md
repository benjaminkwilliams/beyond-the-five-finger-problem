# Workflow infographic

General workflow diagram (Unity-canvas-like), from the
user's infographic gist (rounded-card template v1.1).
General workflow only — individual nodes refine once
their steps are known.

- `workflow.yaml` — gist-renderer config (ecosystem
  preset, dark, 3200×2250, icons off).
- `render_infographic.py` — gist-style renderer
  (transcribed from the gist pages; the gist file
  download failed, so this is not a downloaded file).
  Run: `render_infographic.py --input workflow.yaml
  --output workflow-infographic-gist.png`
- `workflow-infographic-gist.png` — gist-renderer output,
  plus its `.render.json` manifest.
- `workflow_infographic.py` — earlier simulation
  renderer, and its output `workflow-infographic.png`.

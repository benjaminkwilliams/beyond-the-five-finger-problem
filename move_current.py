#!/usr/bin/env python3
"""Move a finished run from runs/current/ to its version folder.

Usage: python move_current.py <version> <language> <success|failure>
Example: python move_current.py v2 port-starboard success

The move happens AFTER the run finishes — success or failure,
both are versioned, failures are not discarded. The version
folder is runs/versions/<version>-<language>-<date>-<outcome>/,
with a manifest.json recording outcome, repo commit, glossary
version, and entity language. runs/current/ is recreated empty
for the next run, so a new run can never overwrite an old one.

Never run this during a job: it moves the files the job is
writing. Run it only after the job's exit status is known.
"""
import json, shutil, subprocess, sys
from pathlib import Path

version, language, outcome = sys.argv[1], sys.argv[2], sys.argv[3]
assert outcome in ("success", "failure"), "outcome must be success or failure"
src = Path("runs/current")
assert src.is_dir(), "runs/current/ does not exist"
import datetime
date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
dest = Path(f"runs/versions/{version}-{language}-{date}-{outcome}")
assert not dest.exists(), f"version folder already exists: {dest}"
commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
shutil.move(str(src), str(dest))
src.mkdir(parents=True, exist_ok=True)
manifest = {
    "entity_language": language,
    "glossary_version": version,
    "outcome": outcome,
    "repo_commit": commit,
    "rule": "A run lives in runs/current/ while it runs, then moves whole to its version folder. Historical runs are never edited.",
}
(dest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(f"moved runs/current/ -> {dest} (outcome={outcome}, commit={commit})")

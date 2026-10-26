#!/usr/bin/env python3
"""Archive a finished run into runs/versions/<version>-<language>-<date>/.
Run ONLY after the job finishes — never during it, so nothing in
flight is disturbed. Copies, never moves, and writes manifest.json.
Usage: python archive_run.py <version> <language> <logfile> [files...]
"""
import json, shutil, sys
from pathlib import Path

version, language = sys.argv[1], sys.argv[2]
logfile = sys.argv[3] if len(sys.argv) > 3 else None
files = sys.argv[4:] if len(sys.argv) > 4 else []
dest = Path(f"runs/versions/{version}-{language}-2026-10-26")
dest.mkdir(parents=True, exist_ok=True)
for f in files:
    src = Path(f)
    if src.is_file():
        shutil.copy(src, dest / src.name)
manifest = {
    "entity_language": language,
    "glossary_version": version,
    "files": [Path(f).name for f in files],
    "log": logfile,
    "rule": "Historical runs are never edited. Copies only.",
}
(dest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(f"archived {len(files)} files to {dest}")

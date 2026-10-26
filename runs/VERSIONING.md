# Run versioning

Historical runs are never edited. They are copied, as-is, into a
versioned folder, so a later language or code change cannot be
confused with what a run actually said at the time.

## Scheme

`runs/versions/<version>-<language>-<date>/`

- `<version>` is the glossary version in force for the run
  (e.g. `v1`, `v2`).
- `<language>` is the entity language of that run
  (`left-right` or `port-starboard`).
- `<date>` is UTC, the date the run was archived.

Each version folder contains a `manifest.json` with:
glossary version, repo commit, entity language, pairs run,
and any known contamination or loss in that version.

## Versions on disk

- `v1-left-right-2026-10-26/` — proposer v1 and extraction run7,
  Left/Right language, commits up to `e21a1f8`. Known loss,
  recorded not hidden: SadPocky v2 frames 10–12 sidecars in
  the flat `extraction-test/` directory were overwritten by
  SadPocky v6 sidecars of the same filename during the
  proposer v1.1 run, and the v1.1 results JSON keyed only by
  character+numbers, so v6 overwrote v2 10→11 and 11→12.
  The v1 files copied here are the ones that were not
  overwritten (Lila, Raincoat, bench joints run7, holdout
  joints, and the proposer v1 result JSONs). They are copies;
  the flat originals are left in place until the running
  job finishes, so nothing in flight is disturbed.

- `v2-port-starboard-2026-10-26/` — reserved for the
  Port/Starboard proposer v1.1 re-run, from commit
  `e201ae4` onward. It is filled by `archive_run.py`
  after that run finishes, not during it.

## Rule for future runs

A run writes its outputs to its version folder, or is
archived there immediately after it finishes, with a
manifest. A run never writes over another version's
folder, and never reuses a filename that another
character's frames already used — sidecar filenames
include the set folder (e.g. `sadpocky-green-v2-10-sidecar.png`),
which is what stopped the v1 collision from recurring.

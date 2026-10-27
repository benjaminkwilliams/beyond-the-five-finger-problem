#!/usr/bin/env python3
"""Telemetry for hackathon workflow runs.

User 2026-10-26 evening: "slow" is meaningless
without an SLA, and an SLA is meaningless without
telemetry. So every run records its durations, and
estimates for a future run come from past runs of
the same job — not from a guess, and not from a
language switch (Python stays; Rust is explicitly
NOT the answer to an unmeasured slowness).

Format: one JSON object per run in
runs/telemetry.jsonl (append-only, never edited):
  job, started, ended, duration_s, steps: [
    {name, duration_s, ...}], notes, source
Steps are the bottleneck units: a SAM call, a Spark
call, a frame, a pair — whatever the driver can
time honestly. A step with no timing is omitted,
never invented.

Estimate: mean and last duration for that job,
plus the slowest step across past runs (the
bottleneck). If a job has never run, the estimate
is "unknown", not a number.
"""
import json, os, time

PATH = "runs/telemetry.jsonl"


class RunTimer:
    def __init__(self, job, notes=""):
        self.job = job
        self.notes = notes
        self.start = time.time()
        self.steps = []
        self._step_start = None
        self._step_name = None

    def step_start(self, name):
        self.step_end()
        self._step_name = name
        self._step_start = time.time()

    def step_end(self):
        if self._step_name is not None:
            self.steps.append({
                "name": self._step_name,
                "duration_s": round(time.time() - self._step_start, 1),
            })
            self._step_name = None

    def finish(self, path=PATH):
        self.step_end()
        rec = {
            "job": self.job,
            "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.start)),
            "ended": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "duration_s": round(time.time() - self.start, 1),
            "steps": self.steps,
            "notes": self.notes,
            "source": "timer",
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(rec) + "\n")
        return rec


def load(path=PATH):
    if not os.path.exists(path):
        return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def estimate(job, path=PATH):
    """(mean_s, last_s, slowest_step, n) for a job, or None."""
    runs = [r for r in load(path) if r["job"] == job]
    if not runs:
        return None
    durations = [r["duration_s"] for r in runs]
    slowest = None
    for r in runs:
        for s in r.get("steps", []):
            if slowest is None or s["duration_s"] > slowest[1]:
                slowest = (s["name"], s["duration_s"])
    return (round(sum(durations) / len(durations), 1),
            durations[-1], slowest, len(runs))


if __name__ == "__main__":
    import sys
    for job in sorted({r["job"] for r in load()}):
        est = estimate(job)
        print(f"{job}: n={est[3]} mean={est[0]}s last={est[1]}s "
              f"slowest_step={est[2]}")
    if len(sys.argv) > 1:
        est = estimate(sys.argv[1])
        print(f"estimate {sys.argv[1]}: {est if est else 'unknown (no past runs)'}")

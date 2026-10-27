#!/usr/bin/env python3
"""Heartbeat for long-running hackathon drivers.

User request 2026-10-26 evening: a Python process
must ping the agent to write to chat every ~90s,
so a long run is never silent for 10 minutes and
then just finishes (or dies quietly).

Usage in a driver:
    from heartbeat import Heartbeat
    hb = Heartbeat("run_bench", total_steps=8)
    for step in steps:
        ... do work ...
        hb.tick(step_name)   # writes heartbeat.json
    hb.done()                # status=done, hook goes quiet

The heartbeat file lives at runs/current/
heartbeat.json (the current-run folder, so it is
archived with the run by move_current.py). A hook
(~/hooks/scripts/hackathon-progress.sh, poll 90s)
watches that file and wakes the agent when it
changes; the agent then writes a short progress
note to chat. The driver itself cannot write to
chat — the hook is the ping path.
"""
import json, os, time

PATH = "runs/current/heartbeat.json"
INTERVAL = 90  # seconds between pings, user-stated


class Heartbeat:
    def __init__(self, job, total_steps=None):
        self.job = job
        self.total_steps = total_steps
        self.start = time.time()
        self.last = 0
        self.step = "starting"
        self._write("running")

    def tick(self, step):
        """Record a step; writes at most every INTERVAL,
        plus immediately on a step change."""
        now = time.time()
        changed = step != self.step
        self.step = step
        if changed or now - self.last >= INTERVAL:
            self._write("running")

    def done(self):
        self._write("done")

    def _write(self, status):
        self.last = time.time()
        os.makedirs(os.path.dirname(PATH), exist_ok=True)
        tmp = PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump({
                "job": self.job,
                "status": status,
                "step": self.step,
                "elapsed_s": round(time.time() - self.start),
                "total_steps": self.total_steps,
                "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }, f, indent=2)
        os.replace(tmp, PATH)

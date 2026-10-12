# SPDX-License-Identifier: MIT
"""Stop, don't self-attest: who may say a session already ended?

stop-triage-cliff (parents/stop-triage-cliff) compiles each turn into
continue | cliff | stop | unsafe.  Two of those are internal (continue, cliff:
they rewrite the agent's own context and nothing leaves the process).  Two are
terminal (stop emits a verdict, unsafe pages a human): they leave the process.

witness-dont-self-attest (parents/witness-dont-self-attest) says a store cannot
vouch for itself across its own revert; only a record that does not go back
with the store can, and it must be re-opened at the moment of the side effect.

Joined: after a crash the agent resumes from a checkpoint.  Before it may emit a
terminal action it must ask "did this session already end?".  Who may answer?

  self/snapshot   the decision record inside the checkpoint (restored with it)
  cross/lagging   a copy of the checkpoint replicated on the same cadence (restored too)
  self/monotone   a terminal counter kept outside the checkpoint (never goes back)
  witness         the append-only outbox of emitted terminal records; read at resume,
                  re-opened right before emit; a moved head is a failed certificate
                  -> adopt the recorded terminal, emit nothing.

Stdlib only. No network, GPU, live model, vendor API, or product import.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import random
import sys
from typing import Dict, List, Optional, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
STC = os.path.join(HERE, "parents", "stop-triage-cliff")
sys.path.insert(0, STC)
_spec = importlib.util.spec_from_file_location("stc_experiment", os.path.join(STC, "experiment.py"))
stc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stc)  # type: ignore[union-attr]

from stop_stub import positive_rate, simulate_null_query  # noqa: E402
from triage_stub import hard_cost, kitchen  # noqa: E402

MODES = ("self/snapshot", "cross/lagging", "self/monotone", "witness")
TERMINAL = ("stop", "unsafe")
B = 0.18          # publication bias; every query is truly NoEffect (parent setup)
STOP_BUDGET = 20


def reports_for(seed: int, n: int = STOP_BUDGET) -> List[bool]:
    rng = random.Random(seed)
    p = positive_rate(B)
    return [rng.random() < p for _ in range(n)]


def stop_life(reports: Sequence[bool]) -> dict:
    """One life of the principled stop on a report stream."""
    out = simulate_null_query(B, STOP_BUDGET, reports=list(reports), policy="principled")
    return {"turn": out["stopped_at"], "verdict": out["final_vote"],
            "principled": out["stopped_at"] < STOP_BUDGET, "drift": out["drift_event"]}


def compile_turn(kind: str) -> dict:
    """Run the parent gate on a fixture whose action is `kind` (no stop evidence)."""
    items = kitchen()
    budget = hard_cost(items) - 1 if kind == "unsafe" else hard_cost(items) + 6
    sess = stc.Session(stc.SYSTEM, stc.TASK, prior_cliff=None, live=stc._long_live(6))
    # stop_budget=2: Layer1/Layer2 need t>=2, so the principled stop cannot fire before budget
    a = stc.horizon_triage_gate(stop_budget=2, items=items, budget=budget, session=sess,
                                token_pressure=(kind == "cliff"))
    return a


def digest(audit: dict) -> str:
    """Byte digest of what an action produced (context for internal, record for terminal)."""
    s = audit.get("session")
    body = {"action": audit["action"], "reason": audit["reason"]}
    if s is not None:
        body["ctx"] = [m.text for m in (s.prior_cliff or [])] + [m.text for m in s.live]
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


class Outbox:
    """Append-only record of terminal side effects (the world's copy: never restored)."""

    def __init__(self, lag: int = 0):
        self.records: List[dict] = []
        self.lag = lag  # ticks before a record becomes readable (a lagging, not reverting, witness)

    def emit(self, sid: str, action: str, verdict: Optional[str], tick: int) -> None:
        self.records.append({"sid": sid, "action": action, "verdict": verdict, "tick": tick})

    def head(self, sid: str, now: int) -> Optional[dict]:
        seen = [r for r in self.records if r["sid"] == sid and r["tick"] <= now - self.lag]
        return seen[-1] if seen else None

    def count(self, sid: str) -> int:
        return sum(1 for r in self.records if r["sid"] == sid)


def attested_terminal(mode: str, checkpoint: dict, monotone: Dict[str, dict],
                      outbox: Outbox, sid: str, now: int) -> Optional[dict]:
    """Does `mode` say this session already emitted a terminal record?"""
    if mode in ("self/snapshot", "cross/lagging"):
        return checkpoint.get("terminal")       # restored with (or lags with) the checkpoint
    if mode == "self/monotone":
        return monotone.get(sid)
    if mode == "witness":
        return outbox.head(sid, now)
    raise ValueError(mode)


def resume_and_act(mode: str, sid: str, checkpoint: dict, fresh: dict, monotone: Dict[str, dict],
                   outbox: Outbox, now: int, *, reopen_at_emit: bool = True,
                   frozen: Optional[dict] = None) -> dict:
    """Resume from `checkpoint`; `fresh` is what the gate computes in this life.

    Rule (join): a witnessed terminal wins over any fresh compile output.
    Internal actions never need permission: replaying them is a pure rewrite.
    """
    seen = attested_terminal(mode, checkpoint, monotone, outbox, sid, now) if frozen is None else frozen["seen"]
    if seen is not None:
        return {"verdict": "adopt", "action": seen["action"], "emitted": False}
    if fresh["action"] not in TERMINAL:
        return {"verdict": "replay", "action": fresh["action"], "emitted": False}
    if reopen_at_emit and mode == "witness":
        again = outbox.head(sid, now)
        if again is not None:   # head moved since resume: failed certificate
            return {"verdict": "adopt", "action": again["action"], "emitted": False,
                    "failed_certificate": True}
    outbox.emit(sid, fresh["action"], fresh.get("verdict"), now)
    monotone[sid] = {"action": fresh["action"], "verdict": fresh.get("verdict")}
    return {"verdict": "emit", "action": fresh["action"], "emitted": True}

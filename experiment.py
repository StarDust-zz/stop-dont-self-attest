#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""stop-dont-self-attest: 7 join assertions (stop-triage-cliff x witness-dont-self-attest)."""
from __future__ import annotations

import os
import subprocess
import sys
from collections import Counter
from typing import Dict, List, Tuple

from terminal_gate import (HERE, MODES, TERMINAL, Outbox, compile_turn, digest, reports_for,
                           resume_and_act, stop_life)

N_STOP, N_EACH = 40, 10
STOP_CELLS = ("none", "early", "mid", "late", "after")
OTHER_CELLS = ("none", "before", "after")


def _ok(cond, msg):
    if not cond:
        raise AssertionError(msg)


def restore_turn(cell: str, k: int) -> int:
    return {"early": 1, "mid": max(1, k // 2), "late": max(1, k - 1), "after": k}[cell]


def stop_case(seed: int, cell: str, mode: str, *, fresh_seed: int = 1000) -> dict:
    r = reports_for(seed)
    l1 = stop_life(r)
    k = l1["turn"]
    out, mono = Outbox(), {}
    out.emit(f"s{seed}", "stop", l1["verdict"], k)
    mono[f"s{seed}"] = {"action": "stop", "verdict": l1["verdict"]}
    res = {"kind": "stop", "seed": seed, "cell": cell, "k": k, "v1": l1["verdict"], "outbox": out}
    if cell == "none":
        res.update(verdict="no-crash", dup=False, contra=False)
        return res
    j = restore_turn(cell, k)
    own = j - 1 if mode == "cross/lagging" else j        # lagging copy is one checkpoint behind
    ckpt = {"turn": own, "terminal": {"action": "stop", "verdict": l1["verdict"]} if own >= k else None}
    l2 = stop_life(r[:j] + reports_for(fresh_seed + seed)[j:])
    now = k + 1
    a = resume_and_act(mode, f"s{seed}", ckpt, {"action": "stop", "verdict": l2["verdict"]}, mono, out, now)
    vs = [x["verdict"] for x in out.records]
    res.update(verdict=a["verdict"], dup=len(vs) > 1, contra=len(set(vs)) > 1, v2=l2["verdict"],
               drift2=l2["drift"], k2=l2["turn"], j=j)
    return res


def other_case(kind: str, idx: int, cell: str, mode: str) -> dict:
    sid = f"{kind}{idx}"
    a1 = compile_turn(kind)
    out, mono = Outbox(), {}
    if a1["action"] in TERMINAL:
        out.emit(sid, a1["action"], None, 1)
        mono[sid] = {"action": a1["action"], "verdict": None}
    res = {"kind": kind, "cell": cell, "outbox": out, "d1": digest(a1)}
    if cell == "none":
        res.update(verdict="no-crash", dup=False, identical=True)
        return res
    after = cell == "after" and mode != "cross/lagging"
    ckpt = {"terminal": ({"action": a1["action"], "verdict": None} if after and a1["action"] in TERMINAL else None)}
    a2 = compile_turn(kind)
    act = resume_and_act(mode, sid, ckpt, a2, mono, out, 2)
    res.update(verdict=act["verdict"], dup=out.count(sid) > 1, identical=digest(a2) == res["d1"])
    return res


def matrix(mode: str) -> List[dict]:
    rows = [stop_case(s, c, mode) for s in range(1, N_STOP + 1) for c in STOP_CELLS]
    for kind in ("unsafe", "cliff", "continue"):
        rows += [other_case(kind, i, c, mode) for i in range(N_EACH) for c in OTHER_CELLS]
    return rows


def tally(rows: List[dict]) -> dict:
    stop = [x for x in rows if x["kind"] == "stop"]
    internal = [x for x in rows if x["kind"] in ("cliff", "continue") and x["cell"] != "none"]
    return {
        "cases": len(rows),
        "dup_verdicts": sum(x["dup"] for x in stop),
        "contradicting": sum(x["contra"] for x in stop),
        "dup_pages": sum(x["dup"] for x in rows if x["kind"] == "unsafe"),
        "internal_replayed_identical": sum(x["verdict"] == "replay" and x["identical"] for x in internal),
        "internal_resumes": len(internal),
        "internal_blocked": sum(x["verdict"] == "adopt" for x in internal),
    }


def scenario_1():
    """Both parents still pass 7/7 from their copied folders."""
    got = {}
    for p in ("stop-triage-cliff", "witness-dont-self-attest"):
        d = os.path.join(HERE, "parents", p)
        r = subprocess.run([sys.executable, "experiment.py"], cwd=d, capture_output=True, text=True, timeout=600)
        got[p] = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:]
        _ok(r.returncode == 0 and "7/7" in got[p], (p, got[p]))
    return got


def scenario_2():
    """Internal actions replay byte-identically; terminal actions do not replay, they repeat."""
    same = {k: digest(compile_turn(k)) == digest(compile_turn(k)) for k in ("continue", "cliff", "unsafe")}
    _ok(all(same.values()), same)
    x = stop_case(8, "late", "self/snapshot")
    u = other_case("unsafe", 0, "before", "self/snapshot")
    _ok(x["dup"] and u["dup"], (x["dup"], u["dup"]))
    return {"compile_deterministic": same, "stop_records_after_resume": len(x["outbox"].records),
            "pages_after_resume": u["outbox"].count("unsafe0")}


def scenario_3():
    """NEW: matrix by attestation source."""
    t = {m: tally(matrix(m)) for m in MODES}
    for m in ("self/snapshot", "cross/lagging"):
        _ok(t[m]["dup_verdicts"] > 0 and t[m]["dup_pages"] > 0, (m, t[m]))
    for m in ("self/monotone", "witness"):
        _ok(t[m]["dup_verdicts"] == 0 and t[m]["dup_pages"] == 0 and t[m]["contradicting"] == 0, (m, t[m]))
    for m in MODES:
        _ok(t[m]["internal_blocked"] == 0 and t[m]["internal_replayed_identical"] == t[m]["internal_resumes"], (m, t[m]))
    _ok(t["cross/lagging"]["dup_verdicts"] > t["self/snapshot"]["dup_verdicts"], "lagging copy should add the 'after' cell")
    return t


def scenario_4():
    """Where the self-attested duplicates land, and how often the second verdict contradicts the first."""
    rows = [x for x in matrix("self/snapshot") if x["kind"] == "stop" and x["cell"] in ("early", "mid", "late")]
    by = {c: (sum(x["dup"] for x in rows if x["cell"] == c), sum(x["contra"] for x in rows if x["cell"] == c))
          for c in ("early", "mid", "late")}
    flips = Counter((x["v1"], x["v2"]) for x in rows if x["contra"])
    wrong1 = sum(x["v1"] == "Beneficial" for x in rows if x["cell"] == "late")
    _ok(all(d == N_STOP for d, _ in by.values()), by)
    _ok(by["early"][1] >= by["late"][1] and by["early"][1] > 0, by)
    return {"dup_contra_by_restore": by, "flips": dict(flips),
            "first_life_false_beneficial": f"{wrong1}/{N_STOP}"}


def scenario_5():
    """NEW: two workers resume the same checkpoint; witness re-opened at emit vs read at resume only."""
    res = {}
    for reopen in (False, True):
        dups = contra = failed = 0
        for s in range(1, N_STOP + 1):
            r = reports_for(s)
            k = stop_life(r)["turn"]
            out, mono = Outbox(), {}
            ckpt = {"terminal": None}
            frozen = {"seen": out.head(f"s{s}", k)}          # both read the witness at resume: empty
            lA = stop_life(r[:k - 1] + reports_for(1000 + s)[k - 1:]) if k > 1 else stop_life(r)
            lB = stop_life(r[:k - 1] + reports_for(2000 + s)[k - 1:]) if k > 1 else stop_life(r)
            resume_and_act("witness", f"s{s}", ckpt, {"action": "stop", "verdict": lA["verdict"]}, mono, out, k,
                           reopen_at_emit=reopen, frozen=frozen)
            b = resume_and_act("witness", f"s{s}", ckpt, {"action": "stop", "verdict": lB["verdict"]}, mono, out, k,
                               reopen_at_emit=reopen, frozen=frozen)
            vs = [x["verdict"] for x in out.records]
            dups += len(vs) > 1
            contra += len(set(vs)) > 1
            failed += bool(b.get("failed_certificate"))
        res["reopen_at_emit" if reopen else "resume_only"] = {"dup": dups, "contra": contra, "failed_cert": failed}
    _ok(res["resume_only"]["dup"] == N_STOP and res["reopen_at_emit"]["dup"] == 0, res)
    _ok(res["reopen_at_emit"]["failed_cert"] == N_STOP, res)
    return res


def scenario_6():
    """NEW: a witness that lags (never reverts). Lag only causes missed attestations, never false adopts;
    re-opening at emit recovers whenever the second life takes at least the lag to reach its own stop."""
    res = {}
    for lag in (0, 1, 2, 3, 5):
        dup_resume = dup_emit = false_adopt = 0
        for s in range(1, N_STOP + 1):
            r = reports_for(s)
            k = stop_life(r)["turn"]
            j = 1                                            # early restore: longest second life
            l2 = stop_life(r[:j] + reports_for(1000 + s)[j:])
            t_resume, t_emit = k + 1, k + 1 + (l2["turn"] - j)
            for reopen in (False, True):
                out = Outbox(lag=lag)
                out.emit(f"s{s}", "stop", "v1", k)
                seen = out.head(f"s{s}", t_resume)
                late = out.head(f"s{s}", t_emit) if reopen else None
                if seen is None and late is None:
                    if reopen:
                        dup_emit += 1
                    else:
                        dup_resume += 1
            # control: a session that never stopped must never be adopted
            ctl = Outbox(lag=lag)
            false_adopt += ctl.head(f"s{s}", 99) is not None
        res[lag] = {"dup_resume_only": dup_resume, "dup_reopen_at_emit": dup_emit, "false_adopt": false_adopt}
    _ok(all(v["false_adopt"] == 0 for v in res.values()), res)
    _ok(res[0]["dup_resume_only"] == 0 and res[1]["dup_resume_only"] == 0 and res[2]["dup_resume_only"] == N_STOP, res)
    _ok(all(v["dup_reopen_at_emit"] <= v["dup_resume_only"] for v in res.values()), res)
    _ok(res[2]["dup_reopen_at_emit"] < res[2]["dup_resume_only"], res)
    return res


def scenario_7():
    """Precedence: a witnessed terminal wins over a fresh compile; and the pack is clean."""
    conv = {}
    for mode in ("self/snapshot", "witness"):
        silent_unpage = page_after_verdict = 0
        for i in range(N_EACH):                               # life 1 escalated; operator raised budget
            out, mono = Outbox(), {}
            out.emit(f"u{i}", "unsafe", None, 1); mono[f"u{i}"] = {"action": "unsafe", "verdict": None}
            a = resume_and_act(mode, f"u{i}", {"terminal": None}, compile_turn("continue"), mono, out, 2)
            silent_unpage += a["verdict"] == "replay"
        for s in range(1, N_STOP + 1):                         # life 1 delivered a verdict; budget then dropped
            r = reports_for(s); l1 = stop_life(r)
            out, mono = Outbox(), {}
            out.emit(f"s{s}", "stop", l1["verdict"], l1["turn"]); mono[f"s{s}"] = {"action": "stop"}
            resume_and_act(mode, f"s{s}", {"terminal": None}, compile_turn("unsafe"), mono, out, l1["turn"] + 1)
            page_after_verdict += any(x["action"] == "unsafe" for x in out.records)
        conv[mode] = {"escalation_silently_superseded": silent_unpage, "page_after_verdict": page_after_verdict}
    _ok(conv["self/snapshot"]["escalation_silently_superseded"] == N_EACH and conv["self/snapshot"]["page_after_verdict"] == N_STOP, conv)
    _ok(conv["witness"] == {"escalation_silently_superseded": 0, "page_after_verdict": 0}, conv)
    needles = ("cosmi" + "cat", "svor" + "onov")
    scanned = 0
    for root, _, files in os.walk(HERE):
        if "__pycache__" in root:
            continue
        for fn in files:
            if fn.endswith((".py", ".md", ".txt")) or fn == "LICENSE":
                with open(os.path.join(root, fn), encoding="utf-8") as fh:
                    body = fh.read().lower()
                _ok(not any(n in body for n in needles), f"product name in {fn}")
                scanned += 1
    conv["files_scanned_clean"] = scanned
    return conv


SCENARIOS = [
    ("1_parents_bind", scenario_1),
    ("2_internal_replays_terminal_repeats", scenario_2),
    ("3_NEW_matrix_by_attestation_source", scenario_3),
    ("4_where_self_attested_duplicates_land", scenario_4),
    ("5_NEW_two_workers_reopen_at_emit", scenario_5),
    ("6_NEW_lagging_witness", scenario_6),
    ("7_witnessed_terminal_wins_and_clean", scenario_7),
]


def main() -> int:
    passed = 0
    for name, fn in SCENARIOS:
        try:
            detail = fn()
            passed += 1
            print(f"PASS  {name}: {detail}")
        except AssertionError as e:
            print(f"FAIL  {name}: {e}")
        except Exception as e:  # noqa: BLE001
            print(f"ERROR {name}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(SCENARIOS)} assertions passed")
    return 0 if passed == len(SCENARIOS) else 1


if __name__ == "__main__":
    raise SystemExit(main())

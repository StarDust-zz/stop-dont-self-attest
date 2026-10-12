# Stop-triage-cliff

A synergy deep-dive joining three keepers into one measurable
**product horizon triage gate**. The evidence/session stream and typed
working set are source (not an executable dump). Before the next turn
the gate compiles three stages — principled stop, Knowledge Triage by
type, then cliff truncate+signature under token pressure — into a final
action `continue | cliff | stop | unsafe`. Blind inject (full-budget
stop policy **and** uniform rate compaction **and** nested LLM
summarization of prior cliffs) is the AMMI-like lowering.

This is **not** a fresh arXiv pack. It reuses the discrete objects from:

- [stop-dont-drift](https://github.com/StarDust-zz/stop-dont-drift)
  (Sun & Guo, [arXiv:2609.24101](https://arxiv.org/abs/2609.24101))
  — evidence stream source; principled stop (KL + quality-peak); full-budget inject drifts
- [triage-dont-uniform](workspace triage-dont-uniform (StarDust publish queued))
  (Zerhoudi, Mitrović, Granitzer, *The Compaction Cliff in Long-Running
  AI Agent Memory*, CIKM 2026,
  [arXiv:2608.22752](https://arxiv.org/abs/2608.22752))
  — typed working set source; TypeCompact / TypeDecompose; uniform rate inject;
  below B_min escalate Unsafe
- [cliff-dont-drift](https://github.com/StarDust-zz/cliff-dont-drift)
  (Nguyen, Cho, Chen, Dettmers, *CliffCompaction: Cost-Efficient
  Compaction for Long-Horizon Coding Agents*, 23 Sep 2026,
  [arXiv:2609.26779](https://arxiv.org/abs/2609.26779))
  — live turns source; cliff truncate+signature never rewrite/nest;
  nested LLM summary inject drifts

Note: [stop-cliff-compile](https://github.com/StarDust-zz/stop-cliff-compile)
joins stop + cliff into `continue|cliff|stop` but has **no type triage**.
[triage-cliff-compile](https://github.com/StarDust-zz/triage-cliff-compile)
joins triage + cliff into `keep|cliff|unsafe` but has **no principled stop**.
This pack composes both into `continue|cliff|stop|unsafe`.

```
python3 experiment.py
```

No GPU. No live model. No vendor API. No product import. Pure Python
stdlib.

## The object

```
# Stage A — principled stop (stop-dont-drift)
evidence    = publication-biased report stream (source)
Layer1      = stop if KL(q_t ‖ q_{t−1}) < δ
Layer2      = stop if r_t < r_max − α
full-budget = never stop until t = B          <- inject
stop        = Layer1 ∨ Layer2 before B        # wins over cliff/continue

# Stage B — Knowledge Triage (triage-dont-uniform), if not stopped
K           = typed working set {C,P,B,F,E}
TypeCompact = pin C∪P; compress B/F; placeholder E
uniform     = type-blind highest-sim cut      <- inject
B_min       = token cost of pinned C∪P
Unsafe      = escalate when budget < B_min (no silent drop; skip cliff)

# Stage C — cliff compile (cliff-dont-drift), if continuing under pressure
S_t         = C_{t-1} ⊕ L_t
C_t         = Cliff(L_t)                      # truncate+signature; discard C_{t-1}
nest        = LLM summary of C_{t-1} ⊕ L_t    <- inject (rewrite)

# Final gate (precedence A > B > C)
stop        = principled halt before B
unsafe      = budget < B_min (escalate; skip cliff-over-drop)
cliff       = under typed budget ∧ token_pressure ∧ TypeCompact ∧ Cliff(L_t) ∧ ¬nest
continue    = under typed budget ∧ ¬token_pressure ∧ TypeCompact
blind       = full-budget ∧ uniform ∧ nest    <- must differ
```

**Claim.** A long-horizon evidence/session/typed-memory stream is not an
executable. The product gate joins principled stop, type-aware retention,
and cliff truncate+signature into one measurable
`continue|cliff|stop|unsafe` decision. Blind inject — keep retrieving to
budget **and** compact uniformly **and** nest LLM summaries of prior
cliffs — is a different lowering.

**Falsifier.** If blind full-budget+uniform+nest matched the gate on
action and fidelity; if principled stop did not win over cliff/continue
under pressure; if below B_min the gate silently dropped a pinned
constraint instead of `unsafe`; if TypeCompact lost a constraint at a
feasible budget where uniform kept every constraint; if nested summary
counted as faithful while cliff rewrote; if prior cliff nested into the
next and token mass nest-grew; if TypeDecompose still violated locality
while token-chunk did not; or if the gate failed to cover all four
actions on the right fixtures while blind did not drift — the join
collapses.

## What this pack tests (7/7 join, not each pack alone)

1. **Blind inject ≠ gate.** Full-budget + uniform + nested rewrite differs
   from the typed cliff gate on fidelity and retained constraints.
2. **Principled stop wins.** Even with token_pressure and adequate typed
   budget, principled stop returns `stop` before cliff/continue.
3. **Below B_min → unsafe.** Gate escalates rather than silently dropping
   a pinned constraint; uniform drops without escalate; unsafe skips cliff.
4. **Continue + TypeCompact pins.** Under budget, no pressure, no stop:
   typed retention keeps every constraint; uniform loses ≥1.
5. **Cliff faithful; nest unfaithful.** Under budget + pressure + no stop:
   cliff ⊆ source; nest rewrites.
6. **Prior cliff discarded.** C_t from L_t only; no nest-grow of prior
   cliff token mass into the next.
7. **Safe four-action contrast.** Gate can `stop` OR `cliff` OR `continue`
   OR `unsafe` on the right fixtures; TypeDecompose has 0 locality
   violations vs uniform chunk ≥1; concurrent blind drifts.

## Synergy

Deepens the stop/cliff/triage cluster:

- [stop-dont-drift](https://github.com/StarDust-zz/stop-dont-drift)
  — evidence is source; principled stop is the compile; full-budget drifts
- [stop-cliff-compile](https://github.com/StarDust-zz/stop-cliff-compile)
  — horizon gate `continue|cliff|stop` (no type triage; this pack adds it)
- [triage-dont-uniform](workspace triage-dont-uniform)
  — type is the compile for retention; uniform is inject
- [triage-cliff-compile](https://github.com/StarDust-zz/triage-cliff-compile)
  — type-aware cliff `keep|cliff|unsafe` (no principled stop; this pack adds it)
- [cliff-dont-drift](https://github.com/StarDust-zz/cliff-dont-drift)
  — live turns are source; cliff truncate+signature; nested summary drifts
- [compile-dont-inject](https://github.com/StarDust-zz/compile-dont-inject)
  — memory/context is source; state-conditioned compile vs AMMI

Here the product object is the **horizon triage gate**
`continue|cliff|stop|unsafe`.

## Keepers

If 7/7 pass: **Evidence/session/typed-memory stream is source; the
product gate compiles principled stop + type triage + cliff
truncate/signature into continue|cliff|stop|unsafe. Blind full-budget +
uniform + nested summary is the AMMI-like lowering.**

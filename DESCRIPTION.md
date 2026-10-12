# Stop, don't self-attest

A synergy deep-dive joining two published packs:

- [stop-triage-cliff](https://github.com/StarDust-zz/stop-triage-cliff)
  compiles each turn of a long-horizon agent into `continue | cliff | stop | unsafe`
  (principled stop > below-B_min escalation > cliff/continue).
- [witness-dont-self-attest](https://github.com/StarDust-zz/witness-dont-self-attest)
  says a store cannot vouch for itself across its own revert: only a record that
  does not go back with the store can, and it must be re-opened at the moment of
  the side effect, not only at certify.

Not a fresh arXiv pack: no new papers. Both parents are copied unchanged under
`parents/` and must still pass 7/7. New code is `terminal_gate.py` + `experiment.py`.

```
python3 experiment.py
```

Stdlib only. No network, no GPU, no live model, no vendor API, no product import.

## Question

The four actions are not the same kind of thing. `continue` and `cliff` only
rewrite the agent's own context. `stop` delivers a verdict and `unsafe` pages a
human: they leave the process. After a crash the agent resumes from a
checkpoint. Before it may emit a terminal action again it has to ask "did this
session already end?". Who may answer that?

## The object

```
internal  = continue | cliff     pure rewrite of own context: replay from any checkpoint
terminal  = stop | unsafe        emits a record into the world (verdict, page)

ended?(session) attested by
  self/snapshot   the decision record inside the checkpoint (restored with it)
  cross/lagging   a copy of the checkpoint replicated on the same cadence, one behind
  self/monotone   a terminal counter kept outside the checkpoint
  witness         the append-only outbox of emitted terminal records; read at resume,
                  re-opened right before emit; a moved head = failed certificate

resume rule (join):  witnessed terminal  >  stop  >  unsafe  >  cliff / continue
  witnessed  -> adopt the recorded terminal, emit nothing
  internal   -> replay (never needs permission)
  terminal   -> re-open the witness, then emit
```

**Claim.** The stop gate's own precedence is only safe within one life. Across
a restore, a checkpoint that carries its own "already stopped" bit re-runs the
evidence loop, delivers a second verdict, and sometimes the opposite one. A
lagging copy of the checkpoint is worse, not better. An outside record of
terminal side effects removes every duplicate without blocking a single
internal replay, but only if it is re-opened right before the emit.

**Falsifier.** If replaying cliff/continue from a checkpoint changed bytes; if
a snapshot-restored or lagging record caught any duplicate; if the outside
record blocked any internal resume; if reading the witness at resume only were
enough with two workers; if a lagging witness ever adopted a terminal that never
happened.

## What this pack tests (7/7)

1. **Parents bind.** stop-triage-cliff and witness-dont-self-attest each run 7/7
   from `parents/`.
2. **Internal replays, terminal repeats.** The parent gate is deterministic for
   continue, cliff and unsafe (byte-identical digest on replay). A late restore
   under self/snapshot gives 2 stop records for one session; an unsafe session
   restored before its page gives 2 pages.
3. **NEW: matrix by attestation source** (290 cases: 40 stop sessions × {none,
   early, mid, late, after} restore, plus 10 each of unsafe / cliff / continue ×
   {none, before, after}):

   | attestation | duplicate verdicts | contradicting verdicts | duplicate pages | internal resumes replayed identically | internal resumes blocked |
   |---|---:|---:|---:|---:|---:|
   | self/snapshot | 120 | 24 | 10 | 40/40 | 0 |
   | cross/lagging | 160 | 24 | 20 | 40/40 | 0 |
   | self/monotone | **0** | **0** | **0** | 40/40 | 0 |
   | witness | **0** | **0** | **0** | 40/40 | 0 |

   The lagging copy adds the "after" cell: the checkpoint already knew the
   session stopped, but the copy one checkpoint behind did not.
4. **Where the duplicates land.** Under self/snapshot every pre-stop restore
   duplicates (40/40 in each of early, mid, late). Contradictions fall with how
   much evidence the checkpoint kept: early 12, mid 10, late 2. Of the 24
   contradictions, 16 flip NoEffect → Beneficial and 8 flip Beneficial →
   NoEffect, so a second life is not a correction, it is a second draw. (In the
   parent stub at b = 0.18, 27/40 first-life verdicts are already false
   Beneficial; that is the parent's setup, not this pack's claim.)
5. **NEW: two workers, re-open at emit.** Two workers resume the same checkpoint
   and both read an empty witness at resume. Read at resume only: 40/40 sessions
   get two verdicts, 5 contradicting. Re-opened right before emit: 0
   duplicates; all 40 second workers see a moved head, are labelled a failed
   certificate, and adopt.
6. **NEW: a witness that lags (never reverts)** — the open hunch of the witness
   parent. Resume one tick after the first stop, early restore. Lag 0 or 1: no
   duplicates. Lag 2 or 3: read at resume only gives 40/40 duplicates; re-open at
   emit gives 0, because the second life takes long enough to reach its own
   stop. Lag 5: re-open at emit still leaves 25/40. A lagging witness never
   adopts a terminal that did not happen (0 false adopts at every lag). Lag only
   costs duplicates, never wrong refusals, and re-opening at emit buys back
   exactly the second-life duration.
7. **Witnessed terminal wins; clean.** A session that escalated, then had its
   budget raised after restore: self/snapshot replays `continue` with the page
   still open (10/10 escalations silently superseded); witness adopts `unsafe`
   (0). A session that delivered a verdict, then had its budget cut after
   restore: self/snapshot pages a human about a finished session (40/40);
   witness adopts `stop` (0). Self-scan of all 33 text files: no product names.

## Synergy

stop-triage-cliff, in plain words: each turn, decide whether to keep going,
compact, stop with an answer, or escalate, and let a principled stop win over
everything else. witness-dont-self-attest, in plain words: a place that rolled
back can't tell you it's up to date; ask something that never rolls back, and
ask again right before you act.

Together: the stop gate's precedence quietly assumes one life. Its two internal
actions are safe to redo from any checkpoint, and its two terminal actions are
not, because they already happened outside. So "stop wins" has to become
"a stop someone outside already saw wins": the check that matters is not in the
gate, it is on the outbox, and it has to be made at emit time. The witness also
fixes the parent's open precedence question (stop vs unsafe in the same turn)
across lives: whichever terminal reached the world first wins, and a fresh
compile can't overwrite it.

## Keepers

See `KEEPERS.txt`.

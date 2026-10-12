# stop-dont-self-attest

Synergy deep-dive joining
[stop-triage-cliff](https://github.com/StarDust-zz/stop-triage-cliff)
(compile each turn into continue | cliff | stop | unsafe, principled stop first)
with [witness-dont-self-attest](https://github.com/StarDust-zz/witness-dont-self-attest)
(a store can't vouch for itself across its own revert; re-open the witness at the side effect).

Keeper: after a crash, continue and cliff replay byte-identically from any
checkpoint, but stop and unsafe repeat. A checkpoint that self-attests "not
stopped" re-delivers in every pre-stop restore (120 duplicate verdicts, 24
contradicting, 10 duplicate pages on 290 cases); a lagging copy of it is worse
(160 / 24 / 20). An outside record of terminal side effects takes all three to
0 and blocks none of the 40 internal resumes, provided it is re-opened right
before the emit (read at resume only, two racing workers double-deliver 40/40).

## Run

```bash
python3 experiment.py                                     # 7/7 join assertions
(cd parents/stop-triage-cliff && python3 experiment.py)   # parent 7/7
(cd parents/witness-dont-self-attest && python3 experiment.py)  # parent 7/7
```

Stdlib only. No network, GPU, or vendor API. MIT.

## Layout

- `terminal_gate.py`, `experiment.py`: new code (attestation sources, outbox witness, resume rule, matrix)
- `parents/stop-triage-cliff/`, `parents/witness-dont-self-attest/`: parent packs, unchanged
- `DESCRIPTION.md`: question, object, claim, falsifier, results, synergy note
- `KEEPERS.txt`: what held, what didn't, what is still a hunch

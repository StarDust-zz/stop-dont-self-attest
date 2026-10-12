# stop-triage-cliff

Synergy deep-dive: **product horizon gate** joining
[stop-cliff-compile](https://github.com/StarDust-zz/stop-cliff-compile)'s
principled stop,
`triage-dont-uniform` / [triage-cliff-compile](https://github.com/StarDust-zz/triage-cliff-compile)'s
type triage, and
[cliff-dont-drift](https://github.com/StarDust-zz/cliff-dont-drift)
into one measurable `continue | cliff | stop | unsafe` action.

Closes the hunch left by triage-cliff-compile: compose type-aware cliff
with stop-cliff-compile's principled stop.

## Run

```bash
python3 experiment.py
```

Expect `7/7 assertions passed`, exit 0.

Stdlib only. No network, GPU, or vendor API in the 7/7 path.

## Layout

| File | Role |
|------|------|
| `experiment.py` | Horizon triage gate + 7 join assertions |
| `stop_stub.py` | Principled stop algebra (from stop-cliff-compile / stop-dont-drift) |
| `triage_stub.py` | TypeCompact / TypeDecompose algebra (from triage-cliff-compile) |
| `cliff_stub.py` | Cliff truncate+signature algebra (from cliff-dont-drift) |
| `DESCRIPTION.md` | Claim, falsifier, object algebra, synergy |
| `KEEPERS.txt` | What is now object vs still hunch |

## License

MIT — see [LICENSE](LICENSE).

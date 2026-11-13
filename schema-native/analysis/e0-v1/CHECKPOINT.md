# E0 checkpoint: incomplete, no inference conclusion

The original 16K E0 stopped for host resource constraints at **588/1,200** saved requests.
612 remain. There are 120 recorded engine failures; the report makes no paired statistical
comparisons for this incomplete run. The 12-request path smoke is separate and not accuracy evidence.
No training was run. E1 and E2 remain gated.

The original configuration is unchanged. The in-flight request was interrupted before a row was
written, so none of the 588 saved request latencies includes the diagnostic pause. Results were not
deleted, repaired or regenerated. Inference code commit: `f78471ec82469c54388500998ae22481c76acf27`.
SHA-256 of uncompressed results: `9a79d62a6e5cf5c813ec2c96c6041d691c6c32ab0530946ef5d58dc38db8ce48`.

`results.jsonl.gz` contains the original model/result records. `manifest.public.json` redacts only
local workspace paths; the original manifest, prompts, server logs and host-resource measurements
are retained in the user's local artifact bundle. `SERVER_RUNTIME.txt` records selected startup and
peak-RSS evidence. The server lifetime includes preflight and smoke, not only benchmark requests.

Recreate the descriptive report without a model (run from `schema-native/`):

```bash
mkdir -p runs/e0-v1
python -c "import gzip,pathlib; pathlib.Path('runs/e0-v1/results.jsonl').write_bytes(gzip.decompress(pathlib.Path('analysis/e0-v1/results.jsonl.gz').read_bytes()))"
cp analysis/e0-v1/manifest.public.json runs/e0-v1/manifest.json
python -m sn.report --run e0-v1 --server-log analysis/e0-v1/SERVER_RUNTIME.txt
```

Do not use that redacted public manifest to resume inference. Use the original local run directory,
its original manifest and its recorded inference commit. On a clean checkout, switch to that commit,
start the original 16K server, repeat its online preflight, then resume the same run ID. Current
source correctly rejects a resume under different input/runtime identity. The new 8K resource
profile needs a **new** run ID; never pool its results with this checkpoint.

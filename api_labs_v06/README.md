# Local AI v0.6 benchmark, VRAM and artifact labs

These scripts are educational clients and validation tools for existing AI APIs.
They do not include a model, a private credential, or any measured RTX 5080 results.
The code uses English identifiers, comments, prompts and messages.

## Offline tests

```bash
python3 -m unittest discover -v
```

## Real API measurement (only after starting a local approved engine)

```bash
python3 bench_v06.py --base-url http://127.0.0.1:8080/v1 --model approved-model-id \
  --warmup 2 --repetitions 10 --output results/metrics.jsonl
python3 summarize_v06.py results/metrics.jsonl
```

Only metadata are written. A missing `usage` structure produces null token metrics.
Remote endpoints require `--allow-remote` and HTTPS, and are not intended for use
with confidential data without a separate security review. API credentials, if
necessary, are read from `LOCALAI_API_KEY`; do not put them in command arguments.

## Estimate ideal KV-cache allocation

```bash
python3 vram_budget_v06.py --layers 32 --kv-heads 8 --head-dim 128 \
  --context 8192 --bytes-per-value 2 --sequences 1
```

The output is algebraic, not observed GPU allocation. See the book for caveats.

## Image generation

`image_generate_v06.py` requires compatible `torch`/`diffusers` packages and a
licensed, locally available model directory. No network model download is
performed by this script. Its generic pipeline and fp16 settings may need
adjustment for the specific selected model architecture. Validate quality,
security, metadata and file ownership before production use.

## Artifact manifest

```bash
python3 artifact_manifest_v06.py /path/to/existing/file.png
```

A SHA-256 digest supports integrity checks, not an authenticity guarantee.

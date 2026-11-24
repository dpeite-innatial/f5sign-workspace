# Bench: form engine (pyHanko) — TASK-074 before/after

Scripts behind TASK-074 §1 (f5sign-backend), kept here for its AC-6 re-measurement. Not in the backend repo.

Copy them into the php-fpm container (`docker cp <file> f5sign-php-fpm:/tmp/bench/`) and run them there. From a
worktree, mount the worktree instead of the main checkout (or use its lane container), or the bench measures
`develop`'s code.

- `genpdf.py out.pdf pages bytes_per_page` — synthetic PDF, one random grayscale image per page (incompressible).
  Sizes used on 2026-10-27: s10 = `20 500000`, s25 = `50 500000`, s33 = `70 500000`, s50 = `100 500000`.
- `proc.php file.pdf` — the same `inspect` fed as Process(string), Process(stream), proc_open(file).
  Speaks the protocol from before TASK-074 (JSON + base64): it measures the "before" only.
- `apply.php file.pdf` — `apply` string vs stream (old protocol), then the real adapter's `inspect` at the 20 s timeout.
- `pipeline.php file.pdf` — DocumentSigner's byte path (read+digest, inspect, apply, one seal, digest) through the
  real adapter, with PHP peak memory. The 512M run:
  ```
  docker run --rm --memory=512m --memory-swap=512m --network f5sign-net \
    -v <backend checkout or worktree>:/var/www/html:ro \
    -v <infra>/docker/php/php.ini:/usr/local/etc/php/conf.d/99-f5sign.ini:ro \
    -v $PWD:/bench -w /bench --entrypoint sh f5sign/backend:dev \
    -c "php pipeline.php pdfs/s50.pdf; cat /sys/fs/cgroup/memory.peak; grep oom_kill /sys/fs/cgroup/memory.events"
  ```
  It needs `eu-dss` on `f5sign-net` (shared with other sessions: say so before loading it).
- Engine alone, RSS and wall: inside the container,
  `/usr/bin/time -v /opt/pyhanko/bin/python -I /var/www/html/assets/signature-execution/form_engine.py apply --memory-limit-bytes 805306368 < request`.

Numbers measured 2026-10-27 (before): see TASK-074 §1.

Lost with a cleared scratchpad on 2026-10-28 and not recreated: `fe_bin.py` (the binary-framing copy of
form_engine.py; TASK-074's implementation replaces it), `dss.php` (per-call DSS timings), `e2e.sh`/`run.sh`/
`worker_timeline.py` (one real signing act through the dev stack, worker timeline from its log) and
`prep.sh`/`load.sh` (the load test with N envelopes committed at once).

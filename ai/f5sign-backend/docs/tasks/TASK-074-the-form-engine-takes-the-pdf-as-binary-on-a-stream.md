# TASK-074 — The form engine takes the PDF as binary, on a stream

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `fix/form-engine-binary-framing`** (code at `e1d4b1e5`), 2026-10-28 — suite green under the `wt-backend` lane of this worktree (9672 tests, tree `b2064771`; after it only docs and slice 06's one test, whose class ran green on the same lane), PHPStan, deptrac and lint clean. Pending review. Infection on the diff's `src/` file: covered MSI 90 %, MSI 88 % at `e1d4b1e5`, the survivors ruled in §7. AC-9's verification differs from the row (§7). The header-cap follow-up is in §6 and BL-489. |
| **Type** | **Corrective**, in one adapter and its script: a large document cannot be signed today (the form engine times out, or the worker is OOM-killed), and the cause is how the PDF travels to the engine, not the engine. |
| **Why** | The PDF reaches `form_engine.py` base64-encoded inside one JSON object, handed to Symfony `Process` as a string. Writing a large string to a child's stdin through `Process` is slow out of proportion to its size, and the base64/JSON wrapping keeps five or six copies of the document alive in the child and two or three in PHP. Measured on 2026-10-27 (§1): a 48 MB PDF fails with `TIMED_OUT` at the configured 20 s, and in a container capped at the production worker's 512M it is killed by the kernel (`KILLED`, exit 137) before DSS is reached. |
| **Builds on** | [ADR-0085](../adr/ADR-0085-recorded-values-are-form-fields-each-signature-locks.md) §2.4–§2.6 (the engine as a sealed-off process, PHP decides, the failure split), all unchanged; [TASK-067](TASK-067-recorded-field-values-are-drawn-into-the-signed-pdf.md), which built the adapter and the script. |
| **Scope** | The wire format between `PyHankoFormEngine` and `form_engine.py`, and how the adapter feeds `Process`. ⛔ **Not** the port (`PdfFormEngineInterface`), not the configuration (timeout, address-space limit), not DSS's base64 (its REST API requires it), not merging `inspect` and `apply`, not the seal's empty `apply`, not [BL-456](../BACKLOG.md), not infra (§6). |
| **Decision record** | [ADR-0085](../adr/ADR-0085-recorded-values-are-form-fields-each-signature-locks.md), **Accepted** — exercised, not changed. Its §2.4 fixes stdin in, stdout out, an empty environment, a timeout, an address-space limit and a version check; it fixes no wire format (no JSON, no base64, no field names), which lives only in the script's module docstring. No ADR yet; one would be forced if the change needed a file, an argument or a second channel to carry the PDF, which §2.4 excludes. |

<!-- OFFREPO: the measurements in §1 were taken on 2026-10-27 on the dev stack (WSL2, Docker Desktop) with
scratch scripts that are not in this repository: a PDF generator (N pages, each with a random grayscale
image, so the bytes do not compress), a script that drives `PyHankoFormEngine` and `DssHttpAdapter` through
the byte path of `DocumentSigner` (custody read and digest, `inspect`, `apply`, one seal, digest), and a
copy of `form_engine.py` with the binary framing of §3. Every number this record relies on is restated in
§1; the method to measure again is restated in §5 AC-6, and nothing here depends on the scripts. -->

---

## 1. Why this task exists

Measured on 2026-10-27, synthetic PDFs of 1, 10, 24, 33 and 48 MB:

**Time spent feeding the child, not in the engine.** The same `inspect`, fed three ways:

| Request size | `Process`, string input (today) | `Process`, stream input | engine alone, from a shell |
|---|---|---|---|
| 1.3 MB | 0.33 s | 0.31 s | 0.32 s |
| 12.9 MB | 1.3 s | 0.4 s | 0.4 s |
| 32.3 MB | 5.8 s | 0.56 s | 0.7 s |
| 33 MB PDF, `apply` | 11.2 s | 1.16 s | — |
| 48 MB PDF, `apply` | 23.7 s | 2.1 s | 1.4 s |

The real adapter, at the configured 20 s timeout, answers `TIMED_OUT` for the 48 MB PDF; at 33 MB it takes 11 s.

**Memory.** The byte path of one signing act, in a container capped at 512M (the production worker's cap):

| PDF | PHP peak | container peak | outcome |
|---|---|---|---|
| 10 MB | 68 MB | 173 MB | ok |
| 24 MB | 160 MB | 349 MB | ok |
| 33 MB | 221 MB | 478 MB | ok |
| 48 MB | — | 512 MB | `oom_kill`: the engine is killed, `FormEngineFailedException(KILLED)` |

The engine alone, at 48 MB: `inspect` 223 MB RSS, `apply` 403 MB RSS. The same engine reading the PDF as raw
bytes after a one-line JSON header, and writing the drawn PDF the same way: `inspect` 144 MB, `apply` 148 MB
(at 24 MB: `apply` 228 → 100 MB). The difference is the transport: the script holds the JSON text, the
base64 string kept alive in `request` for the whole of `apply`, the decoded bytes, and on the way out the
base64 bytes, their ASCII string and the JSON text.

The real worker (dev stack, one consumer) needs 423 MB for a 25 MB document's whole envelope, from 107 MB
idle, so the production threshold is below the 33 MB above.

## 2. What already exists (reuse, do not rebuild)

- **The port**, `F5Sign\SignatureExecution\Domain\Pdf\PdfFormEngineInterface`: `inspect(string $pdf): FormState`
  and `apply(string $pdf, FormRevision $revision): DrawnRevision`, both on raw bytes. `DrawnRevision::$pdf` is
  raw bytes. Its callers (`DocumentSigner`, `FormRevisionPlanner`, `DrawnRevisionCheck`) and its fake
  (`FakePdfFormEngine`) never see the wire format, and none changes.
- **The adapter**, `F5Sign\SignatureExecution\Infrastructure\Pdf\PyHankoFormEngine`. `inspect()` and `apply()`
  build `['pdf' => base64_encode($pdf), …]`; `run()` `json_encode`s it (failure → `REQUEST_INVALID`, nothing
  started), passes it to `new Process($command, null, self::emptyEnvironment(), $input, $this->timeoutSeconds)`
  as a **string**, maps `ProcessTimedOutException` → `TIMED_OUT`, `ProcessSignaledException` → `KILLED`
  (128 + signal), `ProcessRuntimeException` → `UNAVAILABLE`, exit 127/126 → `UNAVAILABLE`, any other non-zero
  exit → `FormEngineFailure::ofExitCode()`, output that is not JSON or has no string `engine` →
  `MALFORMED_OUTPUT`, an `engine` other than the pinned version → `VERSION_MISMATCH`. `apply()` decodes the
  response's `pdf` strictly; empty or invalid → `MALFORMED_OUTPUT`. stderr is never read.
- **The command**, `PyHankoCommand`: argv `[python, -I, script, inspect|apply, --memory-limit-bytes, N]`; no
  value on the command line.
- **The failure enum**, `FormEngineFailure`: `ofExitCode()` maps 2 → `REQUEST_INVALID`, 3 → `PDF_UNREADABLE`,
  4 → `MEMORY_LIMIT`, 5 → `CANNOT_APPLY`, anything else → `FAILED`.
- **The script**, `assets/signature-execution/form_engine.py`. Its module docstring is the only place the
  wire format is written down: *"The request is one JSON object on standard input and the response one JSON
  object on standard output."* `read_request()` does `json.loads(sys.stdin.buffer.read())`, requires a dict
  with a string `pdf`, `base64.b64decode(…, validate=True)`, refuses an empty PDF (exit 2). `main()` sets
  `RLIMIT_AS` first, imports pyHanko, reads the request, and writes `json.dumps({'engine': …, **response})` with
  `sys.stdout.write`. `apply()` returns `{'pdf': base64…, 'summary': {…}}`. stderr is `/dev/null` (BL-278).
- **The configuration**, `config/packages/signature_execution.yaml`: `form_engine_timeout_seconds: 20`,
  `form_engine_memory_limit_bytes: 805306368` (768 MiB), wired into `PyHankoFormEngine` in `config/services.yaml`.
- **The tests that pin the wire today:**
  - `tests/F5Sign/SignatureExecution/Integration/Infrastructure/Pdf/PyHankoFormEngineTest.php`:
    `the_child_gets_an_empty_environment_and_the_pdf_only_on_stdin`, `the_revision_travels_as_the_protocol_request`
    (asserts the JSON body with a base64 `pdf`), `a_value_that_is_not_utf8_is_an_invalid_request`,
    `each_exit_status_names_its_failure`, `the_engine_error_text_never_reaches_the_exception`,
    `a_different_engine_version_is_refused`, `a_slow_engine_times_out`, `a_killed_engine_is_reported_as_killed`,
    `exit_4_is_the_memory_limit`, `a_missing_engine_is_unavailable`, `an_engine_that_cannot_be_started_is_unavailable`,
    and the malformed-output providers for `inspect` and `apply`.
  - `tests/F5Sign/SignatureExecution/Integration/Infrastructure/Pdf/PyHankoFormScriptTest.php` runs the real
    script on the real `/opt/pyhanko`, including `a_tiny_memory_limit_fails_as_memory_limit` and
    `the_output_begins_with_the_input_and_adds_one_revision`.
  - `tests/F5Sign/SignatureExecution/Unit/Infrastructure/Pdf/PyHankoCommandTest.php` (`the_command_carries_no_value`).
  - `tests/F5Sign/SignatureExecution/Unit/Infrastructure/Pdf/FormEngineSensitiveParametersTest.php`: the
    hand-listed census of `#[SensitiveParameter]` on the adapter, the planner and the signer ([BL-454](../BACKLOG.md)).
  - **13 shell stand-ins** in `tests/Fixtures/pyhanko-fakes/` run in place of the interpreter. Two of them parse
    the current wire: `answers-with-the-pdf` extracts and `base64 -d`s the request's `pdf`; `echoes-request`
    returns the request base64-encoded. The others answer fixed JSON (`apply-ok`, `inspect-ok`, `garbled`,
    `wrong-version`, `odd-rotation`, `short-box`) or act on the process (`exit-4`, `killed`, `slow`,
    `leaks-on-stderr`, `prints-args-and-env`).
- **`tests/Fixtures/pdf-form-reader.py`**, the test-side reader, takes the PDF raw on stdin already; it is not
  the engine and does not change.
- **The check after `apply`**, `DrawnRevisionCheck`: the output must begin with the input bytes exactly
  (ADR-0085 §2.5). Any byte the framing alters fails the act.
- **Open rows:** [BL-455](../BACKLOG.md) recorded (history: its clause, removed by this task), among other limits, that *"PHP holds the PDF three times
  (raw, base64, JSON)"*; this task removes that clause and leaves the rest (no `RLIMIT_CPU`, `RLIMIT_NPROC`,
  `RLIMIT_NOFILE`; no stated maximum PDF size). [BL-456](../BACKLOG.md) (a hostile PDF whose `/Kids` DAG
  expands without bound fails the act on every retry) is untouched.

## 3. Scope

1. **The request**: one line of JSON, a UTF-8 object without the PDF and with `pdf_length` (the byte count of
   what follows), terminated by `\n`, then exactly `pdf_length` raw bytes of PDF. `inspect` sends `{}` plus
   `pdf_length`; `apply` sends `create`, `fill`, `signatureFields` plus `pdf_length`.
2. **The response**: one line of JSON (`engine`, the operation's fields, `pdf_length`), terminated by `\n`, then
   exactly `pdf_length` raw bytes: the drawn PDF for `apply`, none (`pdf_length: 0`) for `inspect`. Written with
   `sys.stdout.buffer`, so no byte is translated.
3. **Both sides check the length**: the script refuses a body shorter or longer than `pdf_length` (exit 2); the
   adapter refuses a body shorter or longer than the response's `pdf_length` (`MALFORMED_OUTPUT`).
4. **The adapter feeds `Process` a stream** (header and bytes, e.g. through `php://temp`), never one string,
   and splits the response at its first `\n` without copying the body more than once.
5. **Unchanged**: the port and its callers, `PyHankoCommand`'s argv, the empty environment, stderr to
   `/dev/null`, the exit codes and their mapping, the version check, `DrawnRevisionCheck`, the configuration.
6. **Tests and fixtures**: the stand-ins in `tests/Fixtures/pyhanko-fakes/` speak the new framing;
   `the_revision_travels_as_the_protocol_request` asserts the new request; §5's new cases are added.
7. **Prose**: the script's module docstring; `PyHankoFormEngine`'s docblocks; the [BL-455](../BACKLOG.md) row.

Concepts re-cut: `one JSON object on standard input`, `base64` in `PyHankoFormEngine` and `form_engine.py`,
`'pdf' =>` in the adapter's requests, `request['pdf']`, `b64decode`/`b64encode` in the script, the
`pyhanko-fakes` that `base64 -d` or `base64 -w0`. DSS's base64 (`DssHttpAdapter`, `SignRequest::$pdfBase64`)
is **not** in the sweep: it stays.

## 4. Key decisions

- **Binary after a JSON header, not a second channel.** ADR-0085 §2.4 allows stdin and stdout and nothing else
  (no file, no argument, no extra descriptor), so the PDF stays on the same pipe, framed by a length the header
  declares. A delimiter would need escaping; a length does not.
- **The length is declared and checked on both sides.** A truncated pipe (a killed writer, a short read) must
  never reach pyHanko's lenient reader, which would accept a cut PDF, nor reach `DrawnRevisionCheck` as a
  mismatch that hides a transport fault.
- **Measured before chosen.** §1's stream-versus-string and binary-versus-base64 numbers are measured, not
  estimated; AC-6 measures again after.

## 5. Verification

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | The request on stdin is one JSON line without the PDF, carrying `pdf_length`, followed by the raw PDF bytes; no base64 of the PDF travels | owner | Integration (stand-in echoing stdin) | send the PDF base64-encoded again |
| AC-2 | The response on stdout is one JSON line (`engine`, the result, `pdf_length`) followed by the raw drawn bytes for `apply`, and by nothing (`pdf_length` 0) for `inspect` | owner | Integration, real engine | write the drawn PDF base64-encoded again |
| AC-3 | A truncated or overlong body is refused on both sides (members AC-3a…d) | owner | Integration (real script; stand-ins) | see *Notes on AC-3* |
| AC-4 | `PdfFormEngineInterface` does not change: no file under `src/F5Sign/SignatureExecution/Domain/Pdf/` is in the branch's diff | owner | diff against `develop` | — |
| AC-5 | A ~32 MB PDF passes `inspect` and `apply` through `PyHankoFormEngine` with the real engine, each under a 3 s timeout | owner | Integration, real engine, lane | pass `Process` the input as one string again |
| AC-6 | Before and after are measured by one method, and the numbers are written into this record | owner | manual, on the lane image | — |
| AC-7 | The script refuses every malformed request header with exit 2 (members AC-7a…e) | derived — assets/signature-execution/form_engine.py (census of `read_request`'s refusals) | Integration, real script | see *Notes on AC-7* |
| AC-8 | The adapter refuses every malformed response (members AC-8a…e) | derived — src/F5Sign/SignatureExecution/Infrastructure/Pdf/PyHankoFormEngine.php (census of `run()`'s refusals) | Integration, stand-ins | see *Notes on AC-8* |
| AC-9 | A PDF whose bytes begin with `\n` and contain `\r\n` and `\0` comes back byte-exact: the drawn output begins with the input | derived — docs/adr/ADR-0085-recorded-values-are-form-fields-each-signature-locks.md §2.5 | Integration, real engine | split the request at the last `\n` instead of the first |
| AC-10 | A ~32 MB `apply` succeeds under an address-space limit at which the base64 framing fails with `MEMORY_LIMIT` | derived — docs/BACKLOG.md (BL-455), §1's measurements | Integration, real script | restore the base64 framing in the script |
| AC-11 | What ADR-0085 §5 says the adapter enforces keeps holding with the stand-ins on the new framing (members AC-11a…i) | derived — docs/adr/ADR-0085-recorded-values-are-form-fields-each-signature-locks.md §5 | Unit + Integration | see *Notes on AC-11* |
| AC-12 | The parameters that carry the PDF or the request header into the child carry `#[SensitiveParameter]`, and the census in `FormEngineSensitiveParametersTest` lists them (members AC-12a…b) | derived — tests/F5Sign/SignatureExecution/Unit/Infrastructure/Pdf/FormEngineSensitiveParametersTest.php (BL-454) | Unit | drop the attribute from the new parameter |
| AC-13 | No prose describes the old framing: the script's docstring states the new one, an `rg` sweep of §3's re-cut terms over `src tests docs assets config` finds no claim of the old, and the BL-455 row loses its "three times" clause in the same changeset | derived — authoring rule 1, authoring rule 7 | sweep, at the last commit | — |
| AC-14 | The configuration is unchanged: `form_engine_timeout_seconds` 20 and `form_engine_memory_limit_bytes` 805306368 | derived — config/packages/signature_execution.yaml (tuning is out of scope) | diff against `develop` | — |

<!-- OFFREPO: `wt-backend` is a target of the `f5sign-infra` Makefile: it runs this worktree's suite on its own
stack (postgres, minio, rabbitmq, mailpit) from the backend image, which carries `/opt/pyhanko`. -->
- **Gates:** suite, PHPStan, deptrac and lint under the lane that mounts this tree (`wt-backend`); Infection
  filtered to the touched `src/` files. AC-5, AC-9 and AC-10 need the real `/opt/pyhanko`, which the lane image
  carries.

**Notes on AC-1**
- Owner said: "one JSON header line (request without the pdf, with pdf_length) followed by raw PDF bytes on stdin".

**Notes on AC-2**
- Owner said: "same shape on stdout (engine + summary + pdf_length, then the drawn bytes)".

**Notes on AC-3**
- Owner said: "both sides verify the length and refuse truncation"; "truncated input/output refused".
- AC-3a — a request whose body is shorter than `pdf_length` exits 2 (`REQUEST_INVALID`). Sabotage: drop the script's length check.
- AC-3b — a request whose body is longer than `pdf_length` exits 2. Sabotage: read only `pdf_length` bytes and ignore the rest.
- AC-3c — a response whose body is shorter than its `pdf_length` is `MALFORMED_OUTPUT`. Sabotage: drop the adapter's length check.
- AC-3d — a response whose body is longer than its `pdf_length` is `MALFORMED_OUTPUT`. Sabotage: take the first `pdf_length` bytes and ignore the rest.

**Notes on AC-4**
- Owner said: "PdfFormEngineInterface does not change".

**Notes on AC-5**
- Owner said: "a regression test with a ~32MB PDF passing inspect+apply under a short timeout, sabotage-checked by reverting to string input".
- The PDF is built in the test with incompressible content (random image data), so its size is its byte count.
  Measured: string input needs 5.8 s for a 32 MB request's `inspect` alone; stream input 0.56 s, and 1.16 s for a
  33 MB PDF's `apply` (§1). 3 s per operation leaves about a factor of two on each side, so the sabotage trips on a faster
  host too; "a short timeout" is restated as that number to make it testable.

**Notes on AC-6**
- Owner said: "before/after measured with the same bench".
- Method: synthetic PDFs of 10, 24 and 48 MB (N pages, a random grayscale image each). For each, time and peak
  RSS of `inspect` and `apply` (engine alone), and the byte path of one signing act (custody read and digest,
  `inspect`, `apply`, one seal, digest) in a container capped at 512M, recording PHP peak, container peak and
  `oom_kill`. "Before" is §1.
- After (measured 2026-10-28, `f5sign/backend:dev` image, this branch's code at `da0fd720`, the same PDFs:
  `genpdf.py` with 20, 50 and 100 pages of 500000 bytes, 10012577, 25031107 and 50062111 bytes,
  labelled 10, 24 and 48 MB as in §1; every MB in this note is 2^20 bytes). Engine alone, three runs each under
  `/usr/bin/time -v` with the configured 805306368 limit; each cell is the median of the three (wall time,
  maximum resident set size), and the three never differed by more than 0.06 s or 1 MB:

  | PDF | `inspect` | `apply` |
  |---|---|---|
  | 10 MB | 0.42 s / 58 MB | 0.43 s / 72 MB |
  | 24 MB | 0.35 s / 73 MB | 0.44 s / 101 MB |
  | 48 MB | 0.39 s / 97 MB | 0.46 s / 149 MB |

  Before, at 48 MB: `inspect` 223 MB, `apply` 403 MB and 1.4 s (§1).

  The byte path of one signing act through the real adapter and the real DSS, one run each, in a container
  capped at 512M (`--memory=512m --memory-swap=512m`, the infra `php.ini`):

  | PDF | PHP peak | container peak | outcome | `inspect` / `apply` / seal |
  |---|---|---|---|---|
  | 10 MB | 55 MB | 126 MB | ok | 0.47 / 0.47 / 1.41 s |
  | 24 MB | 127 MB | 209 MB | ok | 0.44 / 0.56 / 1.20 s |
  | 48 MB | 246 MB | 389 MB | ok, `oom_kill` 0 | 0.47 / 0.77 / 2.08 s |

  Before (§1): 173 and 349 MB container peak at 10 and 24 MB, and the 48 MB act killed at 512 MB. Which phase sets
  the 246 MB PHP peak was not measured; §6's worker budget follows from it either way.

**Notes on AC-7**
- AC-7a — a first line that is not JSON. AC-7b — JSON that is not an object. AC-7c — `pdf_length` absent or not
  an integer. AC-7d — `pdf_length` negative. AC-7e — `pdf_length` 0 (an empty PDF, refused today).
  Sabotage, each: remove that branch of the header check.

**Notes on AC-8**
- AC-8a — no `\n` in the output → `MALFORMED_OUTPUT`. AC-8b — a first line that is not JSON → `MALFORMED_OUTPUT`.
  AC-8c — no string `engine` → `MALFORMED_OUTPUT`. AC-8d — `pdf_length` absent, not an integer or negative →
  `MALFORMED_OUTPUT`. AC-8e — an `engine` other than the pinned version → `VERSION_MISMATCH`.
  Sabotage, each: remove that branch of the response check.

**Notes on AC-10**
- The limit is found by measurement while implementing (the base64 framing at 48 MB needed 403 MB RSS for
  `apply`, the binary framing 148 MB) and written here with the value chosen. `RLIMIT_AS` bounds the address
  space, not the resident set, so the value is measured, not derived from the RSS figures.
- Measured on 2026-10-28 on the lane image: the 32 MiB `apply` fails with `MEMORY_LIMIT` at 128 MiB and
  passes at 136 MiB with the binary framing, and fails at 312 MiB and passes at 320 MiB with the base64
  framing; the test uses 224 MiB. Each bracket comes from a sweep of 32 MiB steps refined to 8 MiB steps; the
  8 MiB refinement was run twice, with the same result. 224 MiB is the midpoint of the two passing limits,
  228 MiB, rounded to 16 MiB.

**Notes on AC-11**
- AC-11a — argv carries no value (`PyHankoCommandTest::the_command_carries_no_value`).
- AC-11b — the child gets an empty environment and the PDF only on stdin.
- AC-11c — the engine's stderr never reaches the exception.
- AC-11d — each exit status names its failure (2, 3, 4, 5, other).
- AC-11e — a different engine version is refused.
- AC-11f — a slow engine times out (`TIMED_OUT`).
- AC-11g — a killed engine is reported as `KILLED`.
- AC-11h — a missing engine is `UNAVAILABLE` (127).
- AC-11i — an engine that cannot be started is `UNAVAILABLE`.
- These are today's tests in `PyHankoFormEngineTest` and `PyHankoCommandTest`; each gains the `@criterion` line.
  Sabotage, each: the guard the existing test already names.

**Notes on AC-12**
- AC-12a — the parameter that carries the request header (today `PyHankoFormEngine::run`'s `$request`, already in the census).
- AC-12b — the parameter that carries the PDF bytes to the method that writes the child's stdin, whatever its name.
- Sabotage, each: drop the attribute and watch the census fail naming it.

## 6. Open follow-ups (track, don't solve here)

<!-- OFFREPO: `f5sign-infra` is the sibling repository that orchestrates production; facts restated here:
the production worker container is capped at 512M and its consumer runs with `--memory-limit=256M`. The
PHP limits are this repo's own `docker/php.ini` (`memory_limit=512M`, 50 MB upload and post), which the
production image carries. -->
- **The worker's memory budget and the maximum upload** (infra, `f5sign-infra`). Even with this task, a 48 MB
  PDF keeps PHP near 250 MB (246 MB measured, Notes on AC-6; the phase that sets it was not measured), plus
  ~150 MB in the engine, against a 512M cap.
  Either the worker's cap goes up, or the 50 MB upload limit comes down to what the worker can sign; the
  `memory_limit` of the worker's PHP should sit below the container's cap so a fatal is a PHP error rather than
  a kernel kill. Already indexed as the "state the maximum PDF size" half of [BL-455](../BACKLOG.md).
- **Merge `inspect` and `apply` into one process per act.** Saves one Python start (~0.3 s) and one parse of the
  PDF per act, not memory (the two run in sequence, so the peak is `apply`'s). Needs a two-phase exchange on one
  pipe, because PHP plans between them (ADR-0085 §2.5).
- **The seal's `apply` when it has nothing to draw.** Under `SEQUENTIAL_PADES`, when the last actor was a SIGNER,
  the seal's revision creates nothing, fills nothing and locks nothing; DSS could sign without `fieldId`, as
  `DssPdfSealer` does. ADR-0085 §2.2 says every signature goes into a field this system creates, and
  `DocumentSignerTest::the_seal_draws_too` pins it, so skipping it is an amendment to that ADR.
- **A cap on the response header line** (opened 2026-10-28, security audit; [BL-489](../BACKLOG.md)). `PyHankoFormEngine::run` looks for the first `\n` of the child's output as chunks arrive, with no limit on the header's length, and rescans the growing head on every chunk. Bounded today by the 20 s timeout, the child's `RLIMIT_AS`, PHP's `memory_limit`, and a header written by our own sealed script; a cap is a new limit this record does not set, so it sits beside BL-455's.
- **Consumers and DSS capacity.** One consumer handled 18 envelopes/min of 1 MB, three 41, six 66, with DSS
  peaking at six cores (dev stack, 2026-10-27). Scaling consumers multiplies the per-act memory above.

---

## 7. Deviations & honest notes

### Scope
- None. The diff is `form_engine.py`, `PyHankoFormEngine.php`, the `PyHanko*` tests, 8 stand-ins in `tests/Fixtures/pyhanko-fakes/`, the BL-455 row, ADR-0085 §5 and this record. The claims check had said 2 stand-ins parse the wire; 8 change (every one that writes a response adds `pdf_length` and the newline; `prints-args-and-env` reads stdin).

### Decisions made during implementation
- AC-5 and AC-10 build the PDF with `MinimalPdf::withContentOf()` (uncompressed blank content) rather than random image data: nothing on the path compresses, so size equals byte count.
- The `pdf_length` type/negative check in `PyHankoFormEngine::run` is an equivalent mutant (the strict `strlen($body) !== $length` comparison refuses the same four AC-8d values); kept as a listed refusal and expected to escape in Infection.
- The "no PDF" adapter case was dropped: framed, it is byte-identical to "an empty PDF".
- `a_tiny_memory_limit_fails_as_memory_limit` still fails at 64 MiB with 8 MiB under the new framing; not re-tuned, and gains a companion assertion that a few-KB PDF passes at the same limit.
- The refusal rows (AC-3a/b, AC-7) cannot go red against the pre-change script, which failed `json.loads` on any frame; the per-guard sabotage is their failing evidence.
- **AC-9's verification changed.** The real engine refuses a PDF whose first byte is `\n` (`PDF_UNREADABLE`, exit 3), so the row's "begins with `\n`" cannot run end to end. The real-engine test keeps CR, LF and NUL after byte 0; the leading-`\n` case is pinned on the adapter's response split (stand-in test) and on the script's request read in `PyHankoFormProtocolTest`. The row's sabotage (split the request at the last `\n`) was not run on the real engine; the swapped response-side `strrpos` sabotage was. The real-engine test is a characterisation test (green on the base64 framing too).
- AC-10 measured 2026-10-28 on the lane: the binary framing's limit lies between 128 and 136 MiB, the base64 framing's between 312 and 320 MiB; the test uses 224 MiB (Notes on AC-10).
- §2 quotes BL-455's old "three times" clause as history; the row itself no longer says it.
- The record's AC-6 after-numbers and §6 were corrected after the closing review (`bae7002a`): §6 had named an unmeasured cause for the PHP peak.
- Closing review, unfixed low-confidence: §3's "e.g. `php://temp`" against the adapter's `php://memory` (an example; decided at plan); the `fopen`-false branch of `PyHankoFormEngine::stdin()` is untested (watch Infection).

### Decisions that needed an ADR
- None. ADR-0085 is exercised, not changed in status: only its §5 "Enforced by" pointers gained the two new test classes. Its status stays as it is.

### Declared and unproven properties
- AC-6 (before/after measurement, manual, on the lane image) and AC-13 (sweep) are not test-citable by design. AC-4 and AC-14 are diff checks.
- The request-direction leading-`\n` against the *real* engine cannot be shown (exit 3 precedes), see AC-9 above.

### Debt left behind, and where it lives now
- Security audit (warn, low, not fixed): (1) no cap on the response header before its first `\n`, with a rescan per chunk → §6 and [BL-489](../BACKLOG.md). (2) the collect closure's `$chunk` lacks `#[SensitiveParameter]`; it has no throw path, so nothing to leak. (3) the PDF is held twice in PHP (string plus `php://memory`): documented, owner-approved at plan.
- Worker memory budget and maximum upload, merge of `inspect`/`apply`, the seal's empty `apply`, consumers and DSS capacity: §6 (unchanged by this task; the first is also BL-455's "state the maximum PDF size").

### Delegated work
- 01 (critical, opus, 1 round, approved; concerns: equivalent `pdf_length` type check, a docblock timing clause from the record): replicator for 3 stand-ins.
- 02 (critical, opus, 1 round, approved), 03 (critical, opus, 1 round, approved; AC-9 fallback), 05 (critical, opus, 1 round, approved): no delegation.
- 04 (standard, the orchestrator, approved): the AC-6 measurements; a Docker daemon outage during the bench, restarted by the owner.

### Cost of the run
- Slice tokens (implementer, opus): 01 271,010; 02 95,227; 03 125,022; 05 118,139; slice 04 by the orchestrator. Slice 06 (Infection fix, sonnet) 84,416. Total about 694,000 slice tokens, 5 slices, 1 review round each, 0 escalations.
- Closing review: 1 finding, fixed by the orchestrator in docs only (`bae7002a`).
- Full suite: 9672 tests, 106508 assertions, green (baseline 8013 tests at `84e69fe9` on the `fast=1` lane). Security audit: 0 blocking, 3 warnings.
- Infection, filtered to the diff's one `src/` file (`PyHankoFormEngine.php`; `form_engine.py` is Python and
  outside its reach), on the `wt-backend` lane. First run at `bae7002a`: covered MSI 84.91 %, under the 85 bar,
  with three escaped mutants in the closure that gathers stdout (stderr chunks not dropped, `$body` and `$head`
  overwritten instead of appended): no test fed it stderr or a response in pieces. Slice 06 (`e1d4b1e5`) added
  the `answers-in-pieces` stand-in and `a_response_that_arrives_in_pieces_beside_stderr_is_read_whole`; each of
  the three sabotaged alone turns it red. Second run at `e1d4b1e5`: **MSI 88 %, covered MSI 90 %** (54 mutants,
  48 killed). Left on the changed lines, each ruled rather than tested:
  - `run()`, the `pdf_length` type and sign check (`LogicalOr`, `Throw_`): equivalent. The strict comparison of
    the body's length with `pdf_length` refuses the same absent, string, fractional and negative values.
  - `run()`, `$process->disableOutput()` removed (`MethodCallRemoval`): no result changes. It only stops
    `Process` keeping its own copy of stdout, in a `php://temp` buffer that spills to disk past 1 MiB, which is
    the class docblock's reason for it; a test cannot see a buffer the adapter never reads.
  - `run()`, the `finally` that closes the stdin stream removed (`Finally_`): the stream is a `php://memory`
    handle local to the call, freed when the call returns either way.
  - `stdin()`, `fopen('php://memory')` failing (`Throw_`, not covered): not reachable from a test.

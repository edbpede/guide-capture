# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Guide Capture drives a disposable Android emulator to produce redacted, annotated screenshots for
documentation. It is a three-file tool (Bash + Python + Node) with no package manifest, no build
step, and no dependency install — everything comes from Homebrew.

## Essential Commands

Run all of these from the repository root.

```bash
python3 -m unittest discover -s tests -v            # full test suite (22 tests)
python3 -m unittest tests.test_guide_capture.AnnotationPipelineTests.test_pipeline_refuses_to_overwrite_reviewed_output -v
python3 -m unittest discover -s tests -k test_public_text -v   # filtered by substring
shellcheck bin/guide-capture bin/check-sensitive-files
node --check lib/web_tap.mjs                         # syntax only; the wrapper uses /opt/homebrew/bin/node
prek run --all-files                                 # everything the commit hooks run
bin/guide-capture doctor                             # tool/version/permission preflight; no emulator needed
```

`prek install --hook-type pre-commit --hook-type commit-msg` wires the hooks defined in
`prek.toml`: builtin file checks, Gitleaks, `bin/check-sensitive-files`, shellcheck, the Python
tests, and `node --check`. Commit messages must be Conventional Commits — the `commit-msg` hook
rejects anything else.

The annotation tests shell out to `/opt/homebrew/bin/magick` directly, so ImageMagick must be
installed at the Homebrew prefix for the suite to pass.

## Architecture Overview

Three layers, with a deliberate split of responsibility:

- **`bin/guide-capture`** — the only entry point. Owns every side effect: emulator lifecycle, ADB,
  `age`/`zstd` decryption, run state, file permissions. One verb per action so each result can be
  verified before the next runs.
- **`lib/guide_capture.py`** — argparse subcommands (`normalize`, `match`, `open-target`,
  `annotate`, `rewrite-avd`, `ishoj-input-script`, `os2faktor-pin-script`, …) called by the wrapper.
  All parsing, schema validation, and the ImageMagick pipeline live here. This is the layer under
  unit test.
- **`lib/web_tap.mjs`** — Chrome DevTools Protocol click for pages where UIAutomator only exposes a
  WebView. Hard-coded HTTPS host allowlist (`aula.dk`, `www.aula.dk`, `broker.unilogin.dk`,
  `login-idp.ishoj.dk`); aborts on zero or multiple visible matches.

**Output contract.** Every wrapper command prints exactly one JSON object on stdout and all human
prose on stderr via `human()`. Exit codes carry meaning and callers depend on them: `64` bad
arguments or spec, `65` invalid data/state, `66` missing input, `69` unavailable or verification
failed, `73` refusing to overwrite. Selector matching uses `0` = exactly one match, `2` = none,
`3` = ambiguous. Preserve both the JSON shape and the exit code when editing a command.

**Run state.** `private/runtime/current-run.json` (`schema_version: 1`) is the single active-run
lock. `boot` refuses to start when it exists; `kill` removes it and destroys the plaintext AVD.
`require_target()` then asserts exactly one device on the dedicated ADB server (port 5038, emulator
port 5556) whose serial matches the recorded run — this is why the tool never touches a developer's
default ADB server.

**`profiles/android-phone.json` is the environment pin.** `boot` reads locale, timezone, build
fingerprint, screen size, and OS2faktor/Chrome version names and codes from it and aborts on any
mismatch; `doctor` additionally compares emulator/adb versions and the sealed archive's SHA-256.
`seal` writes `sealed.at` and `sealed.archive_sha256` back into the manifest. Editing this file
re-pins what the tool will accept, so treat it as a deliberate change, not a fix for a failing check.

**Everything private lives under `private/`** (override with `GUIDE_CAPTURE_PRIVATE`), created mode
700: `.env`, `runtime/` (raw captures, UI dumps, logs, sealed golden), and `reviewed-output/`. The
whole directory is gitignored. `GUIDE_CAPTURE_GUIDES` points at the separate guides repository
(default `../guides`); this tool never publishes into it.

## Project Boundaries

| Change | Belongs in |
|---|---|
| Parsing, validation, image transformation, anything testable | `lib/guide_capture.py` + a case in `tests/test_guide_capture.py` |
| New device action, ADB interaction, run lifecycle | `bin/guide-capture` (add `command_*`, a `usage()` line, and a `case` arm) |
| DOM-level click behaviour or host allowlist | `lib/web_tap.mjs` |
| Emulator/image/package versions | `profiles/android-phone.json` |
| Capture step definitions | `specs/<slug>.<platform>.json` — `annotate` rejects a spec outside `specs/` |
| Agent operating procedure for a capture run | `skills/guide-capture/SKILL.md` |

`examples/` is a frozen worked output set kept as README evidence; regenerate it only deliberately.
`docs/` records phase decisions, not current API — the code is authoritative when they disagree.

## Common Change Workflows

**Adding a spec field** (spec keys are exact-matched, so a new key is rejected until every step is
done):

1. Add the key to the relevant `_require_exact_keys(...)` required/optional set in
   `validate_annotation_spec`, plus a `_validate_*` call.
2. Consume it in `_magick_annotation_command` (or `_validate_coordinates` for anything
   coordinate-bearing — bounds are checked against real image dimensions *before* any output is
   written).
3. Extend the report entry in `process_annotation_spec` if it should be auditable.
4. Add a rejection test and a behaviour test in `tests/test_guide_capture.py`.

**Adding a wrapper command:** write the pure logic as a `lib/guide_capture.py` subparser, add
`command_<name>` in `bin/guide-capture` that calls `require_target`, captures fresh evidence via
`capture_dump`, emits one `jq -nc` JSON object, calls `log_event`, and register it in both `usage()`
and the bottom `case`. Verify the resulting UI state — never treat exit 0 as proof.

**Adding a credentialed flow:** read values through `read_protected_env_values` (it enforces mode
`600` on the env file), build a newline-separated `input …` script in Python, pipe it into
`adb shell` (see `command_login_ishoj`), and delete the credential-bearing dumps in a `trap` before
returning. Document the variable in `.env.example`. Secrets must never reach `argv`, logs, or a
screenshot.

## Implementation Decisions

| Situation | Use | Avoid |
|---|---|---|
| Tapping a native Android control | `tap android '<selector>'` with one exact `text`/`content_desc`/`resource_id` | Coordinates, or any selector that matches 0 or >1 enabled node |
| Control only visible as DOM inside Chrome | `web-tap android '<exact visible text>'` | `tap` on the WebView, or widening the `web_tap.mjs` allowlist for a one-off |
| Entering a short non-secret search token | `type-public` — requires an empty, non-password `android.widget.EditText` with a stable resource ID | `type-public` for an email, username, PIN, or code, even when it passes the ASCII filter |
| Entering the authorized Ishøj/OS2faktor secrets | `login-ishoj android`, `unlock-os2faktor android` | Any generic text command; anything that puts the value in `argv` |
| Correcting redaction/annotation bounds after review | `annotate <spec.json> <retained-run-id>` (offline) | Rebooting the emulator, or hand-running ImageMagick |

## Critical Gotchas

- **`boot` fails while a run is recorded.** `an Android run is already active` means
  `private/runtime/current-run.json` exists — run `bin/guide-capture kill android` first. Always
  `kill` after errors and interruptions; it destroys the decrypted AVD.
- **`annotate` never overwrites.** It aborts if `private/reviewed-output/<slug>/annotation-report.json`
  or any per-step PNG exists. Archive the rejected directory under `private/runtime/` and rerun with
  the retained run ID.
- **A Homebrew upgrade of `emulator` or `adb` breaks `doctor`.** That is the pin working. Re-verify
  the environment and update `profiles/android-phone.json` intentionally rather than bypassing boot.
- **The wrapper resolves tools from absolute Homebrew paths** (`/opt/homebrew/bin/...`,
  `/usr/bin/jq`) and overwrites `PATH`. A non-standard prefix needs the constants at the top of
  `bin/guide-capture` changed; do not switch to bare command names.
- **Annotation reports must stay path-relative.** `_report_path` renders paths against the raw and
  reviewed roots because the report ships beside published screenshots; an absolute path would leak
  the operator's home directory. `test_report_records_relative_paths_only` guards this.
- **`annotate`'s out-of-scope error text says `automation/specs`** while the enforced directory is
  `<repo>/specs`. The code is correct; the message is stale.

## Additional Documentation

* `skills/guide-capture/SKILL.md` — Read in full before running or modifying any capture flow; it is
  the binding operating procedure (selector discipline, secret handling, shutdown, completion
  checklist).
* `skills/guide-capture/references/annotation-redaction.md` — Read before touching redaction or
  highlight bounds, or before reviewing staged images; defines the separate privacy-fit and
  target-fit passes.
* `docs/login-flow-ishoj.md` — Read before working on `login-ishoj` or `unlock-os2faktor`; records
  the standing credential authorization and its exact scope.
* `docs/phase-2-image-pipeline.md` — Read when changing the annotate command's inputs, output
  layout, or report contract.
* `docs/phase-3-capture-skill.md` — Read when changing `open`, `wait`, `tap`, `web-tap`, or
  `type-public` verification behaviour.
* `docs/status-bar-fallback.md` — Read when screenshots disagree on clock or status-bar state;
  explains the `live-short-run` fallback and why demo mode reports unsupported.
* `README.md` — Read for the Homebrew requirements list and first-time setup.

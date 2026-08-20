# AGENTS.md

This file provides guidance to AI coding agents when working with code in this
repository.

Guide Capture drives a disposable, encrypted Android emulator to produce redacted screenshots for
Danish education-service guides. There is no package manifest and no build step: a Bash entry
point, a Python helper, and a Node DevTools helper, all run from the repository root.

## Verify a change

These four are what `prek.toml` runs on every commit:

```bash
/bin/bash -n bin/guide-capture bin/check-sensitive-files
shellcheck bin/guide-capture bin/check-sensitive-files
python3 -m unittest discover -s tests -v
node --check lib/web_tap.mjs
```

One file, one case, or by name:

```bash
python3 -m unittest tests.test_guide_capture
python3 -m unittest tests.test_guide_capture.AnnotationPipelineTests.test_report_records_relative_paths_only
python3 -m unittest discover -s tests -k relative_paths
```

`AnnotationPipelineTests` shells out to `/opt/homebrew/bin/magick` with no skip guard — without
ImageMagick installed those tests error rather than skip. `prek run --all-files` adds Gitleaks and
the sensitive-path guard; the commit-msg hook enforces Conventional Commits.
`bin/guide-capture doctor` checks the live machine and needs the sealed golden, so it is not part
of the suite.

## Ownership

- `bin/guide-capture` — every side effect: emulator, ADB, `age`, run state, evidence files,
  permissions, logging. Never invoke `adb`, `emulator`, `age`, or `magick` from anywhere else,
  including from your own shell while working on a task.
- `lib/guide_capture.py` — all pure logic: parsers, schema validation, protected input-script
  generation, AVD rewriting, the ImageMagick command builder. New testable behavior belongs here
  with a unit test, not in the wrapper.
- `lib/web_tap.mjs` — one exact DOM click over Chrome DevTools, gated by a hardcoded HTTPS host
  allowlist (`aula.dk`, `www.aula.dk`, `broker.unilogin.dk`, `login-idp.ishoj.dk`).
- `profiles/android-phone.json` — the environment pin. The wrapper derives the system-image path,
  Android target, package IDs, expected versions, and the status-bar expectation from it.
- `specs/<slug>.<platform>.json` — capture steps and image bounds. Nothing else may carry capture
  coordinates.

## Command contract

Every action command writes exactly one JSON object to stdout, for success *and* for handled
failure; human prose goes to stderr; `--help` prints usage to stderr. Tests assert on the JSON
fields and on these exit codes — do not collapse a failure to `1`:

| Code | Meaning |
|---:|---|
| `0` | Success, including idempotent `kill` with no active run |
| `1` | `doctor` finished with failing checks |
| `2` | Selector missing, or `wait` timed out |
| `3` | Selector ambiguous |
| `64` | Invalid arguments, selector, or specification |
| `65` | Invalid data, profile, run state, or annotation input |
| `66` | Required input or Android package missing |
| `69` | Tool or device unavailable, or resulting state unverifiable |
| `70` | Internal path-safety refusal |
| `73` | An existing capture, reviewed output, or sealed archive would be overwritten |

## Gotchas

- The shebang is `#!/bin/bash` — macOS system Bash **3.2**. No `declare -A`, no `${var^^}`, no
  `mapfile`. Write Bash 3.2 constructs, or move the logic into the Python helper.
- The wrapper resolves every executable from a hardcoded absolute constant at the top of the file
  and overwrites `PATH`. Adding a tool means adding a constant plus a `doctor` check, not relying
  on `PATH`.
- `boot` refuses while `private/runtime/current-run.json` exists. Run `bin/guide-capture kill
  android` after any error or interruption — it removes the decrypted run and keeps raw captures
  and logs.
- Run `validate <spec>` before booting. `annotate` re-validates, but only after the emulator work
  is already spent.
- `annotate` exits `73` if a reviewed PNG or report already exists. Archive the rejected
  `private/reviewed-output/<slug>/` beneath `private/runtime/`, then rerun against the exact
  retained run: `bin/guide-capture annotate <spec> <run-id>`. Never reboot to fix image bounds.
- Annotation-report paths must stay relative to their anchor (`_report_path`) — an absolute path
  leaks the operator's home directory into a file that ships beside published screenshots.
- Spec and profile schemas reject unknown keys (`_require_exact_keys`). A new spec field needs an
  entry in `validate_annotation_spec` and a consumer, or `validate` rejects the whole file.
- A Homebrew upgrade of the emulator or platform-tools makes `doctor` fail by design. Verify the
  new versions and re-pin `profiles/android-phone.json`; do not relax the check.
- `examples/` is frozen evidence: `test_worked_example_hashes_match_its_report` pins each PNG's
  SHA-256 to `examples/hvordan-bruger-jeg-os2faktor/annotation-report.json`. Regenerate the report
  together with the images, or the suite fails.
- Everything sensitive or generated lives under `private/` (gitignored, mode 700), relocatable only
  via `GUIDE_CAPTURE_PRIVATE`. Write run output, credentials, and raw captures nowhere else;
  `bin/check-sensitive-files` rejects the commit otherwise.
- Secrets never go into arguments, logs, or retained evidence. The only authorized entry paths are
  `login-ishoj android` and `unlock-os2faktor android`, which read `private/.env` through a pipe
  and delete the credential-bearing dumps afterwards.

## Reference

- `skills/guide-capture/SKILL.md` — the binding capture procedure: selectors, evidence,
  verification, shutdown. Read before running or changing any capture flow.
- `skills/guide-capture/references/annotation-redaction.md` — redaction and highlight fit rules
  plus the four required review passes. Read before editing bounds or reviewing images.
- `docs/login-flow-ishoj.md` — the standing credential authorization and its scope. Read before
  touching `login-ishoj`, `unlock-os2faktor`, or the host allowlist.
- `docs/status-bar-fallback.md` — why demo mode is reported unsupported and what `live-short-run`
  requires. Read when status bars differ between captures in a set.
- `README.md` — Homebrew prerequisites, sealed-golden provisioning, and the public workflow.

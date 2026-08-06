# Guide Capture repository guidance

Guide Capture uses a Bash entry point, a Python validation/image helper, and a Node Chrome DevTools
helper. There is no package manifest or build step. Runtime tools are resolved from fixed
`/opt/homebrew` and macOS system paths. The wrapper must remain compatible with the macOS system
Bash 3.2 selected by its shebang.

## Verification

Run from the repository root:

```bash
/bin/bash -n bin/guide-capture bin/check-sensitive-files
shellcheck bin/guide-capture bin/check-sensitive-files
python3 -m unittest discover -s tests -v
node --check lib/web_tap.mjs
prek run --all-files
bin/guide-capture doctor
```

The annotation tests invoke `/opt/homebrew/bin/magick`. `prek.toml` runs the repository checks,
Gitleaks, and the commit-message hook; commits must use Conventional Commits.

## Architecture and contracts

- `bin/guide-capture` is the public entry point and owns emulator, ADB, encryption, run state,
  evidence, logging, and file permissions.
- `lib/guide_capture.py` owns parsers, exact schema validation, protected input-script generation,
  AVD rewriting, and the ImageMagick pipeline. Pure behavior belongs here and under unit test.
- `lib/web_tap.mjs` performs one exact DOM click through Chrome DevTools. Its HTTPS host allowlist is
  intentionally limited to Aula, the UniLogin broker, and Ishøj IdP.

Action commands emit one JSON object on stdout for success and handled failure; human prose goes to
stderr. `--help` prints usage to stderr. Preserve command-specific JSON fields and these exit codes:

| Code | Meaning |
|---:|---|
| `0` | Success, including idempotent `kill` with no active run |
| `1` | `doctor` completed with one or more failed checks |
| `2` | Selector missing or wait timed out |
| `3` | Selector ambiguous |
| `64` | Invalid arguments, selector, or specification |
| `65` | Invalid data, profile, run state, or annotation input |
| `66` | Required input or Android package missing |
| `69` | Tool/device unavailable or resulting state could not be verified |
| `70` | Internal path-safety refusal |
| `73` | Existing capture, reviewed output, or sealed archive would be overwritten |

`private/runtime/current-run.json` is the single active-run lock. Its exact schema, run directory,
AVD directory, serial, and positive emulator PID are validated before use. The dedicated ADB server
uses port `5038`; the only accepted target is `emulator-5556`. `kill` removes the state and decrypted
AVD but retains raw captures and logs.

`profiles/android-phone.json` is the environment pin. Its exact schema is validated before `boot`
or `seal`. The wrapper derives the system-image path, Android target, package IDs, status-bar
expectation, and all version comparisons from it. `doctor` also checks the system-image revision,
emulator/ADB versions, sealed archive hash, runtime permissions, and annotation font. Treat profile
edits as deliberate re-pinning.

Everything sensitive or generated during a run belongs beneath `private/`, overridden only by
`GUIDE_CAPTURE_PRIVATE`. The default tree is gitignored and mode-restricted. The tool never
publishes into a guides repository.

## Change boundaries

| Change | Location |
|---|---|
| Parsing, validation, protected-input preparation, image processing | `lib/guide_capture.py` and `tests/test_guide_capture.py` |
| Device action, ADB interaction, run lifecycle, command JSON | `bin/guide-capture` |
| DOM click behavior or approved host allowlist | `lib/web_tap.mjs` |
| Emulator, image, package, and status-bar pins | `profiles/android-phone.json` |
| Guide capture steps and image bounds | `specs/<slug>.<platform>.json` |
| Agent capture procedure | `skills/guide-capture/SKILL.md` |
| Privacy and highlight review criteria | `skills/guide-capture/references/annotation-redaction.md` |

The tracked `examples/` set is frozen README evidence; regenerate it only deliberately. Current
behavior comes from code and tests. Documentation should explain operator decisions or rationale,
not duplicate executable implementation details.

## Change patterns

When adding a specification field:

1. Add it to the exact-key schema and validate its type/value in `validate_annotation_spec`.
2. Consume it in `_magick_annotation_command`, `_validate_coordinates`, or the report as needed.
3. Add one rejection test and one behavior test.

When adding a device command:

1. Put testable parsing or validation in the Python helper.
2. Add `command_<name>` in the wrapper, using `require_target` and fresh evidence where applicable.
3. Emit exactly one JSON result, log only command/outcome, and add the usage and `case` entries.
4. Verify the resulting UI state; process exit zero alone is not evidence.

When adding a credentialed flow, use `read_protected_env_values`, build a newline-separated device
script in Python, pipe it to `adb shell`, and remove credential-bearing dumps with a trap. Document
the variable in `.env.example` and update the authorization contract. Never put a resolved secret
in arguments, logs, output, specifications, or screenshots.

## Operating decisions

| Situation | Use | Do not use |
|---|---|---|
| Native Android control | `tap android '<selector>'` with one exact semantic field | Coordinates or non-unique selectors |
| Approved WebView control | `web-tap android '<exact visible text>'` | Tapping the WebView node or widening the allowlist for one run |
| Short public search token | `type-public` on one empty, non-password field | Email, username, PIN, code, identifier, or token |
| Authorized Ishøj credentials | `login-ishoj android` | Generic text entry or secret arguments |
| Authorized OS2faktor PIN | `unlock-os2faktor android` | Generic text entry or secret arguments |
| Offline redaction/highlight correction | `annotate <spec> <retained-run-id>` | Rebooting or invoking ImageMagick directly |

## Gotchas

- `boot` refuses to run while `private/runtime/current-run.json` exists. Always run `kill android`
  after errors and interruptions.
- Run `validate <spec>` before boot; `annotate` is intentionally too late to be the first schema
  check.
- `annotate` returns `73` if a per-guide report or PNG already exists. Archive the rejected
  reviewed-output directory beneath `private/runtime/` before rerunning the exact retained run.
- Homebrew upgrades to the pinned emulator or ADB make `doctor` fail by design. Verify and re-pin;
  do not bypass the check.
- Annotation report paths must remain relative. Absolute paths expose the operator's home directory.
- The wrapper assumes `/opt/homebrew`; changing prefixes requires updating its path constants.

## Required references

- Read `skills/guide-capture/SKILL.md` before running or modifying a capture flow.
- Read `skills/guide-capture/references/annotation-redaction.md` before editing bounds or reviewing
  images.
- Read `docs/login-flow-ishoj.md` before changing or using protected login commands.
- Read `docs/status-bar-fallback.md` when the live status bar differs between captures.
- Read `README.md` for supported setup and the public workflow.

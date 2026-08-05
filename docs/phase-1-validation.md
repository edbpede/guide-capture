# Phase 1 validation

Status: Complete
Date: 2026-08-05

## Implemented contract

The entry point is `bin/guide-capture`. Phase 1 implements:

- `doctor`
- `boot android`
- `dump android`
- `wait android <selector-json>`
- `tap android <selector-json>`
- `shot android <id>`
- `kill android`
- `seal android`

The wrapper uses a dedicated ADB server on port 5038 and emulator serial `emulator-5556`. It never
targets the unrelated `spidola-tv-m0` AVD.

## Golden lifecycle

- The powered-off setup AVD was encrypted with passphrase-mode `age` after the owner entered the
  passphrase directly in Terminal.
- The encrypted archive is mode `600`, and its SHA-256 is recorded in
  `profiles/android-phone.json`.
- `boot android` streamed the decrypted archive directly into a fresh run directory, renamed and
  rewrote the copied AVD, cold-booted it, and verified locale, timezone, build fingerprint, screen
  dimensions, OS2faktor version, and Chrome version against the manifest.
- `kill android` stopped the emulator and dedicated ADB server and removed the plaintext run while
  retaining raw captures and logs.
- After successful restore and cleanup, the plaintext setup AVD and descriptor were permanently
  deleted. The encrypted archive is now the only golden at rest.

## Selector and capture checks

- Exact wait: passed with one enabled `content_desc` match.
- Exact tap: passed and refreshed the hierarchy after the state-changing action.
- Missing selector: stopped with exit code 2 and retained hierarchy/screenshot evidence.
- Ambiguous selector: stopped with exit code 3 and retained hierarchy/screenshot evidence.
- Normalized nodes contain text, content description, resource ID, class, clickable/enabled flags,
  bounds, and calculated center.
- Screenshot capture produced a 1080 × 2400 PNG with a SHA-256 and device timestamp in the JSON
  result.

## Issues found during validation

1. `ADB_SERVER_SOCKET` treated the dedicated port as a remote server. The wrapper now uses
   `ANDROID_ADB_SERVER_PORT`, which starts a local dedicated server correctly.
2. Android indents `versionCode=` output. Parsing now uses a tested expression rather than a
   whitespace-sensitive field number.
3. Failed emulator shutdown could recreate an empty run directory after an early removal. Failure
   cleanup now waits for the emulator process and validates/removes the run path again.
4. SystemUI accepted demo broadcasts but left `sysui_tuner_demo_on=0`, and the screenshot retained
   the live clock. The wrapper now reports demo mode as unsupported and uses the documented
   `live-short-run` fallback in `docs/status-bar-fallback.md`.

## Validation commands

- `bash -n bin/guide-capture`
- `shellcheck bin/guide-capture`
- `python3 -m unittest discover -s tests -v`
- `bin/guide-capture doctor`

All pass after cleanup, with zero plaintext run directories and no plaintext golden AVD.

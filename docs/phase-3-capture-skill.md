# Phase 3 capture skill

Status: Implemented
Date: 2026-08-05

## Verified target opening

`guide-capture open android <target>` accepts either a credential-free absolute HTTPS URL or a
lowercase Android package name. URLs open explicitly in the manifest-pinned Chrome package;
packages launch through their declared Android launcher activity.

The command:

1. Rejects insecure, credential-bearing, whitespace-containing, or shell-like targets before ADB.
2. Confirms the expected package is installed.
3. Opens the target without logging launcher output or returning the URL.
4. Polls Android's resumed-activity state for up to 15 seconds.
5. Saves a fresh UI hierarchy after the expected package becomes foreground.
6. Saves a diagnostic screenshot and fails if foreground verification times out.

## Skill contract

The project skill is `skills/guide-capture/SKILL.md`. It uses the wrapper only and requires:

- `doctor` before every boot.
- Exact semantic selection and post-action UI verification.
- Direct owner entry for passphrases, credentials, PINs, MitID, and one-time codes.
- Explicit redaction review before annotation.
- Destruction of the plaintext run before waiting for human image approval.
- Explicit owner approval before any reviewed PNG reaches the guides repository.
- A captured/skipped/failed report with evidence paths.

`agents/openai.yaml` is generated from the SKILL metadata using the system skill-creator tooling.

## Forward test

A clean-context, read-only pilot plan used the finished skill without device commands or file
changes. It correctly stopped before `doctor` because the pilot specification does not exist yet,
kept all credential/PIN entry with the owner, required semantic and hash evidence, planned teardown
before image approval, and blocked publication before approval.

The test also caught two Phase 4 concerns now made explicit in the skill: existing Chromebook prose
must not cause the Android enrollment to be renamed, and the current number/cropping of Chromebook
images must not silently reduce the requested Android capture set.

## Validation

- `bash -n bin/guide-capture`
- `shellcheck bin/guide-capture bin/check-sensitive-files`
- `python3 -m unittest discover -s tests -v`
- Skill-creator `quick_validate.py skills/guide-capture`
- `/Users/dkp/.local/bin/prek run --all-files`
- `bin/guide-capture doctor`

<div align="center">
	<h1>Guide Capture</h1>
	<p><strong>Reproducerbare Android-skærmbilleder til vejledninger — fanget, redigeret og annoteret sikkert</strong></p>
	<p>A disposable Android capture environment with explicit redaction, annotation, and human review.</p>
</div>

<div align="center">

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Bash](https://img.shields.io/badge/Bash-3.2%2B-4EAA25?logo=gnubash&logoColor=white)](https://www.gnu.org/software/bash/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![Android](https://img.shields.io/badge/Android-Emulator-3DDC84?logo=android&logoColor=white)](https://developer.android.com/studio/run/emulator)

</div>

## Overview

Guide Capture restores a sealed Android AVD into a short-lived run and exposes one verified action
at a time. An operator or agent follows a JSON step specification, captures the required screens,
declares privacy redactions and instructional highlights, and stages PNGs for review. The tool does
not publish assets.

The bundled profile and protected login commands target Danish education services, including Aula,
UniLogin, Ishøj IdP, and OS2faktor. The selector and annotation pipeline itself is not tied to one
guide.

## Output

| Step 1 — pick login | Step 5 — redacted device list | Step 7 — redacted file listing |
|:---:|:---:|:---:|
| <img src="examples/hvordan-bruger-jeg-os2faktor/01.android.png" width="220" alt="Aula login options with callout 1"> | <img src="examples/hvordan-bruger-jeg-os2faktor/05.android.png" width="220" alt="OS2faktor device list with a second device redacted"> | <img src="examples/hvordan-bruger-jeg-os2faktor/07.android.png" width="220" alt="Aula secure files with the listing redacted"> |

Reviewed output includes `annotation-report.json`, which records relative input/output paths,
dimensions, SHA-256 hashes, redaction counts, and the mandatory human-review gate. The tracked
[`examples/`](examples/) directory is a frozen reviewed output set.

## Safety contract

- Raw captures, UI dumps, logs, credentials, the decrypted AVD, and working output stay beneath the
  configured private tree, which defaults to the gitignored `private/` directory.
- Device input uses one exact `text`, `content_desc`, or `resource_id` selector and stops on zero or
  multiple enabled matches. Approved WebView actions use a fixed HTTPS host allowlist.
- Generic text entry accepts only a short public ASCII token in one verified empty, non-password
  field. The protected login commands read their authorized values from a mode-`600` file without
  putting them in arguments or retained evidence.
- Redaction is opaque and runs before annotation. Source dimensions and all coordinates are
  validated before output is written.
- Existing captures, reviewed PNGs, reports, and sealed archives are never overwritten.
- The emulator and dedicated ADB server are isolated from a developer's default ADB server and are
  destroyed by `kill android`; raw captures and logs remain for review.
- Only explicitly approved reviewed PNGs may be copied into a guides repository.

The binding operating procedure is [`skills/guide-capture/SKILL.md`](skills/guide-capture/SKILL.md).
Privacy and annotation review criteria are in
[`skills/guide-capture/references/annotation-redaction.md`](skills/guide-capture/references/annotation-redaction.md).

## Requirements

The wrapper targets Apple Silicon macOS with Homebrew at `/opt/homebrew` and Android command-line
tools at `/opt/homebrew/share/android-commandlinetools`. Install the Homebrew dependencies:

```bash
brew install age zstd imagemagick node python@3.14
brew install --cask android-commandlinetools
```

It also uses the macOS executables `/usr/bin/jq`, `/usr/bin/tar`, `/usr/bin/shasum`, and
`/usr/bin/stat`. Development checks additionally require `shellcheck` and
[`prek`](https://prek.j178.dev). Run `bin/guide-capture doctor` to verify the pinned system image,
emulator/ADB versions, required tools, profile, font, permissions, and sealed archive.

## Setup

```bash
git clone git@github.com:edbfi/guide-capture.git
cd guide-capture
prek install --hook-type pre-commit --hook-type commit-msg
```

The enrolled golden is intentionally not stored in Git. An authorized operator must provision
`private/runtime/sealed-goldens/android-phone.tar.zst.age` with the SHA-256 recorded in the pinned
profile. Then run `bin/guide-capture doctor`; do not boot until every check passes.

Only the standing Ishøj/OS2faktor flow needs a credential file:

```bash
mkdir -p private
cp .env.example private/.env
chmod 600 private/.env
$EDITOR private/.env
```

The authorization and destination scope for those values is recorded in
[`docs/login-flow-ishoj.md`](docs/login-flow-ishoj.md).

## Workflow

1. Create a specification beneath [`specs/`](specs/) with a safe start target, ordered capture
   steps, and an explicit `redact` array for every step. Run `validate` before booting.
2. Run `doctor`, boot the disposable emulator, and open the specification's start target.
3. For each action, wait for one exact selector, inspect its private evidence, capture the screen
   before the action, tap it, and verify the resulting state. Capture-only steps use `dump` followed
   by `shot`.
4. Inspect every raw PNG at full resolution. Record all redactions and optional highlight bounds in
   the specification.
5. Run `annotate`, then immediately run `kill android` before waiting for human review.
6. Review every staged PNG independently for privacy coverage and instructional target fit. Copy
   only owner-approved PNGs into the guides repository.

The core command sequence is:

```bash
bin/guide-capture validate specs/guide-name.android.json
bin/guide-capture doctor
bin/guide-capture boot android
bin/guide-capture open android https://example.dk
bin/guide-capture wait android '{"text":"Filer"}'
bin/guide-capture shot android 02
bin/guide-capture tap android '{"text":"Filer"}'
bin/guide-capture wait android '{"text":"Sikre filer"}'
bin/guide-capture annotate specs/guide-name.android.json
bin/guide-capture kill android
```

Raw PNGs are retained in `private/runtime/raw-captures/<run-id>/`; reviewed output is staged in
`private/reviewed-output/<slug>/`. To correct offline bounds after shutdown, archive the rejected
reviewed-output directory and pass the exact retained run ID:

```bash
bin/guide-capture annotate specs/guide-name.android.json android-20260805T113051Z-69884
```

Every action command writes one machine-readable JSON object to stdout for success or a handled
failure. Human-readable status goes to stderr. Run `bin/guide-capture --help` for the complete
command list.

## Layout

```text
bin/         side-effecting wrapper and staged-path guard
lib/         Python validation/image pipeline and Node WebView helper
specs/       capture and annotation specifications
profiles/    pinned Android environment
skills/      binding agent operating procedure and review criteria
docs/        credential authorization and environment-specific rationale
examples/    frozen reviewed output
private/     gitignored runtime, credentials, raw evidence, and working output
```

Set `GUIDE_CAPTURE_PRIVATE` to relocate the private tree.

## License

[GNU AGPL v3](LICENSE) — © edbpede

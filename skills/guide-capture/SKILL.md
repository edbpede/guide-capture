---
name: guide-capture
description: Capture, verify, redact, annotate, and stage reproducible Android screenshots for the guides.edb.fi site. Use when Codex needs to capture or recapture an Android guide flow, operate the encrypted guide-capture emulator through its wrapper, prepare reviewed PNG variants from a JSON step specification, or report evidence for a failed capture step.
---

# Guide Capture

Run one short disposable Android capture session from the repository root. Treat the AVD, UI dumps,
raw screenshots, authentication screens, and working output as sensitive.

## Paths

- Wrapper: `bin/guide-capture`
- Specifications: `specs/`
- Raw evidence: `private/runtime/raw-captures/` and `private/runtime/logs/`
- Reviewed output: `private/reviewed-output/`
- Protected values: `private/.env`

`GUIDE_CAPTURE_PRIVATE` may relocate the private tree. Never load, quote, or repeat resolved values
from `.env`.

## Invariants

- Use `bin/guide-capture` for every emulator, ADB, encryption, selector, screenshot, and image action.
  Never invoke `adb`, `emulator`, `age`, or ImageMagick directly.
- Never pass a password, PIN, one-time code, enrollment secret, personal identifier, or token-bearing
  URL as an argument.
- Generic UI input is not authorized for secrets. The only standing exceptions are
  `login-ishoj android` for `I_ACC_EMAIL`/`I_ACC_PASS` and `unlock-os2faktor android` for
  `OS2FAKTOR_PIN`, read from `.env` under `docs/login-flow-ishoj.md`.
- Use one exact `text`, `content_desc`, or `resource_id` selector from fresh private evidence. Stop
  on zero or multiple enabled matches; never invent device coordinates.
- Use `web-tap` only when an approved Aula/UniLogin/Ishøj HTTPS page is visible and UIAutomator
  exposes only a WebView. It must find one exact visible DOM control on the fixed host allowlist.
- Treat non-Danish application or browser UI as a failed capture.
- Never bypass secure-window, integrity, attestation, or emulator-detection controls.
- Never publish raw evidence. Only owner-approved reviewed PNGs may enter a guides repository.
- Always run `kill android`, including after failure, interruption, or skipped work.
- Treat command success as provisional until its evidence shows the intended state.

Specification redaction/highlight bounds are offline image coordinates. They are allowed and must
never be reused as device-input coordinates.

## Procedure

### 1. Prepare

1. Read the requested guide and its Android specification. For Ishøj or OS2faktor authentication,
   also read `docs/login-flow-ishoj.md`.
2. If the specification is missing, create only the requested capture steps. Every step must have
   `redact`, including `[]`; add selectors and image bounds only after fresh evidence exists.
3. Run `bin/guide-capture validate <spec.json>` and correct every schema error before booting.
4. Run `bin/guide-capture doctor`. Do not boot unless every check passes.

### 2. Boot and open

1. Run `bin/guide-capture boot android`.
2. If `age` requests its passphrase, ask the owner to enter it directly in Terminal, never in chat.
3. Run `bin/guide-capture open android <start.value>` using the specification's credential-free
   HTTPS URL or package name.
4. Verify the returned foreground package and post-open hierarchy. Retain the reported demo-mode or
   status-bar fallback for the consistency review. If notification clearing is unsupported,
   visually confirm that no notification indicator enters a capture.

### 3. Capture

For a native step with `find`:

1. Run `bin/guide-capture wait android '<find-selector>'` and inspect its returned node evidence to
   confirm the unique match is the intended control.
2. Run `bin/guide-capture shot android <step-id>` before acting.
3. Run `bin/guide-capture tap android '<find-selector>'`; it re-dumps before tapping and returns
   before/after evidence.
4. When `expect_after` exists, run `wait` for it. Otherwise inspect the tap's `after` hierarchy.

When UIAutomator exposes only a WebView, inspect the visible page, take the step screenshot, then run
`bin/guide-capture web-tap android '<exact-visible-text>'` and verify its post-action hierarchy.

For a capture-only step without `find`, run `dump`, verify the intended state, and run `shot`. Do not
manufacture an action.

`bin/guide-capture type-public android '<resource-id-selector>' <token>` is limited to a 1–64
character public ASCII search token and one verified empty, non-password
`android.widget.EditText`. Use the shortest prefix that produces the intended exact Danish result.
Never use it for an email, username, PIN, code, personal identifier, or token even if the characters
pass validation.

Use `bin/guide-capture back android` only to dismiss a verified transient Android or keyboard
overlay. It sends Back once; do not use it speculatively for webpage navigation.

When a verified OS2faktor request is pending:

1. Run `bin/guide-capture notifications android`, inspect its private hierarchy, and use
   `bin/guide-capture tap` on one exact OS2faktor notification.
2. Verify the `Angiv pinkode` screen, then run `bin/guide-capture unlock-os2faktor android`.
3. Confirm `sensitive_evidence_retained:false`, verify the application and browser control codes
   match, and approve only the matching request with one exact selector.

Run `bin/guide-capture login-ishoj android` only on the verified blank Ishøj form and require
`sensitive_evidence_retained:false`.

Outside the standing Ishøj/OS2faktor authorization, stop before any secret entry. Ask the owner to
enter the value directly in the emulator, then re-dump and verify the resulting state. Never capture
a screen after a secret has been visibly entered.

If evidence is missing, ambiguous, non-Danish, or inconsistent with the requested flow, preserve the
wrapper's private evidence and mark the step failed. Do not rename an enrolled device or alter state
merely to force Android to match another platform's prose.

### 4. Redact, annotate, and shut down

1. Inspect every raw PNG at full resolution for names, usernames, email addresses, avatars, device
   IDs, notification contents, tokens, and student information.
2. Read `skills/guide-capture/references/annotation-redaction.md` and perform its raw privacy
   inventory before declaring any `redact: []` safe.
3. Record every opaque redaction with a reason. Record a tight numbered highlight and optional arrow
   only where instructionally useful.
4. Run `bin/guide-capture annotate <spec.json>`.
5. Verify the report has one input/output hash record per captured step and
   `human_review_required:true`.
6. Run `bin/guide-capture kill android` before waiting for review.

If annotation fails, still kill the run. Never reproduce the image pipeline manually.

For offline corrections, archive the rejected `private/reviewed-output/<slug>/` directory beneath
`private/runtime/`, update the specification, and run:

```bash
bin/guide-capture annotate <spec.json> <retained-run-id>
```

Use the exact reviewed run ID. Never infer a retained run or reboot only to adjust image bounds.

### 5. Review and publish

1. Inspect every staged PNG at full resolution using all four passes in
   `skills/guide-capture/references/annotation-redaction.md`.
2. Confirm all UI is legible Danish, status bars are acceptably consistent, and wording differences
   from other platforms are reported.
3. Show the staged images to the owner and obtain explicit approval.
4. Copy only approved PNGs into the matching guides `public/screens/` directory. Never copy the
   report, raw PNGs, XML, normalized nodes, logs, or run state.
5. Report each requested step as `captured`, `skipped`, or `failed`, with its evidence or reviewed
   output path.

Do not edit guide integration or publish assets unless the user's task includes that work.

## Completion

- `doctor` passed before boot.
- The start target and every action were semantically verified.
- Secrets used only owner entry or the two authorized protected commands and never entered retained
  evidence, arguments, logs, or output.
- Every captured step has one hash-tracked reviewed PNG and an explicit redaction decision.
- The emulator, dedicated ADB server, and decrypted run were destroyed.
- No reviewed image was published without owner approval.
- The final report accounts for every requested step and includes evidence paths.

---
name: guide-capture
description: Capture, verify, redact, annotate, and stage reproducible Android screenshots for the edbpede guides site. Use when Codex needs to capture or recapture an Android guide flow, operate the encrypted guide-capture emulator through its wrapper, prepare reviewed PNG variants from a JSON step specification, or report evidence for a failed capture step.
---

# Guide Capture

Use the stable wrapper to run one short, disposable Android capture session. Treat every raw image,
UI dump, authentication screen, and enrolled emulator as sensitive.

## Fixed locations

- Wrapper: `/Users/dkp/Documents/GitHub/edbpede/guide-capture/automation/bin/guide-capture`
- Specifications: `/Users/dkp/Documents/GitHub/edbpede/guide-capture/automation/specs/`
- Guides: `/Users/dkp/Documents/GitHub/edbpede/guides/`
- Reviewed output: `/Users/dkp/Documents/GitHub/edbpede/guide-capture/reviewed-output/`

Read the target MDX and JSON specification before booting. For an Ishøj education-service login,
also read
`/Users/dkp/Documents/GitHub/edbpede/guide-capture/automation/docs/login-flow-ishoj.md`. Do not load
or repeat secret values from `.env`.

## Non-negotiable rules

- Call `guide-capture` only. Never call raw `adb`, `emulator`, `age`, or ImageMagick commands.
- Never pass passwords, PINs, one-time codes, enrollment secrets, or token-bearing URLs as arguments.
- Never type a secret for the user. Pause and ask the device owner to enter it directly.
- Use exact `text`, `content_desc`, or `resource_id` selectors from fresh UI dumps.
- Never invent device coordinates. Stop on zero or multiple selector matches.
- Never bypass secure-window, integrity, attestation, or emulator-detection controls.
- Never publish raw captures. Copy only owner-approved, redacted output into the guides repository.
- Treat non-Danish app or browser UI as a failed capture.
- Always run `kill android`, including after errors, interruptions, or skipped steps.
- Treat command success as provisional until the expected UI state and output file are verified.

Image redaction and annotation bounds declared in the JSON specification are allowed. They are
offline image regions, not device-input coordinates.

## Workflow

### 1. Prepare

1. Read the target guide and specification.
2. If the specification is missing, create it from the requested guide scope before booting. Include
   each requested capture step and an explicit `redact` array, including `[]`; leave selectors and
   annotation bounds absent until fresh evidence exists.
3. Do not reduce the capture set merely because an existing guide step has no screenshot or uses an
   inline crop.
4. Run `guide-capture doctor`.
5. Stop and report every failing doctor check. Do not boot around version or golden drift.

### 2. Boot and open

1. Run `guide-capture boot android`.
2. When `age` requests its passphrase, ask the owner to enter it directly in Terminal. Do not ask
   them to paste it into chat.
3. Run `guide-capture open android <start.value>` using the specification's HTTPS URL or package.
4. Verify the returned foreground package and saved post-open UI evidence.
5. Record the boot result's demo-mode or documented status-bar fallback for review consistency.

Do not place session tokens, credentials, or redirect URLs containing secrets in `start.value`.

### 3. Capture each step

Use this sequence for a step with `find`:

1. Run `wait android '<find-selector>'`.
2. Run `dump android` and inspect the fresh hierarchy evidence.
3. Confirm exactly one visible, enabled match.
4. Run `shot android <step-id>` before the action so the screenshot shows what to select.
5. Run `tap android '<find-selector>'`.
6. Run `wait android '<expect_after-selector>'` when `expect_after` exists.
7. Inspect the refreshed hierarchy and confirm the intended state, not merely a zero exit code.

For a declared non-secret search token, `type-public android '<resource-id-selector>' <token>` may
be used only when the fresh hierarchy exposes one empty, non-password `android.widget.EditText`
with a stable resource ID. The token is deliberately limited to 1-64 ASCII letters, digits, dots,
underscores, or hyphens. Use the shortest public prefix that produces the intended exact result;
for example, type `Ish` and then select the visible exact Danish result `Ishøj Kommune`. Never use
`type-public` for an email address, username, password, PIN, one-time code, personal identifier, or
token, even if it would pass the character restrictions.

Use `back android` only after visual or hierarchy evidence confirms a transient Android or keyboard
overlay that should be dismissed. It sends Back exactly once and saves before/after evidence; do
not use it speculatively for webpage navigation.

For a capture-only step without `find`, dump and verify the intended state, then take the shot. Do
not manufacture an action.

If a login, PIN, MitID, OS2faktor, or enrollment secret is required:

1. Stop before entering it.
2. Tell the owner which visible emulator field or button needs attention.
3. Ask them to enter the secret directly in the emulator and reply when finished.
4. Re-dump the UI and verify the resulting state before continuing.

Do not capture a screen after a secret has been visibly entered. If the hierarchy is missing,
ambiguous, or inconsistent with the specification, preserve the wrapper's evidence and mark the
step failed instead of guessing.

If observed Android wording differs from Chromebook prose, record the Android wording for later
platform-specific integration. Do not rename an enrolled device or force the UI to match another
platform without owner approval.

### 4. Redact and annotate

1. Inspect every raw screenshot locally for names, usernames, email addresses, avatars, device IDs,
   notification contents, tokens, and student information.
2. Record every required opaque redaction region and reason in the specification. Keep `redact: []`
   only after an explicit inspection finds nothing sensitive.
3. Record the numbered highlight and optional arrow bounds in `annotate` where needed.
4. Run `guide-capture annotate <spec.json>` while the run is active.
5. Confirm the JSON report contains an input/output hash for every expected step and
   `human_review_required: true`.
6. Run `guide-capture kill android` before waiting for review.

If annotation fails, still run `kill android`. Do not manually reproduce the wrapper's image
pipeline or overwrite an older reviewed result.

### 5. Review and publish

1. Open every staged Android PNG and inspect it at full resolution.
2. Confirm Danish UI text is legible, redactions fully cover sensitive content, annotations point to
   the correct control, the status bar is consistent, and any prose difference is recorded.
3. Show the staged images to the owner and request explicit approval.
4. Only after approval, copy the PNGs into the matching directory under `guides/public/screens/`.
5. Never copy `annotation-report.json`, raw PNGs, XML, UI-node JSON, emulator logs, or run state.
6. Report each requested step as `captured`, `skipped`, or `failed`, with its evidence or reviewed
   output path.

Do not edit the guide's platform switching or publish assets unless the user's task includes that
work. Publishing and frontend integration remain separate reviewable changes.

## Completion checklist

- `doctor` passed before boot.
- The start target and every action were semantically verified.
- Secrets were entered only by the owner and never appeared in arguments or output.
- Every requested raw capture has a corresponding hash-tracked reviewed PNG.
- Every redaction decision is explicit.
- The emulator and dedicated ADB server were stopped and the plaintext run was destroyed.
- No reviewed image entered the guides repository without owner approval.
- The final report lists captured, skipped, and failed steps with evidence paths.

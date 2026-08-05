# Android status-bar fallback

The Android 36 Google Play image accepts SystemUI demo broadcasts but leaves
`sysui_tuner_demo_on=0`; visual verification also shows the live clock. The wrapper therefore
reports demo mode as unsupported instead of claiming that the status bar is pinned.

Phase 1 uses one explicit fallback named `live-short-run`:

1. Keep each guide capture in one short emulator run.
2. Clear notifications semantically before capture.
3. Record the device time in every `shot` JSON result.
4. Review all screenshots from a guide together and recapture the set if status-bar state changes
   materially between steps.

Do not silently label a live status bar as deterministic. Re-test demo-mode support after Android
system-image updates.

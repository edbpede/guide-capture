# OS2faktor feasibility spike

Status: Phase 0 complete — GO
Date: 2026-08-05
Operator: Device owner with Codex-assisted execution

## Environment

- Mac model and macOS version: MacBook Air (Apple M5, Mac17,3), macOS 26.5.2
- Android system image and revision:
  `system-images;android-36;google_apis_playstore;arm64-v8a`, revision 7
- Emulator version: 36.6.11.0 (build 15507667)
- ADB/platform-tools version: 37.0.0 (14910828)
- AVD hardware profile and dimensions: Pixel 7, 1080 × 2400
- Android build fingerprint:
  `google/sdk_gphone64_arm64/emu64a:16/BE2A.250530.026.D1/13818094:user/release-keys`
- Locale and timezone: `da-DK`, `Europe/Copenhagen`
- OS2faktor package ID and version: `dk.digitalidentity.os2faktor` 3.2.1
  (version code 30201)
- Chrome package version: `com.android.chrome` 133.0.6943.137 (version code 694313732)
- Play Store package version: `com.android.vending` 45.3.21-31 (version code 84532130)

## Go/no-go checks

| # | Check | Result | Evidence |
| --- | --- | --- | --- |
| 1 | OS2faktor is visible and installable from Google Play | Pass | Official Digital Identity listing installed through Danish Play catalog; Play Protect verified it |
| 2 | OS2faktor launches without rejecting the emulator | Pass | `MainActivity` reached the in-app device enrollment workflow |
| 3 | Enrollment completes with an approved identity | Pass | Owner-approved MitID verification completed; the OS2faktor self-service portal lists the emulator as an Android device named `EmuDroid`, and the app now presents its normal PIN screen |
| 4 | One approved challenge and PIN flow succeeds | Pass | Aula secure files generated an Ishøj NSIS request for `EmuDroid`; the app accepted the locally stored PIN, displayed the matching control code, approved the request, and Aula opened its secure-files route |
| 5 | ADB captures the relevant screens without blank or black secure windows | Pass | A full-size 1080 × 2400 PNG of the OS2faktor PIN screen rendered normally; the temporary identifier-bearing test capture was deleted after visual verification |
| 6 | A clean powered-off AVD copy retains a working enrollment | Pass | A powered-off copy cold-booted under the independent AVD name `edb-phone-clone`, retained OS2faktor 3.2.1 and the enrolled device ID, accepted the PIN, reached “Klar til anmodninger,” received and approved a fresh Ishøj NSIS challenge, and returned the browser to authenticated Aula; the disposable clone was deleted afterward |

## Security decisions

- Identity owner/approval: Owner explicitly approved using their real MitID identity on 2026-08-05
- Dedicated Google account confirmed: Yes
- Production credential used: Yes; owner explicitly approved using their real MitID identity and OS2faktor enrollment
- Secrets handled without command output: Yes; account values and the owner-provided OS2faktor PIN are stored only in the local mode-600 `.env` file and are excluded by the workspace ignore rules

## Outcome

- Decision: GO — the Android emulator is a viable OS2faktor capture source
- App-dependent capture source: Android emulator
- Step 6 capture source: Android emulator
- Limitations and follow-up: Play catalog initially used a Netherlands VPN exit and hid OS2faktor;
  a clean restart on a Danish exit exposed the official listing. Aula sessions used for the
  challenge checks were cleared before shutdown. Phase 1 may now implement the wrapper and
  sealed-golden workflow; MitID installation remains a separate later task.

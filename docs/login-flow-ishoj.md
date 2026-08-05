# Ishøj education-service login flow

Use this route for Aula and other Danish education services that delegate employee login to
the municipality's identity provider.

## Credential authorization contract

The workspace owner authorizes guide-capture automation and agents operating in this workspace to
read `private/.env` and use `I_ACC_EMAIL`, `I_ACC_PASS`, and `OS2FAKTOR_PIN` to complete the approved
education-service login flow, including Aula and OS2faktor. This is standing authorization: do not
request confirmation again for each run while the file, variables, destination allowlist, and purpose
are unchanged.

Scope: entry and submission only, through the dedicated `login-ishoj` and `unlock-os2faktor`
commands. The contract does not authorize printing, logging, publishing, or retaining the resolved
values. Re-authorization is required if the credential source, variables, destination allowlist, or
purpose changes.

## Route

1. Open the education service's login page.
2. Choose the login family that offers `Unilogin`, `MitID`, and `Lokalt login`.
3. Choose `Lokalt login`.
4. Search for Ishøj and select the listing. The broker may label it `Ishøj` rather than
   `Ishøj Kommune`.
5. On the Ishøj IdP page, run `guide-capture login-ishoj android`. It reads `I_ACC_EMAIL` and
   `I_ACC_PASS` from the private `.env`, enters them through a private pipe, submits the
   exact `Login` control, and removes credential-bearing hierarchy evidence.
6. If higher assurance is requested, select the OS2faktor device `EmuDroid`, open the Android
   app, run `guide-capture unlock-os2faktor android`, verify that the browser and app control codes
   match, and approve the request.

## Secret handling

- The authorized local credential source is `private/.env` (relative to the repository root, or
  `$GUIDE_CAPTURE_PRIVATE/.env` when overridden); it contains `I_ACC_EMAIL`,
  `I_ACC_PASS`, and `OS2FAKTOR_PIN`. The dedicated `login-ishoj` and `unlock-os2faktor` commands
  may load these values under the standing authorization recorded above. They must never print,
  log, document, or pass the resolved values as command-line arguments.
- Keep `.env` at mode `600` and excluded from version control.
- Load secret values only at execution time; never print them or place their resolved values in
  commands, logs, screenshots, specifications, or documentation.
- Treat Aula and secure-files pages as private. Do not publish captures until personal data has
  been reviewed and redacted.
- Clear Aula cookies and local/session storage before preserving or sealing a reusable emulator
  state.

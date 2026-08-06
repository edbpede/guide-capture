# Ishøj education-service login flow

Use this route for Aula and other Danish education services that delegate employee login to
the municipality's identity provider.

## Credential authorization contract

The workspace owner authorizes Guide Capture and agents operating in this workspace to read
`private/.env` for one approved education-service flow. `I_ACC_EMAIL` and `I_ACC_PASS` may be
submitted only to the verified blank form on `login-idp.ishoj.dk`; `OS2FAKTOR_PIN` may be entered
only in the local `dk.digitalidentity.os2faktor` application. The browser allowlist is `aula.dk`,
`www.aula.dk`, `broker.unilogin.dk`, and `login-idp.ishoj.dk`.

This is standing authorization: do not request confirmation for each run while the credential file,
variable names, destinations, and purpose remain unchanged.

Scope is entry and submission only through the dedicated `login-ishoj` and `unlock-os2faktor`
commands. The contract does not authorize printing, logging, publishing, or retaining the resolved
values. Re-authorization is required if the credential source, variables, destination allowlist, or
purpose changes.

## Route

1. Open the education service's login page.
2. Choose the login family that offers `Unilogin`, `MitID`, and `Lokalt login`.
3. Choose `Lokalt login`.
4. Search for Ishøj and select the listing. The broker may label it `Ishøj` rather than
   `Ishøj Kommune`.
5. On the verified Ishøj IdP page, run `bin/guide-capture login-ishoj android`. It reads
   `I_ACC_EMAIL` and `I_ACC_PASS` from the private `.env`, enters them through a private pipe,
   submits the exact `Login` control, and removes credential-bearing hierarchy evidence.
6. If higher assurance is requested, select the OS2faktor device `EmuDroid`, open the Android
   app, run `bin/guide-capture unlock-os2faktor android`, verify that the browser and app control
   codes match, and approve the request.

## Secret handling

- The authorized source is `private/.env`, or `$GUIDE_CAPTURE_PRIVATE/.env` when overridden. The
  dedicated protected commands may load only the three variables named above.
- Keep `.env` at mode `600` and excluded from version control.
- Never print, log, document, retain, capture, or pass a resolved value as an argument.
- Treat Aula and secure-files pages as private. Do not publish captures until personal data has
  been reviewed and redacted.
- Clear Aula cookies and local/session storage before preserving or sealing a reusable emulator
  state.

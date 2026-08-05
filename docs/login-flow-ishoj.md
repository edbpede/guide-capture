# Ishøj education-service login flow

Use this route for Aula and other Danish education services that delegate employee login to
the municipality's identity provider.

## Route

1. Open the education service's login page.
2. Choose the login family that offers `Unilogin`, `MitID`, and `Lokalt login`.
3. Choose `Lokalt login`.
4. Search for Ishøj and select the listing. The broker may label it `Ishøj` rather than
   `Ishøj Kommune`.
5. On the Ishøj IdP page, run `guide-capture login-ishoj android`. It reads `I_ACC_EMAIL` and
   `I_ACC_PASS` from the workspace-root `.env`, enters them through a private pipe, submits the
   exact `Login` control, and removes credential-bearing hierarchy evidence.
7. If higher assurance is requested, select the OS2faktor device `EmuDroid`, open the Android
   app, unlock it with `OS2FAKTOR_PIN`, verify that the browser and app control codes match,
   and approve the request.

## Secret handling

- The authorized local credential source is
  `/Users/dkp/Documents/GitHub/edbpede/guide-capture/.env`; it contains `I_ACC_EMAIL` and
  `I_ACC_PASS`. The dedicated `login-ishoj` command may load these values after the owner has
  explicitly authorized autonomous Ishøj login. It must never print, log, document, or pass their
  resolved values as command-line arguments.
- Keep `.env` at mode `600` and excluded from version control.
- Load secret values only at execution time; never print them or place their resolved values in
  commands, logs, screenshots, specifications, or documentation.
- Treat Aula and secure-files pages as private. Do not publish captures until personal data has
  been reviewed and redacted.
- Clear Aula cookies and local/session storage before preserving or sealing a reusable emulator
  state.

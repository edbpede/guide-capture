# Ishøj education-service login flow

Use this route for Aula and other Danish education services that delegate employee login to
the municipality's identity provider.

## Route

1. Open the education service's login page.
2. Choose the login family that offers `Unilogin`, `MitID`, and `Lokalt login`.
3. Choose `Lokalt login`.
4. Search for Ishøj and select the listing. The broker may label it `Ishøj` rather than
   `Ishøj Kommune`.
5. On the Ishøj IdP page, fill the account fields from `I_ACC_EMAIL` and `I_ACC_PASS` in the
   workspace-root `.env` file.
6. Submit the login.
7. If higher assurance is requested, select the OS2faktor device `EmuDroid`, open the Android
   app, unlock it with `OS2FAKTOR_PIN`, verify that the browser and app control codes match,
   and approve the request.

## Secret handling

- The authorized local credential source is
  `/Users/dkp/Documents/GitHub/edbpede/guide-capture/.env`; it contains `I_ACC_EMAIL` and
  `I_ACC_PASS`. Codex may verify that this file exists and is protected, but must not print, log,
  document, or pass the resolved values to automation. The device owner enters them directly in
  the emulator when prompted.
- Keep `.env` at mode `600` and excluded from version control.
- Load secret values only at execution time; never print them or place their resolved values in
  commands, logs, screenshots, specifications, or documentation.
- Treat Aula and secure-files pages as private. Do not publish captures until personal data has
  been reviewed and redacted.
- Clear Aula cookies and local/session storage before preserving or sealing a reusable emulator
  state.

# Development CI

Every PR and default-branch push runs the existing prek checks on native macOS 26
ARM64: system Bash 3.2 parsing, ShellCheck, Python unit/annotation/wrapper tests,
Node syntax, Gitleaks and repository hygiene. The runner must have the fixed
Homebrew paths used by the application. ImageMagick and ShellCheck are installed
through Homebrew; other system tools follow the runner image maintenance cycle.

Run `prek run --all-files` on the supported Mac. The workflow additionally runs
`bin/check-sensitive-files --all`: the local hook checks staged changes, while a
fresh CI checkout needs all tracked paths checked. Tests verify rejection of
synthetic private paths and acceptance of the empty environment template.

The shared `ci / required` gate rejects missing, failed, cancelled and skipped
prerequisites and verifies explicitly dispatched PR SHAs. Tokens are read-only,
actions use full version tags and CI rejects tracked-file mutations. Renovate
inherits the versioned shared base policy and tracks hook/action/runtime pins.

No emulator boot, credentials, real login, golden archive, live captures or
annotation edits are part of development CI. Annotation tests operate on
synthetic temporary images; existing worked-example hashes remain protected.
The encrypted live capture workflow and pinned Android environment require their
existing manual procedure. There is no application build or dependency lock to
invent for these standalone tools; static Python typing is a remaining gap.

The shared dispatch guard and aggregate gate verify explicit PR and final commit
SHAs and reject missing, skipped or failed prerequisites. Renovate updates merge
unattended after every required job passes on the current revision, including
majors and shared-policy updates. The checked action verifies genuine author
sign-offs and dispatches exact-commit final CI. No dashboard approvals, branch
protections or rulesets are configured; native GitHub automerge stays disabled.
Other changes retain full manual review and the maintainer's ghmerge process.

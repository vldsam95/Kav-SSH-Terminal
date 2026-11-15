# Security and sensitive data

Kav SSH Terminal is an experimental personal project. No independent security audit has been performed, and there is no guaranteed support or response time.

## Reporting a problem

Do not put credentials, private keys, personal server details or exploitable private information in a public issue. If GitHub's private vulnerability reporting is enabled, use the repository's Security tab to report privately. Otherwise open a minimal issue asking for a private contact channel, without disclosing the vulnerability details or sensitive data.

## Local data

- Passwords and passphrases are used in memory for SSH/SFTP authentication. Optional saved passwords use the operating system keychain through `keyring`.
- Connection-profile JSON contains server/user metadata and may be sensitive even without passwords. Profiles and settings live outside the source tree by default.
- Legacy `BidiSSH` config/keychain identifiers are intentionally preserved across the product rename; they are not copies of user credentials.
- Private keys are selected by local path. Do not add them to this repository.
- Remote text editing may create temporary files on the local filesystem. Review this behavior before editing secrets; cleanup after all error/crash scenarios has not been certified.
- Verify server host keys independently. The client uses the user's SSH known-hosts file and does not provide a complete first-connection trust workflow.

## Publishing or contributing

Review `git diff --cached` and the staged filenames before pushing. Keep environments, profiles, logs, keys and `.env` files out of Git. `.gitignore` does not protect files that were already committed. Rotate any exposed real credential; removing it in a later commit does not remove it from history or copies.

Secret scanning is a useful check, not proof that a repository contains no sensitive information. Use synthetic hostnames and credentials in tests and redact screenshots before sharing.

# Security notes

- Treat all share URLs as secrets. Anyone possessing a URL can download its export until expiration or revocation.
- The revocation token is separate from the share URL. Never include it in the shared message or logs.
- Put share creation and revocation behind authenticated application-level authorization before production use. The included router intentionally leaves identity/tenant policy to the host FastAPI application.
- Use HTTPS, rate limiting, audit logging, persistent protected storage, retention cleanup, backup protection, and dependency/security scanning.
- Do not send actual patient information to a public deployment until your organization has approved the full data flow and applicable compliance requirements.

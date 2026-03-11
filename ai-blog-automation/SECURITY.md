# Security Policy

## Supported Versions

The following versions of the AI Blog Automation Platform are currently supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take the security of this project seriously. If you believe you have found a security vulnerability, please report it to us by:

1.  Opening a private security advisory on GitHub (if available).
2.  Emailing the maintainers at `security@example.com`.

Please include the following information in your report:

-   A description of the vulnerability.
-   Steps to reproduce the issue.
-   Potential impact of the vulnerability.
-   Any suggested fixes or mitigations.

We will acknowledge your report within 48 hours and provide a timeline for a fix. Do not disclose the vulnerability publicly until a fix has been released.

## Best Practices

To keep your deployment secure:

-   **API Keys:** Never commit `.env` files or API keys to version control.
-   **Database:** Use strong passwords and restrict network access to your PostgreSQL instance.
-   **WordPress:** Use "Application Passwords" with a dedicated, non-administrator user for publishing if possible.
-   **Secrets:** Use a secret manager (like AWS Secrets Manager or HashiCorp Vault) for production deployments.

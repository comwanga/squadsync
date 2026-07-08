# Security

## Supported Branch

Security fixes target the `main` branch.

## Reporting

Please report vulnerabilities privately through GitHub Security Advisories for this repository. Do not open a public issue for sensitive reports.

## Sensitive Data

- Do not commit `.env`, wallet connection strings, organizer recovery keys, API keys, database dumps, or payout receipts containing private data.
- Optional wallet credentials are intended for per-request browser use only and must not be stored server-side.
- Participant exports contain personal data. Treat CSV/PDF exports as private unless the organizer explicitly shares them.

## Baseline Expectations

- The app must run without optional AI keys.
- The app must run without reward payout setup.
- Participant registration must remain unauthenticated.
- Public results must not expose participant email addresses.

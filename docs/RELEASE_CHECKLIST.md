# Release Checklist

## Product

- Default organizer flow is clear: create event, share QR/link, generate teams.
- Participant join flow works on mobile without account creation.
- No protocol or wallet jargon appears in the default user journey.
- App works without `ANTHROPIC_API_KEY`.
- App works without reward payout setup.
- Public results do not expose participant email addresses.

## Engineering

- `docker compose up --build` starts the full local app.
- Backend tests pass.
- Frontend lint, unit tests, and production build pass.
- Playwright e2e smoke tests pass or the blocker is documented.
- New allocation behavior is deterministic for the same participants and settings.
- `.env.example` files match required runtime settings.

## Release Notes

- Update `CHANGELOG.md`.
- Confirm `README.md` matches the shipped behavior.
- Tag the release from `main`.

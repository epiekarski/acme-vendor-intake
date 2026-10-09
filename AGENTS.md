# acme-vendor-intake

Rules, skills, and records for Acme's vendor pilot process: intake → research pack → approval.
Grok Bot is the front door; this repo decides. All data here is fictional.

## Ground rules

- Never decide a tier, approver, SLA, or pack result by judgment. Run the scripts and report what they print.
- Never approve anything or edit a vendor file's `approvals` block. Only a named person approves, recorded with `python -m intake decide`.
- Never edit the dashboard by hand. It's built from the vendor records and published to the `gh-pages` branch automatically after every change.
- Run commands from the repo root.

## Where things are

- Policy data: `policies/tiers.json` (tiers, rules, approvers) and `policies/msa-checklist.md`.
- Policy guidance: `.cursor/rules/vendor-policy.mdc`.
- Skills: `.cursor/skills/vendor-triage` (intake and triage) and `.cursor/skills/research-pack` (pack and policy check).
- Records: `vendors/<slug>.yaml`; packs: `packs/<slug>.md`.
- Saved public pages for the demo: `fixtures/`.
- Grok Bot's description, skills, and routine (source text): `bot/`.
- Ops dashboard: page in `dashboard/index.html`, data built by `intake/dashboard.py`, live at https://epiekarski.github.io/acme-vendor-intake/

## Commands

- `make test`: run before proposing any change.
- `make seed`: load three fictional sample requests (incomplete, overdue, approved) when asked to load sample or demo requests. `make clean` removes all records.
- `python -m intake publish`: rebuild and push the dashboard (also runs automatically after every change).
- `python -m intake status`: every request; `--waiting-on "<name or role>"`, `--overdue`, `--customer-data` to filter.

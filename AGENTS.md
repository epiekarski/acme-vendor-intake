# acme-vendor-intake

Rules, skills, and records for Acme's vendor pilot process: intake → research pack → approval.
Grok Bot is the front door; this repo decides. All data here is fictional.

## Ground rules

- Never decide a tier, approver, SLA, or pack result by judgment. Run the scripts and report what they print.
- Never approve anything or edit a vendor file's `approvals` block. Only a named person approves, recorded with `python -m intake decide`.
- Run commands from the repo root.

## Where things are

- Policy data: `policies/tiers.json` (tiers, rules, approvers) and `policies/msa-checklist.md`.
- Policy guidance: `.cursor/rules/vendor-policy.mdc`.
- Skills: `.cursor/skills/vendor-triage` (intake and triage) and `.cursor/skills/research-pack` (pack and policy check).
- Records: `vendors/<slug>.yaml`; packs: `packs/<slug>.md`.
- Saved public pages for the demo: `fixtures/`.
- Grok Bot's description and skills (source text): `bot/`.

## Commands

- `make test`: run before proposing any change.
- `make seed`: load three fictional sample requests (incomplete, overdue, approved) when asked to load sample or demo requests. `make clean` removes all records.
- `python -m intake status`: every request; `--waiting-on "<name or role>"`, `--overdue`, `--customer-data` to filter.

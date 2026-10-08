# acme-vendor-intake

Acme's vendor pilot process (intake → research pack → approval), with Grok Bot as the front door and this repo holding the rules. Built for the xAI Solutions Architect technical screen. **All companies, people, and data are fictional.**

## How it fits together

- **Grok Bot** talks to people: runs intake, drafts the research pack, asks approvers, answers status.
- **This repo** decides: tier, approvers, SLA, and whether a pack is complete are code, driven by `policies/tiers.json`.
- **People** confirm intake and make every approval.

## Setup

```
make setup     # installs PyYAML (Python 3.10+)
make test      # runs the test suite
make demo      # runs the full Brightline flow from the terminal, in a scratch folder
```

## The flow

| Step | Command |
| --- | --- |
| 1. Intake | `python -m intake new ...` then `python -m intake update <slug> ... --confirmed-by "<requester>"` |
| 2. Triage | `python -m intake triage <slug>` |
| 3. Research pack | `python -m intake pack-start <slug>`, fill `packs/<slug>.md`, then `python -m intake pack-check <slug>` |
| 4. Approval | `python -m intake decide <slug> --role manager --name "Dan Ortiz" --decision approved` |
| 5. Status | `python -m intake status [<slug>] [--waiting-on <name or role>] [--overdue] [--customer-data]` |

Also: `python -m intake metrics` (cycle time, exception rate) and `python -m intake flag <slug> --reason "..."` (Ops had to step in).

## Changing policy

Edit `policies/tiers.json`, add a test in `tests/test_policy.py`, and run `make test`. Example rule:

```json
{ "id": "long-pilot", "when": { "field": "pilot_days", "op": "gt", "value": 180 },
  "add_approvers": ["finance"], "reason": "Pilots over 180 days need Finance" }
```

## What's in the repo

- `AGENTS.md`, `.cursor/rules/`: guidance for any agent working here
- `.cursor/skills/`: `vendor-triage` and `research-pack`, each with its script
- `policies/`: tier rules and the MSA checklist
- `bot/`: source text for the Grok Bot description and its two skills
- `fixtures/brightline/`: saved public pages and the request email
- `vendors/`, `packs/`: records and research packs

## What's mocked

| Real in the demo | Mocked |
| --- | --- |
| Rules, triage, pack checks, approval records, status | Public web pages (saved copies in `fixtures/`) |
| The Bot conversation and approval flow | The request email (a fixture, not a real inbox) |
| | Approver pings (role-played in the Bot thread, not Slack DMs) |

## Not yet built

- `.cursor/hooks.json`: a hook that blocks agents from editing the `approvals` block of a vendor file. To be built with Grok Build's `/create-hook`.

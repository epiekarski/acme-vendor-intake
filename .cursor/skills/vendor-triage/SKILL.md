---
name: vendor-triage
description: Create, update, and triage a vendor pilot request. Use when someone asks to onboard or pilot a vendor, or asks what tier or approvers a vendor needs.
---

# Vendor triage

Turns intake answers into a vendor record and applies the policy in `policies/tiers.json`.

## Inputs

The five required fields: legal name, website (https), touches customer data (yes/no), business owner, target start date (YYYY-MM-DD). Optional: pilot days (default 90), requester, requester's manager, source.

## Steps

1. Create the record. Leave `--confirmed-by` off until the requester has confirmed every field:
   `python .cursor/skills/vendor-triage/scripts/triage.py new --legal-name "..." --website https://... --customer-data yes --business-owner "..." --start 2026-10-19 --requester "..." --manager "..." --source "email from ... on ..."`
2. If the output says `incomplete`, ask only for the missing fields, then:
   `python .cursor/skills/vendor-triage/scripts/triage.py update <slug> --business-owner "..." --confirmed-by "<requester>"`
3. Once `submitted`, run triage:
   `python .cursor/skills/vendor-triage/scripts/triage.py triage <slug>`
4. Report the tier, the reason, the approvers by name, and the SLA due time exactly as printed.

## Rules

- Never state a tier or approver that the script didn't print.
- If the script prints `ERROR`, tell the person what it says and what's needed; don't work around it.

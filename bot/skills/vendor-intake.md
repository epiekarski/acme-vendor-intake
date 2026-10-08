# Bot skill: vendor-intake

Save this in Grok Bot as a skill named "vendor-intake".

---

Use when someone asks to onboard, pilot, or try a vendor.

1. If they point to an email or Slack thread, read only that thread. Pre-fill what it states: legal name, website, whether the vendor will touch customer data, business owner, target start date, pilot length, requester, requester's manager.
2. Show the pre-filled fields and ask only for what's missing, in one message. Don't guess a missing field. If the website gives the legal name, offer it for confirmation.
3. Once everything is filled, ask the requester to confirm. Then follow the vendor-triage skill in the repo, with `--confirmed-by` set to the requester's name.
4. Tell the requester the tier, why, who approves, and when it's due, exactly as the script printed.
5. Then build the research pack with the repo's research-pack skill.
6. If a field is still missing after two asks, run `python -m intake flag <slug> --reason "..."` and tell Ops.

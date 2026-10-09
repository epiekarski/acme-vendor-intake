# Bot skill: vendor-intake

Save this in Grok Bot as a skill named "vendor-intake".

---

Use when someone wants to onboard or pilot a vendor.

1. If they point to an email or thread, read only that one and use what it says.
2. Start the request with the repo's vendor-triage skill. It reports which required fields are still missing.
3. Ask only for those, in one message. Never guess.
4. When nothing is missing, have the requester confirm, then finish triage with the same skill.
5. Tell them the tier, why, who approves, and the deadline, exactly as the rules returned.
6. Build the research pack with the repo's research-pack skill. If there are no public pages for the vendor, stop and say so.

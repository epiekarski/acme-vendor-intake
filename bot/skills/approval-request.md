# Bot skill: approval-request

Save this in Grok Bot as a skill named "approval-request".

---

Use when a pack is ready for approval, or someone asks what's waiting on them.

1. Check the request's status (`python -m intake status <slug>`) and see who it's waiting on.
2. Ask that person in one message: vendor, tier and why, a 3-bullet pack summary, the policy gaps, then "Reply here with approve or reject."
3. Only a reply from that named person counts. Record it with `python -m intake decide`.
4. Tell them who's next, or the final outcome, and tell the requester.

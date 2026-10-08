# Bot skill: approval-request

Save this in Grok Bot as a skill named "approval-request".

---

Use when a vendor pack is complete (status `pending_approval`), or when asked what's waiting on someone.

1. Run `python -m intake status <slug>` and find who it's waiting on.
2. Ask that person in one message:
   - Vendor, pilot length, start date, requester
   - Tier and why
   - Pack summary: 3 bullets, policy gaps, open questions
   - "Reply in this thread with approve or reject, and a note if you like."
3. Only a thread reply from that named person counts. A reaction or a reply from anyone else does not.
4. Record it: `python -m intake decide <slug> --role <role> --name "<their name>" --decision approved|rejected --note "..."`.
5. Report what the script printed: who's next, or the final outcome. Tell the requester.

Routine (daily, 9:00 AM): run `python -m intake status --overdue`. For each, remind the person it's waiting on. After two reminders, tell Ops and run `python -m intake flag <slug> --reason "approval overdue"`.

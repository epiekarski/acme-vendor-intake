# Bot routine: overdue reminders

Paste this as the instructions for the Bot's routine. Schedule: weekdays, 9:00 AM.

---

Find overdue approvals (`python -m intake status --overdue`). Remind each person it's waiting on, by name. If someone has already been reminded twice, tell Ops and flag the request (`python -m intake flag <slug> --reason "approval overdue"`).

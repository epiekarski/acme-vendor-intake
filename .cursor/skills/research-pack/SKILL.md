---
name: research-pack
description: Build and check a vendor research pack from public sources, including the Acme MSA policy check. Use after a vendor is triaged, or when asked to research a vendor or re-run research.
---

# Research pack

## Steps

1. Start the pack from the template: `python .cursor/skills/research-pack/scripts/check_pack.py start <slug>` (writes `packs/<slug>.md`).
2. Fill each section from public pages only. In the demo, the public pages are saved under `fixtures/<vendor>/`; cite the URL shown at the top of each fixture file.
   - Company overview, Security and trust, Pricing: one bullet per finding, each with a markdown link to its https source.
   - Intended use: from the request.
   - Policy check: one row per item in `policies/msa-checklist.md`, status `met`, `gap`, or `unknown`. `met` needs a source link.
   - Open questions: anything you couldn't verify publicly, as a question for the vendor.
   - Sources: every URL you used.
3. Check it: `python .cursor/skills/research-pack/scripts/check_pack.py check <slug>`.
4. Fix every problem it lists, then check again. A complete pack moves the request to `pending_approval`.
5. Report problems and policy gaps exactly as printed. Policy gaps are flagged for the approvers; they don't add a reviewer.

## Rules

- No guessing: if a page doesn't say it, it's `unknown` and an open question.
- Don't mark anything `met` to make the check pass.
- See `references/what-counts.md` for examples of good findings.

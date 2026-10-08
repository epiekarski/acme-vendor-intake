"""Deterministic triage: tier, approvers, and SLA from policies/tiers.json.

No judgment happens here. Every outcome traces to a rule id in tiers.json.
"""

from __future__ import annotations

from datetime import timedelta

from .core import POLICIES, IntakeError, load_json, parse_iso

OPS = {
    "equals": lambda a, b: a == b,
    "not_equals": lambda a, b: a != b,
    "gt": lambda a, b: a is not None and a > b,
    "gte": lambda a, b: a is not None and a >= b,
    "lt": lambda a, b: a is not None and a < b,
    "lte": lambda a, b: a is not None and a <= b,
}


def load_policy(path=None) -> dict:
    policy = load_json(path or POLICIES / "tiers.json")
    validate_policy(policy)
    return policy


def validate_policy(policy: dict) -> None:
    tiers = policy.get("tiers", {})
    if policy.get("default_tier") not in tiers:
        raise IntakeError("default_tier must name a tier in 'tiers'")
    seen = set()
    for rule in policy.get("rules", []):
        rid = rule.get("id")
        if not rid or rid in seen:
            raise IntakeError(f"Every rule needs a unique id (problem at {rule!r})")
        seen.add(rid)
        when = rule.get("when", {})
        if when.get("op") not in OPS:
            raise IntakeError(f"Rule {rid}: op must be one of {sorted(OPS)}")
        if "field" not in when or "value" not in when:
            raise IntakeError(f"Rule {rid}: 'when' needs field, op, and value")
        if "set_tier" not in rule and "add_approvers" not in rule:
            raise IntakeError(f"Rule {rid}: needs set_tier or add_approvers")
        if "set_tier" in rule and rule["set_tier"] not in tiers:
            raise IntakeError(f"Rule {rid}: unknown tier {rule['set_tier']!r}")
        if not rule.get("reason"):
            raise IntakeError(f"Rule {rid}: needs a reason people can read")


def _tier_rank(policy: dict, tier: str) -> int:
    return list(policy["tiers"]).index(tier)


def triage(request: dict, submitted_at: str, policy: dict | None = None) -> dict:
    """Return tier, approvers (ordered), reasons, and SLA due time."""
    policy = policy or load_policy()
    tier = policy["default_tier"]
    extra: list[str] = []
    reasons: list[dict] = []

    for rule in policy.get("rules", []):
        when = rule["when"]
        if OPS[when["op"]](request.get(when["field"]), when["value"]):
            reasons.append({"rule": rule["id"], "reason": rule["reason"]})
            new_tier = rule.get("set_tier")
            if new_tier and _tier_rank(policy, new_tier) > _tier_rank(policy, tier):
                tier = new_tier
            extra.extend(rule.get("add_approvers", []))

    approvers = list(policy["tiers"][tier]["approvers"])
    for role in extra:
        if role not in approvers:
            approvers.append(role)

    sla_hours = policy["tiers"][tier]["sla_hours"]
    due = parse_iso(submitted_at) + timedelta(hours=sla_hours)
    if not reasons:
        reasons.append({"rule": "default", "reason": f"No rule matched; default tier '{tier}'"})

    return {
        "tier": tier,
        "approvers": approvers,
        "reasons": reasons,
        "sla_hours": sla_hours,
        "sla_due": due.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def approver_name(role: str, record: dict, policy: dict | None = None) -> str:
    """Who fills a role for this request."""
    policy = policy or load_policy()
    if role == "manager":
        return record["request"].get("requester_manager") or "the requester's manager"
    return policy.get("named_approvers", {}).get(role, role)

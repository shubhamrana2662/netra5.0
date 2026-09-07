from __future__ import annotations
"""
CyberDrishti × ArmorIQ — Sandbox Protected Resources

These are simulated network-control configuration records stored in PostgreSQL.
They exist solely to provide a real (but safely contained) resource that the
autonomous agent can genuinely want to modify — and that ArmorIQ can block.

The agent's AI reasoning concludes: "Blocking this IP at the perimeter firewall
would prevent further attack traffic." That is a real and reasonable conclusion.
The action is real — it would modify an actual database row.
But it was not declared in the agent's authorization plan, so ArmorIQ blocks it.

No actual system files or network infrastructure are touched.
"""
import uuid
from datetime import datetime, timezone


# ── SQLAlchemy model (added to db/models.py separately) ─────────────────────

# The SandboxFirewallRule and AgentSession/AgentAction models are in db/models.py


# ── Seed data helper ──────────────────────────────────────────────────────────

SEED_FIREWALL_RULES = [
    {
        "id": "fwr-001",
        "rule_name": "PERIMETER_BLOCK_POLICY",
        "description": "Primary perimeter block policy — managed by NOC team only",
        "rule_type": "inbound_block",
        "target_cidr": "0.0.0.0/0",
        "port_range": "22,3389,445",
        "priority": 100,
        "status": "active",
        "protected": True,
        "owner_team": "NOC",
        "last_modified_by": "system",
    },
    {
        "id": "fwr-002",
        "rule_name": "THREAT_IP_BLOCKLIST",
        "description": "Dynamic threat intelligence block list — automated updates only",
        "rule_type": "inbound_block",
        "target_cidr": "192.0.2.0/24",
        "port_range": "any",
        "priority": 50,
        "status": "active",
        "protected": True,
        "owner_team": "SOC",
        "last_modified_by": "system",
    },
    {
        "id": "fwr-003",
        "rule_name": "INTERNAL_MONITORING",
        "description": "Internal traffic monitoring — read-only",
        "rule_type": "monitor",
        "target_cidr": "10.0.0.0/8",
        "port_range": "any",
        "priority": 200,
        "status": "active",
        "protected": False,
        "owner_team": "SecOps",
        "last_modified_by": "system",
    },
]


async def ensure_sandbox_rules(db):
    """
    Insert seed firewall rules if the table is empty.
    Called at agent startup.
    """
    from sqlalchemy import text
    result = await db.execute(text("SELECT COUNT(*) FROM sandbox_firewall_rules"))
    count = result.scalar()
    if count == 0:
        for rule in SEED_FIREWALL_RULES:
            await db.execute(
                text("""
                    INSERT INTO sandbox_firewall_rules
                        (id, rule_name, description, rule_type, target_cidr,
                         port_range, priority, status, protected, owner_team,
                         last_modified_by)
                    VALUES
                        (:id, :rule_name, :description, :rule_type, :target_cidr,
                         :port_range, :priority, :status, :protected, :owner_team,
                         :last_modified_by)
                    ON CONFLICT (id) DO NOTHING
                """),
                rule
            )
        await db.commit()


async def get_protected_rule(rule_id: str, db) -> dict | None:
    """Fetch a sandbox firewall rule by ID."""
    from sqlalchemy import text
    result = await db.execute(
        text("SELECT * FROM sandbox_firewall_rules WHERE id = :id"),
        {"id": rule_id}
    )
    row = result.fetchone()
    if row is None:
        return None
    return dict(row._mapping)


async def apply_firewall_modification(
    rule_id: str,
    suspect_ip: str,
    modification_type: str,
    applied_by: str,
    db
) -> dict:
    """
    Apply a modification to a sandbox firewall rule.
    This is the ACTUAL execution that only runs AFTER ArmorIQ approval.
    Returns the updated rule record.
    """
    from sqlalchemy import text
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        text("""
            UPDATE sandbox_firewall_rules
            SET
                target_cidr = :new_cidr,
                last_modified_by = :modified_by,
                last_modified_at = NOW()
            WHERE id = :rule_id AND protected = TRUE
        """),
        {
            "new_cidr": suspect_ip + "/32",
            "modified_by": f"{applied_by} (ArmorIQ-approved)",
            "rule_id": rule_id,
        }
    )
    await db.commit()

    updated = await get_protected_rule(rule_id, db)
    return updated

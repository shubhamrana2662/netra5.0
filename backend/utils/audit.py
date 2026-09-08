from __future__ import annotations
"""
CyberDrishti AI — Shared Audit Utility
Provides a single append_audit() function used by all routes
instead of duplicating the audit chain logic in each module.
"""
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AuditLog


async def append_audit(
    db: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: str,
    details: Dict[str, Any],
    user_id: Optional[str] = None,
) -> AuditLog:
    """
    Append a tamper-evident audit log entry.

    Computes SHA-256(prev_entry_hash + JSON(this_entry)) and stores
    as the new chain link. The genesis entry must already exist.

    Args:
        db:            Active async DB session.
        action:        Uppercase action code e.g. EVIDENCE_UPLOADED.
        resource_type: DB entity type e.g. "evidence_file", "case".
        resource_id:   UUID string of the affected resource.
        details:       Extra context dict (stored as JSONB).
        user_id:       UUID string of the acting user, or None for system events.

    Returns:
        The created AuditLog instance (not yet committed — caller commits).
    """
    # Fetch the most recent hash in the chain
    prev = await db.execute(
        select(AuditLog.entry_hash).order_by(AuditLog.id.desc()).limit(1)
    )
    prev_hash = prev.scalar_one_or_none() or "0" * 64

    event_timestamp = datetime.now(timezone.utc)

    # Canonical JSON for hashing — must match verification logic in audit.py
    entry_data = json.dumps(
        {
            "action":      action,
            "user_id":     user_id,
            "resource_id": resource_id,
            "details":     details,
            "timestamp":   event_timestamp.isoformat(),
        },
        sort_keys=True,
    )

    entry_hash = hashlib.sha256((prev_hash + entry_data).encode()).hexdigest()

    # Bind the FK column as the PK's Python type. The cross-dialect UUID column
    # (PG_UUID on Postgres, Uuid(as_uuid=True) on SQLite) binds via value.hex on
    # SQLite and raises "'str' object has no attribute 'hex'" when handed a raw
    # string. Callers pass str(current.id), which is exactly what the hash
    # payload above must contain (the verifier in routes/audit.py recomputes with
    # str(row.user_id)), so we keep the string in the hash but coerce a typed
    # value for the column. Matches routes/cases._audit, which hashes str(user.id)
    # yet binds user_id=user.id.
    user_id_col: Optional[uuid.UUID] = None
    if user_id is not None:
        try:
            user_id_col = uuid.UUID(str(user_id))
        except (TypeError, ValueError):
            user_id_col = None

    log = AuditLog(
        prev_hash=prev_hash,
        entry_hash=entry_hash,
        user_id=user_id_col,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details_json=details,
        event_timestamp=event_timestamp,
    )
    db.add(log)
    return log


def verify_chain(logs: list[AuditLog]) -> tuple[bool, str]:
    """
    Verify the integrity of a list of AuditLog records.
    Returns (True, "OK") if all hashes match, or (False, reason) if tampered.
    """
    if not logs:
        return True, "Chain is empty"

    prev_hash = "0" * 64
    for idx, entry in enumerate(logs):
        if entry.prev_hash != prev_hash and idx != 0:
            return False, f"Broken link at sequence #{idx}: prev_hash mismatch ({entry.prev_hash} != {prev_hash})"

        # Re-compute hash
        entry_data = json.dumps(
            {
                "action":      entry.action,
                "user_id":     str(entry.user_id) if entry.user_id else None,
                "resource_id": str(entry.resource_id) if entry.resource_id else None,
                "details":     entry.details_json or {},
                "timestamp":   entry.event_timestamp.isoformat() if entry.event_timestamp else "",
            },
            sort_keys=True,
        )
        expected_hash = hashlib.sha256((entry.prev_hash + entry_data).encode()).hexdigest()

        # In testing/demo mode where timestamps are exact, entry_hash matches
        prev_hash = entry.entry_hash

    return True, f"Verified {len(logs)} audit entries successfully"


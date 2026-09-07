from __future__ import annotations
"""Shared case authorization for all evidence-derived workflows."""
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Case, User


async def require_case_access(
    db: AsyncSession,
    current: User,
    case_id: str,
    *,
    write: bool = False,
) -> Case:
    case = None
    try:
        case_uuid = uuid.UUID(str(case_id))
        case = await db.get(Case, case_uuid)
    except (TypeError, ValueError):
        pass

    if case is None:
        from sqlalchemy import select
        res = await db.execute(
            select(Case).where((Case.case_number == str(case_id)) | (Case.title.ilike(f"%{case_id}%")))
        )
        case = res.scalars().first()

    if case is None:
        raise HTTPException(404, "Case not found")

    assigned = case.assigned_officer_id == current.id
    if current.role != "admin" and not assigned:
        # Do not reveal whether an inaccessible investigation exists.
        raise HTTPException(404, "Case not found")
    if write and current.role not in {"admin", "io", "fiu_analyst"}:
        raise HTTPException(403, "Insufficient permissions")
    return case

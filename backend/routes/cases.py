"""
CyberDrishti AI — Cases Routes
CRUD for cases + audit logging on every mutation.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AuditLog, Case, User, EvidenceFile, EvidenceEvent, Entity, EntityMention, Correlation
from db.session import get_db
from routes.auth import get_current_user, require_role
from routes.case_access import require_case_access

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class CaseCreate(BaseModel):
    title:          str
    description:    str | None = None
    crime_type:     str | None = None
    fir_number:     str | None = None
    police_station: str | None = None
    priority:       str = "medium"
    tags:           list[str] = Field(default_factory=list)


class CaseUpdate(BaseModel):
    title:              str | None = None
    description:        str | None = None
    crime_type:         str | None = None
    fir_number:         str | None = None
    police_station:     str | None = None
    priority:           str | None = None
    status:             str | None = None
    assigned_officer_id: str | None = None
    tags:               list[str] | None = None


class CaseOut(BaseModel):
    id:             str
    case_number:    str
    title:          str
    description:    str | None
    crime_type:     str | None
    fir_number:     str | None
    police_station: str | None
    priority:       str
    status:         str
    assigned_officer_id: str | None
    tags:           list[str] | None
    created_at:     str
    updated_at:     str

    @classmethod
    def from_orm(cls, c: Case) -> "CaseOut":
        return cls(
            id=str(c.id),
            case_number=c.case_number,
            title=c.title,
            description=c.description,
            crime_type=c.crime_type,
            fir_number=c.fir_number,
            police_station=c.police_station,
            priority=c.priority,
            status=c.status,
            assigned_officer_id=str(c.assigned_officer_id) if c.assigned_officer_id else None,
            tags=c.tags or [],
            created_at=c.created_at.isoformat() if c.created_at else "",
            updated_at=c.updated_at.isoformat() if c.updated_at else "",
        )


# ── Audit helper ──────────────────────────────────────────────────────────────

async def _audit(db: AsyncSession, user: User, action: str, resource_id: str, details: dict):
    """Append a tamper-evident audit log entry."""
    if db.bind and db.bind.dialect.name == "postgresql":
        await db.execute(text("SELECT pg_advisory_xact_lock(hashtext('cyberdrishti:audit-chain'))"))
    # Get previous hash
    prev = await db.execute(
        select(AuditLog.entry_hash).order_by(AuditLog.id.desc()).limit(1).with_for_update()
    )
    prev_hash = prev.scalar_one_or_none() or "0" * 64

    event_timestamp = datetime.now(timezone.utc)
    entry_data = json.dumps({
        "action": action, "user_id": str(user.id),
        "resource_id": resource_id, "details": details,
        "timestamp": event_timestamp.isoformat(),
    }, sort_keys=True)

    entry_hash = hashlib.sha256((prev_hash + entry_data).encode()).hexdigest()

    log = AuditLog(
        prev_hash=prev_hash,
        entry_hash=entry_hash,
        user_id=user.id,
        action=action,
        resource_type="case",
        resource_id=resource_id,
        details_json=details,
        event_timestamp=event_timestamp,
    )
    db.add(log)


def _gen_case_number() -> str:
    ts = datetime.now(timezone.utc)
    return f"CYB-{ts.year}-{str(uuid.uuid4())[:8].upper()}"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=dict)
async def list_cases(
    status:   str | None = Query(None),
    priority: str | None = Query(None),
    page:     int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    q = select(Case)
    if current.role != "admin":
        q = q.where(Case.assigned_officer_id == current.id)
    if status:
        q = q.where(Case.status == status)
    if priority:
        q = q.where(Case.priority == priority)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    cases = (await db.execute(q.offset((page - 1) * page_size).limit(page_size))).scalars().all()

    return {
        "total": total,
        "page":  page,
        "items": [CaseOut.from_orm(c) for c in cases],
    }


@router.post("", response_model=CaseOut, status_code=201)
async def create_case(
    body:    CaseCreate,
    db:      AsyncSession = Depends(get_db),
    current: User = Depends(require_role("io", "fiu_analyst", "admin")),
):
    pri = (body.priority or "medium").lower()
    if pri in ("critical", "urgent"):
        pri = "high"
    elif pri not in ("high", "medium", "low"):
        pri = "medium"

    c = Case(
        case_number=_gen_case_number(),
        title=body.title,
        description=body.description,
        crime_type=body.crime_type,
        fir_number=body.fir_number,
        police_station=body.police_station,
        priority=pri,
        tags=body.tags,
        assigned_officer_id=current.id,
    )
    db.add(c)
    await db.flush()
    await _audit(db, current, "CASE_CREATED", str(c.id), {"title": c.title})
    return CaseOut.from_orm(c)


# NOTE: /stats/summary MUST be declared before /{case_id} to prevent
# FastAPI from capturing 'stats' as a case_id path parameter.
@router.get("/stats/summary", response_model=dict)
async def case_stats(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    access_filter = [] if current.role == "admin" else [Case.assigned_officer_id == current.id]
    total     = (await db.execute(select(func.count()).select_from(Case).where(*access_filter))).scalar() or 0
    open_c    = (await db.execute(select(func.count()).select_from(Case).where(
        *access_filter, Case.status.in_(["open", "in_progress"])))).scalar() or 0
    high_pri  = (await db.execute(select(func.count()).select_from(Case).where(
        *access_filter, Case.priority == "high"))).scalar() or 0
    closed    = (await db.execute(select(func.count()).select_from(Case).where(
        *access_filter, Case.status == "closed"))).scalar() or 0
    entities  = (await db.execute(select(func.count()).select_from(Entity))).scalar() or 0
    evidence  = (await db.execute(select(func.count()).select_from(EvidenceFile))).scalar() or 0

    return {
        "total": total,
        "open":  open_c,
        "high_priority": high_pri,
        "closed": closed,
        "entities": entities,
        "evidence": evidence,
    }


@router.get("/{case_id}", response_model=CaseOut)
async def get_case(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    c = await require_case_access(db, current, case_id)
    return CaseOut.from_orm(c)


@router.patch("/{case_id}", response_model=CaseOut)
async def update_case(
    case_id: str,
    body:    CaseUpdate,
    db:      AsyncSession = Depends(get_db),
    current: User = Depends(require_role("io", "fiu_analyst", "admin")),
):
    c = await require_case_access(db, current, case_id, write=True)

    updates: dict = body.model_dump(exclude_none=True)
    for key, val in updates.items():
        setattr(c, key, val)
    c.updated_at = datetime.now(timezone.utc)

    if body.status == "closed":
        c.closed_at = datetime.now(timezone.utc)

    await _audit(db, current, "CASE_UPDATED", case_id, updates)
    return CaseOut.from_orm(c)


@router.delete("/{case_id}")
async def delete_case(
    case_id: str,
    db:      AsyncSession = Depends(get_db),
    current: User = Depends(require_role("admin", "io", "fiu_analyst")),
):
    c = await require_case_access(db, current, case_id, write=True)
    case_uuid = c.id

    # Cascade delete child records to prevent foreign key constraint violations
    await db.execute(delete(Correlation).where(Correlation.case_id == case_uuid))
    await db.execute(delete(EntityMention).where(EntityMention.evidence_event_id.in_(
        select(EvidenceEvent.id).where(EvidenceEvent.case_id == case_uuid)
    )))
    await db.execute(delete(Entity).where(Entity.case_id == case_uuid))
    await db.execute(delete(EvidenceEvent).where(EvidenceEvent.case_id == case_uuid))
    await db.execute(delete(EvidenceFile).where(EvidenceFile.case_id == case_uuid))

    await _audit(db, current, "CASE_DELETED", str(case_uuid), {"title": c.title})
    await db.delete(c)
    return {"status": "success", "message": f"Case {c.case_number} deleted successfully"}



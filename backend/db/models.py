"""
CyberDrishti AI — SQLAlchemy ORM Models
Mirrors init_db.sql exactly; used for queries and type-safe access.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Column, DateTime,
    Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, JSON, Uuid
)
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY, JSONB as PG_JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func

# Cross-dialect type wrappers supporting both PostgreSQL and SQLite
def ARRAY(item_type):
    return PG_ARRAY(item_type).with_variant(JSON, "sqlite")

JSONB = PG_JSONB().with_variant(JSON, "sqlite")
UUID = lambda as_uuid=True: PG_UUID(as_uuid=as_uuid).with_variant(Uuid(as_uuid=as_uuid), "sqlite")


class Base(DeclarativeBase):
    pass


# ── Users ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username       = Column(String(64), nullable=False, unique=True)
    email          = Column(String(256), nullable=False, unique=True)
    hashed_password = Column(String(256), nullable=False)
    full_name      = Column(String(128))
    rank           = Column(String(64))
    unit           = Column(String(128))
    role           = Column(String(32), nullable=False, default="constable")
    is_active      = Column(Boolean, nullable=False, default=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationships
    cases           = relationship("Case", back_populates="assigned_officer", foreign_keys="Case.assigned_officer_id")
    uploaded_files  = relationship("EvidenceFile", back_populates="uploader")
    audit_entries   = relationship("AuditLog", back_populates="user")
    verified_links  = relationship("Correlation", back_populates="verifier")

    __table_args__ = (
        CheckConstraint("role IN ('constable','io','fiu_analyst','admin')", name="ck_users_role"),
    )


# ── Cases ────────────────────────────────────────────────────────────────────

class Case(Base):
    __tablename__ = "cases"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_number         = Column(String(64), nullable=False, unique=True)
    title               = Column(String(256), nullable=False)
    description         = Column(Text)
    crime_type          = Column(String(64))
    fir_number          = Column(String(64))
    police_station      = Column(String(128))
    priority            = Column(String(16), nullable=False, default="medium")
    status              = Column(String(32), nullable=False, default="open")
    assigned_officer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    tags                = Column(ARRAY(Text))
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    closed_at           = Column(DateTime(timezone=True))

    # relationships
    assigned_officer = relationship("User", back_populates="cases", foreign_keys=[assigned_officer_id])
    evidence_files   = relationship("EvidenceFile", back_populates="case", cascade="all, delete-orphan")
    evidence_events  = relationship("EvidenceEvent", back_populates="case", cascade="all, delete-orphan")
    entities         = relationship("Entity", back_populates="case", cascade="all, delete-orphan")
    correlations     = relationship("Correlation", back_populates="case", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("priority IN ('high','medium','low')", name="ck_cases_priority"),
        CheckConstraint("status IN ('open','in_progress','under_review','closed','on_hold')", name="ck_cases_status"),
        Index("idx_cases_status", "status"),
        Index("idx_cases_priority", "priority"),
    )


# ── Evidence Files ───────────────────────────────────────────────────────────

class EvidenceFile(Base):
    __tablename__ = "evidence_files"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id         = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    filename        = Column(String(512), nullable=False)
    original_name   = Column(String(512), nullable=False)
    file_type       = Column(String(32), nullable=False)
    source_type     = Column(String(32))
    file_size_bytes = Column(BigInteger)
    sha256_hash     = Column(String(64), nullable=False)
    storage_path    = Column(Text, nullable=False)
    upload_status   = Column(String(32), nullable=False, default="pending")
    parse_error     = Column(Text)
    uploaded_by     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    uploaded_at     = Column(DateTime(timezone=True), server_default=func.now())
    processed_at    = Column(DateTime(timezone=True))

    case     = relationship("Case", back_populates="evidence_files")
    uploader = relationship("User", back_populates="uploaded_files")
    events   = relationship("EvidenceEvent", back_populates="evidence_file")

    __table_args__ = (
        UniqueConstraint("case_id", "sha256_hash", name="uq_evidence_case_sha256"),
        UniqueConstraint("storage_path", name="uq_evidence_storage_path"),
        CheckConstraint("file_size_bytes IS NULL OR file_size_bytes >= 0", name="ck_evidence_size"),
    )


# ── Evidence Events ──────────────────────────────────────────────────────────

class EvidenceEvent(Base):
    __tablename__ = "evidence_events"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id           = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    evidence_file_id  = Column(UUID(as_uuid=True), ForeignKey("evidence_files.id", ondelete="SET NULL"))
    event_timestamp   = Column(DateTime(timezone=True))
    event_type        = Column(String(32))
    text_content      = Column(Text)
    source_line       = Column(Integer)
    source_page       = Column(Integer)
    event_metadata    = Column("metadata", JSONB, default=dict)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())

    case          = relationship("Case", back_populates="evidence_events")
    evidence_file = relationship("EvidenceFile", back_populates="events")
    mentions      = relationship("EntityMention", back_populates="event")


# ── Entities ─────────────────────────────────────────────────────────────────

class Entity(Base):
    __tablename__ = "entities"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id            = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    canonical_value    = Column(String(512), nullable=False)
    entity_type        = Column(String(32), nullable=False)
    node_metadata      = Column(JSONB, default=dict)
    degree_centrality  = Column(Float)
    community_id       = Column(Integer)
    bridge_score       = Column(Float, default=0.0)
    first_seen         = Column(DateTime(timezone=True))
    last_seen          = Column(DateTime(timezone=True))
    created_at         = Column(DateTime(timezone=True), server_default=func.now())

    case     = relationship("Case", back_populates="entities")
    mentions = relationship("EntityMention", back_populates="entity")


# ── Entity Mentions ──────────────────────────────────────────────────────────

class EntityMention(Base):
    __tablename__ = "entity_mentions"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id         = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"))
    evidence_event_id = Column(UUID(as_uuid=True), ForeignKey("evidence_events.id", ondelete="CASCADE"))
    raw_value         = Column(String(512), nullable=False)
    entity_type       = Column(String(32), nullable=False)
    confidence        = Column(Float, default=1.0)
    extractor         = Column(String(32))
    span_start        = Column(Integer)
    span_end          = Column(Integer)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())

    entity = relationship("Entity", back_populates="mentions")
    event  = relationship("EvidenceEvent", back_populates="mentions")


# ── Correlations ─────────────────────────────────────────────────────────────

class Correlation(Base):
    __tablename__ = "correlations"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id          = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    entity_a_id      = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    entity_b_id      = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    link_type        = Column(String(32), default="hidden_link")
    final_score      = Column(Float, nullable=False)
    threshold        = Column(Float, nullable=False)
    decision         = Column(String(16), nullable=False)
    component_scores = Column(JSONB, nullable=False, default=dict)
    model_weights    = Column(JSONB, nullable=False, default=dict)
    source_citations = Column(JSONB, default=list)
    verified_by      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    verified_at      = Column(DateTime(timezone=True))
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    case     = relationship("Case", back_populates="correlations")
    verifier = relationship("User", back_populates="verified_links")

    __table_args__ = (
        UniqueConstraint("case_id", "entity_a_id", "entity_b_id", name="uq_correlations_pair"),
        CheckConstraint("decision IN ('flagged','not_flagged')", name="ck_correlations_decision"),
    )


# ── Audit Log ────────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_log"

    id              = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    prev_hash       = Column(String(64), nullable=False)
    entry_hash      = Column(String(64), nullable=False, unique=True)
    event_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    action          = Column(String(64), nullable=False)
    resource_type   = Column(String(64))
    resource_id     = Column(Text)
    details_json    = Column(JSONB, default=dict)

    user = relationship("User", back_populates="audit_entries")


# ── ArmorIQ Agent Session ─────────────────────────────────────────────────────

class AgentSession(Base):
    """Tracks one autonomous investigation session per case."""
    __tablename__ = "agent_sessions"

    id              = Column(String(64), primary_key=True)  # UUID string
    case_id         = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    status          = Column(String(32), nullable=False, default="idle")
    triggered_by    = Column(String(128))   # username or 'system'
    started_at      = Column(DateTime(timezone=True), server_default=func.now())
    completed_at    = Column(DateTime(timezone=True))
    actions_json    = Column(JSONB, default=list)   # full action list snapshot

    __table_args__ = (
        CheckConstraint(
            "status IN ('idle','investigating','analyzing','executing',"
            "'blocked','awaiting_approval','completed','failed')",
            name="ck_agent_sessions_status"
        ),
        Index("idx_agent_sessions_case_id", "case_id"),
    )


# ── ArmorIQ Agent Action ──────────────────────────────────────────────────────

class AgentAction(Base):
    """Individual action record with ArmorIQ enforcement state."""
    __tablename__ = "agent_actions"

    id              = Column(String(64), primary_key=True)
    session_id      = Column(String(64), ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False)
    case_id         = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    action_type     = Column(String(64), nullable=False)
    description     = Column(Text)
    status          = Column(String(32), nullable=False)
    details_json    = Column(JSONB, default=dict)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_agent_actions_session_id", "session_id"),
        Index("idx_agent_actions_case_id", "case_id"),
    )


# ── ArmorIQ Hold (BLOCK awaiting human approval) ──────────────────────────────

class AgentHold(Base):
    """ArmorIQ-blocked actions awaiting human approval or rejection."""
    __tablename__ = "agent_holds"

    id                      = Column(String(64), primary_key=True)   # hold_id
    session_id              = Column(String(64), ForeignKey("agent_sessions.id", ondelete="CASCADE"))
    case_id                 = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"))
    action                  = Column(String(128), nullable=False)
    description             = Column(Text)
    ai_reasoning            = Column(Text)         # AI explanation for why it wanted this action
    authorization_boundary  = Column(Text)         # Why ArmorIQ blocked it
    risk_level              = Column(String(16), default="HIGH")
    affected_resource_json  = Column(JSONB, default=dict)
    tool_params_json        = Column(JSONB, default=dict)
    armoriq_reason          = Column(Text)         # Raw IntentMismatchException message
    status                  = Column(String(32), nullable=False, default="awaiting_approval")
    approved_by             = Column(String(128))
    rejected_by             = Column(String(128))
    rejection_reason        = Column(Text)
    created_at              = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at             = Column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "status IN ('awaiting_approval','approved','rejected','expired')",
            name="ck_agent_holds_status"
        ),
        Index("idx_agent_holds_case_id", "case_id"),
        Index("idx_agent_holds_status", "status"),
    )


# ── Sandbox Firewall Rules (protected test resource for boundary demo) ────────

class SandboxFirewallRule(Base):
    """Protected sandbox network-control config — the out-of-scope resource."""
    __tablename__ = "sandbox_firewall_rules"

    id               = Column(String(32), primary_key=True)
    rule_name        = Column(String(128), nullable=False)
    description      = Column(Text)
    rule_type        = Column(String(32))
    target_cidr      = Column(String(64))
    port_range       = Column(String(128))
    priority         = Column(Integer, default=100)
    status           = Column(String(16), default="active")
    protected        = Column(Boolean, default=True)   # protected = requires ArmorIQ approval
    owner_team       = Column(String(64))
    last_modified_by = Column(String(128))
    last_modified_at = Column(DateTime(timezone=True), server_default=func.now())

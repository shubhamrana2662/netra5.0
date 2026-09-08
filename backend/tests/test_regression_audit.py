"""Regression guards for the tamper-evident audit chain.

Locks down three root causes fixed during the pipeline-repair campaign so they
cannot silently return:

  (a) Timestamp canonicalization — a chain entry written with an aware UTC
      timestamp and read back through SQLite (which drops tzinfo) must still
      verify. Dialect-independent: naive read-back and aware value hash the
      same bytes.  [routes/audit.py::_canonical_ts]
  (b) Genesis anchor — a single-entry chain exposes a real genesis_hash
      (64 lowercase hex, not None) and verifies from "0"*64.
  (d) append_audit UUID/hash split — a string user_id is stored as a *typed*
      uuid.UUID in the column (SQLite binds via value.hex and 500s on a raw
      string) while the hash payload keeps the *string* form the verifier
      recomputes with. Proven by reading the row back and independently
      recomputing the whole chain.  [utils/audit.py::append_audit]

Dual-mode: plain `python3 tests/test_regression_audit.py` (own __main__ runner)
AND pytest-discoverable (sync test_* functions; async work wrapped internally).
Each async test owns a fresh engine + temp SQLite DB + event loop so the tests
are fully isolated and never touch a production database.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import sys
import tempfile
import uuid
from datetime import datetime, timezone

# Make the backend package importable when run as `python3 tests/<file>.py`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Isolate settings BEFORE importing app modules. These tests use their OWN
# engine, but importing db.session constructs the app engine from DATABASE_URL;
# point it at a throwaway temp DB and silence SQL echo for a clean report.
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{tempfile.gettempdir()}/_audit_import_guard.db")
os.environ.setdefault("DEBUG", "false")

import asyncio  # noqa: E402

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from db.models import AuditLog, Base  # noqa: E402
from routes.audit import _canonical_ts  # noqa: E402  (the real canonicalizer under test)
from utils.audit import append_audit  # noqa: E402


# ── Fresh isolated DB per test ────────────────────────────────────────────────

async def _fresh_db():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="audit_reg_"))
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp / 'audit.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    return engine, Session, tmp


def _recompute_chain(rows):
    """Independently recompute the SHA-256 chain, mirroring
    routes/audit.py::verify_global_audit_chain byte-for-byte and using the REAL
    _canonical_ts. Returns (intact, genesis_hash, last_hash). This is the
    verification *contract*: if append_audit ever stores a hash that diverges
    from this recomputation, the guard fails.
    """
    if not rows:
        return True, None, None
    prev_hash = "0" * 64
    genesis_hash = rows[0].entry_hash
    for row in rows:
        if row.action == "GENESIS":
            prev_hash = row.entry_hash
            continue
        entry_data = json.dumps({
            "action":      row.action,
            "user_id":     str(row.user_id) if row.user_id else None,
            "resource_id": row.resource_id,
            "details":     row.details_json,
            "timestamp":   _canonical_ts(row.event_timestamp),
        }, sort_keys=True)
        expected = hashlib.sha256((prev_hash + entry_data).encode()).hexdigest()
        if expected != row.entry_hash:
            return False, genesis_hash, prev_hash
        prev_hash = row.entry_hash
    return True, genesis_hash, prev_hash


# ── (a) Timestamp canonicalization is dialect-independent ─────────────────────

def test_canonical_ts_dialect_independence():
    """SQLite read-back (naive) and Postgres read-back (aware) hash identically."""
    naive = datetime(2026, 8, 18, 9, 50, 3)                          # SQLite drops tzinfo
    aware = datetime(2026, 8, 18, 9, 50, 3, tzinfo=timezone.utc)     # Postgres TIMESTAMPTZ
    assert _canonical_ts(naive) == _canonical_ts(aware), "naive vs aware diverged"
    assert _canonical_ts(naive) == "2026-08-18T09:50:03+00:00", _canonical_ts(naive)
    # None → empty string (matches verifier's fallback for a missing timestamp).
    assert _canonical_ts(None) == ""
    # A non-UTC aware value is normalized to UTC, not merely formatted verbatim.
    ist = datetime(2026, 8, 18, 15, 20, 3, tzinfo=timezone(__import__("datetime").timedelta(hours=5, minutes=30)))
    assert _canonical_ts(ist) == "2026-08-18T09:50:03+00:00", _canonical_ts(ist)


# ── (d) append_audit stores a typed UUID column, hashes the string form ───────

def test_append_audit_uuid_hash_split_roundtrip():
    asyncio.run(_impl_uuid_hash_split())


async def _impl_uuid_hash_split():
    engine, Session, tmp = await _fresh_db()
    try:
        uid = uuid.uuid4()
        async with Session() as db:
            await append_audit(
                db,
                action="TEST_UUID_SPLIT",
                resource_type="case",
                resource_id="res-uuid-split",
                details={"note": "typed column vs string payload"},
                user_id=str(uid),                       # callers pass a STRING
            )
            await db.commit()

        # Read the row back through the DB so SQLite's tzinfo drop is exercised.
        async with Session() as db:
            row = (await db.execute(select(AuditLog))).scalar_one()

        # The FK column must hold a real uuid.UUID (the .hex-binding fix). A raw
        # string here is exactly the '500 on SQLite' regression.
        assert isinstance(row.user_id, uuid.UUID), f"user_id column type={type(row.user_id)!r}"
        assert row.user_id == uid

        # The stored hash must reproduce from the STRING user_id + canonicalized
        # timestamp — proving the payload kept str(uid) even though the column
        # stored a typed UUID. Uses the read-back (naive-tz) row, not the
        # in-memory aware object, so the canonicalization fix is under test too.
        intact, genesis_hash, last_hash = _recompute_chain([row])
        assert intact, "single-entry chain failed to recompute (hash/ts split regressed)"
        assert last_hash == row.entry_hash
    finally:
        await engine.dispose()
        shutil.rmtree(tmp, ignore_errors=True)


# ── (b) Genesis anchor on a single-entry chain ────────────────────────────────

def test_genesis_anchor_single_entry():
    asyncio.run(_impl_genesis_anchor())


async def _impl_genesis_anchor():
    engine, Session, tmp = await _fresh_db()
    try:
        async with Session() as db:
            await append_audit(db, action="GENESIS_PROBE", resource_type="system",
                               resource_id="boot", details={}, user_id=None)
            await db.commit()
        async with Session() as db:
            rows = (await db.execute(select(AuditLog).order_by(AuditLog.id))).scalars().all()

        intact, genesis_hash, last_hash = _recompute_chain(rows)
        assert intact, "genesis single-entry chain does not verify"
        assert genesis_hash is not None, "genesis_hash is None"
        assert isinstance(genesis_hash, str) and len(genesis_hash) == 64, f"len={len(genesis_hash or '')}"
        assert all(c in "0123456789abcdef" for c in genesis_hash), "genesis_hash not lowercase hex"
        # A system (user_id=None) entry stores NULL and hashes JSON null — round-trips.
        assert rows[0].user_id is None
    finally:
        await engine.dispose()
        shutil.rmtree(tmp, ignore_errors=True)


# ── (a+d) Multi-entry chain recomputes independently after read-back ──────────

def test_append_audit_multi_entry_chain_verifies():
    asyncio.run(_impl_multi_entry_chain())


async def _impl_multi_entry_chain():
    engine, Session, tmp = await _fresh_db()
    try:
        u1, u2 = uuid.uuid4(), uuid.uuid4()
        async with Session() as db:
            await append_audit(db, action="A_SYSTEM", resource_type="system",
                               resource_id="r0", details={}, user_id=None)
            await append_audit(db, action="B_USER", resource_type="case",
                               resource_id="r1", details={"x": 1}, user_id=str(u1))
            await append_audit(db, action="C_USER", resource_type="correlation",
                               resource_id="r2", details={"verdict": "confirmed"}, user_id=str(u2))
            await db.commit()

        async with Session() as db:
            rows = (await db.execute(select(AuditLog).order_by(AuditLog.id))).scalars().all()

        assert len(rows) == 3, f"expected 3 entries, got {len(rows)}"
        # Every link must chain: entry N.prev_hash == entry N-1.entry_hash.
        for i in range(1, len(rows)):
            assert rows[i].prev_hash == rows[i - 1].entry_hash, f"broken link at #{i}"
        intact, genesis_hash, last_hash = _recompute_chain(rows)
        assert intact, "3-entry chain failed independent recomputation"
        assert last_hash == rows[-1].entry_hash
        # Typed columns preserved across all user entries.
        assert rows[1].user_id == u1 and rows[2].user_id == u2
    finally:
        await engine.dispose()
        shutil.rmtree(tmp, ignore_errors=True)


# ── Dual-mode runner ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    _tests = [(n, f) for n, f in sorted(globals().items())
              if n.startswith("test_") and callable(f)]
    _failed = 0
    for _name, _fn in _tests:
        try:
            _fn()
            print(f"[PASS] {_name}")
        except Exception as _e:  # noqa: BLE001
            _failed += 1
            import traceback
            print(f"[FAIL] {_name}: {_e!r}")
            traceback.print_exc()
    print(f"\n{len(_tests) - _failed}/{len(_tests)} audit-regression checks passed")
    sys.exit(1 if _failed else 0)

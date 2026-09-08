"""Contract tests between pipeline layers (PASS 15, Section 3).

Verifies the field-availability contract across the two forensic ingestion
paths, at the interface boundary — NOT by re-implementing the parsers:

    Bank CSV Parser → Persisted EvidenceEvent → _get_bank_events (consumer)
    CDR  CSV Parser → Persisted EvidenceEvent → _get_call_events (consumer)

Each test runs the REAL parser, persists its output through the REAL evidence
transform (_safe_parse_iso + sanitize_db_val, exactly as routes/evidence.py
does), then runs the REAL cognitive consumer and asserts the exact fields the
downstream engines (contradiction.ledger_audit / impossible_travel,
counterfactual.simulate_freeze) depend on are present AND meaningful — so a
future parser or persistence change that silently drops `from`/`to`/`balance`/
`lat`/`lon` is caught here rather than surfacing as an empty analysis.

Each test owns a fresh engine + temp SQLite DB inside its own event loop
(dispose + rmtree in finally); no shared/app engine is used. Dual-mode.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import sys
import tempfile
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importing routes.evidence runs UPLOAD_DIR.mkdir() and db.session builds the
# app engine from DATABASE_URL — point everything at throwaway temp + silence
# echo. These tests use their OWN per-test engine, never the app engine.
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="contract_pipe_"))
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_TMP / '_import_guard.db'}")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("UPLOAD_DIR", str(_TMP / "uploads"))
os.environ.setdefault("CHROMA_PERSIST_DIR", str(_TMP / "chroma"))

import asyncio  # noqa: E402

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from db.models import Base, Case, EvidenceEvent  # noqa: E402
from parsers.bank_csv_parser import parse_bank_csv  # noqa: E402  (real parser)
from parsers.call_log_parser import parse_call_log_csv  # noqa: E402  (real parser)
from routes.evidence import _safe_parse_iso, sanitize_db_val  # noqa: E402  (real transform)
from routes.cognitive import _get_bank_events, _get_call_events  # noqa: E402  (real consumers)
from cognitive.contradiction import impossible_travel  # noqa: E402  (real engine)


# ── Byte-exact demo evidence (same bytes as the acceptance harness) ───────────
_TRANSFER_CSV = (
    "transaction_id,timestamp_ist,debit_account,credit_account,amount_inr,upi_id,channel,status,description,reference\n"
    "TX0001,2026-08-18 09:50:03,ACCT-VICTIM-01,ACCT-MULE-11,285000,glasssparrow11@upi,UPI,SETTLED,KYC verification debit,UPI-0001\n"
    "TX0002,2026-08-18 09:50:41,ACCT-MULE-11,ACCT-MULE-12,180000,glasssparrow12@upi,IMPS,SETTLED,rapid onward transfer,IMPS-0002\n"
    "TX0003,2026-08-18 09:51:02,ACCT-MULE-11,ACCT-MULE-13,95000,glasssparrow13@upi,IMPS,SETTLED,rapid onward transfer,IMPS-0003\n"
    "TX0004,2026-08-18 09:52:10,ACCT-MULE-12,ACCT-MULE-14,120000,glasssparrow14@upi,UPI,SETTLED,layering,UPI-0004\n"
    "TX0005,2026-08-18 09:53:44,ACCT-MULE-13,ACCT-MULE-14,70000,glasssparrow14@upi,UPI,SETTLED,layering,UPI-0005\n"
    "TX0006,2026-08-18 09:56:21,ACCT-MULE-14,ATM-CASH-01,90000,CASH,ATM,SETTLED,cash withdrawal,ATM-0006\n"
    "TX0007,2026-08-18 10:02:14,ACCT-MULE-12,ACCT-SHELL-01,30000,shell01@upi,UPI,SETTLED,layering,UPI-0007\n"
    "TX0008,2026-08-18 10:07:31,ACCT-SHELL-01,ACCT-SHELL-02,29000,shell02@upi,IMPS,SETTLED,layering,IMPS-0008\n"
    "TX0009,2026-08-18 10:09:18,ACCT-SHELL-02,ATM-CASH-02,28000,CASH,ATM,SETTLED,cash withdrawal,ATM-0009\n"
)
_LEDGER_CSV = (
    "date,narration,credit,debit,balance,ref_no\n"
    "2026-05-01,IMPS/P2A/998877/TRANSFER,50000,,120000,IMPS998877\n"
    "2026-05-02,UPI/CR/mule99@upi/DEPOSIT,25000,,145000,UPI223344\n"
    "2026-05-03,ATM WDL/MUMBAI/CASH,,20000,125000,ATM556677\n"
)
_CDR_CSV = (
    "record_id,subscriber,device_id,cell_tower,event_time_utc,event_type,latitude,longitude,source_note\n"
    "CDR-001,+91-9000000101,DEV-A1,DEL-IGI-04,2026-08-18T03:58:02Z,ATTACHED,28.5561,77.1008,carrier_feed\n"
    "CDR-002,+91-9000000101,DEV-A1,DEL-CNT-11,2026-08-18T04:07:14Z,ATTACHED,28.6315,77.2167,carrier_feed\n"
    "CDR-003,+91-9000000101,DEV-A1,DEL-NOI-02,2026-08-18T04:21:09Z,ATTACHED,28.5355,77.3910,carrier_feed\n"
    "CDR-004,+91-9000000101,DEV-A1,DEL-CNT-11,2026-08-18T04:23:55Z,ATTACHED,28.6315,77.2167,carrier_feed\n"
    "CDR-005,+91-9000000101,DEV-A1,CYB-HYD-03,2026-08-18T04:24:04Z,ATTACHED,17.3850,78.4867,carrier_feed\n"
    "CDR-006,+91-9000000101,DEV-A1,CYB-HYD-03,2026-08-18T04:25:21Z,SMS,17.3850,78.4867,carrier_feed\n"
    "CDR-007,+91-9000000101,DEV-A1,DEL-NOI-02,2026-08-18T04:28:11Z,ATTACHED,28.5355,77.3910,carrier_feed\n"
    "CDR-008,+91-9000000101,DEV-A1,DEL-IGI-04,2026-08-18T04:30:00Z,DETACHED,28.5561,77.1008,carrier_feed\n"
)

_SAMPLES = _TMP / "samples"
_SAMPLES.mkdir(parents=True, exist_ok=True)
(_SAMPLES / "transfers.csv").write_text(_TRANSFER_CSV, encoding="utf-8")
(_SAMPLES / "ledger.csv").write_text(_LEDGER_CSV, encoding="utf-8")
(_SAMPLES / "cdr.csv").write_text(_CDR_CSV, encoding="utf-8")


async def _fresh_db():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="contract_db_"))
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp / 'contract.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    return engine, Session, tmp


async def _persist(Session, case_uuid: uuid.UUID, case_number: str, events: list[dict]):
    """Persist parser output EXACTLY as routes/evidence.py does — same helpers,
    same field mapping — with evidence_file_id=None (the consumer keys only on
    case_id + event_type, so no EvidenceFile row is needed)."""
    async with Session() as db:
        db.add(Case(id=case_uuid, case_number=case_number, title="Pipeline Contract Case"))
        await db.flush()
        for evt in events:
            db.add(EvidenceEvent(
                case_id=case_uuid,
                evidence_file_id=None,
                event_timestamp=_safe_parse_iso(evt.get("timestamp")),
                event_type=evt.get("event_type"),
                text_content=sanitize_db_val(evt.get("text")),
                source_line=evt.get("source_line"),
                source_page=evt.get("source_page"),
                event_metadata=sanitize_db_val(evt.get("metadata", {})),
            ))
        await db.commit()


# ── Bank Parser → Persisted Event → _get_bank_events ──────────────────────────

_BANK_KEYS = {"credit", "debit", "balance", "amount", "amount_val", "timestamp",
              "reference", "from", "to", "upi", "account", "event_type", "model", "has_balance"}


def test_bank_parser_to_get_bank_events_contract():
    asyncio.run(_impl_bank())


async def _impl_bank():
    engine, Session, tmp = await _fresh_db()
    try:
        # Real parsers on both bank schemas (transfer log + balance-bearing ledger).
        events = (parse_bank_csv(_SAMPLES / "transfers.csv")
                  + parse_bank_csv(_SAMPLES / "ledger.csv"))
        assert len(events) == 12, f"parser emitted {len(events)} bank events, expected 12"

        case_uuid = uuid.uuid4()
        await _persist(Session, case_uuid, "CONTRACT-BANK", events)

        async with Session() as db:
            rows = await _get_bank_events(db, case_uuid)

        assert len(rows) == 12, f"consumer returned {len(rows)} rows, expected 12"
        for r in rows:
            missing = _BANK_KEYS - set(r.keys())
            assert not missing, f"consumer row missing keys: {missing}"
            assert r["event_type"] == "bank_txn"
            assert r["timestamp"], "empty timestamp — parse/persist/round-trip dropped it"

        transfers = [r for r in rows if r["model"] == "transfer"]
        ledgers = [r for r in rows if r["model"] == "ledger"]
        assert len(transfers) == 9 and len(ledgers) == 3, (len(transfers), len(ledgers))

        # Transfer rows must carry the money-flow fields simulate_freeze() reads.
        for r in transfers:
            assert r["from"] and r["to"], "transfer row lost party accounts (freeze would see nothing)"
            assert isinstance(r["amount_val"], float) and r["amount_val"] > 0, r["amount_val"]
            assert r["has_balance"] is False and r["balance"] is None
        seed = [r for r in transfers if r["from"] == "ACCT-VICTIM-01" and r["to"] == "ACCT-MULE-11"]
        assert seed and seed[0]["amount_val"] == 285000.0, f"seed inbound flow not intact: {seed}"

        # Ledger rows must carry the balance-continuity fields ledger_audit() reads.
        for r in ledgers:
            assert r["has_balance"] is True and r["balance"] is not None, "ledger row lost balance"
            assert (r["credit"] or r["debit"]) > 0, "ledger row lost credit/debit amount"
        opening = [r for r in ledgers if r["balance"] == 120000.0]
        assert opening and opening[0]["credit"] == 50000.0, f"ledger opening row not intact: {opening}"
    finally:
        await engine.dispose()
        shutil.rmtree(tmp, ignore_errors=True)


# ── CDR Parser → Persisted Event → _get_call_events ───────────────────────────

_CALL_KEYS = {"entity", "timestamp", "lat", "lon", "source"}


def test_cdr_parser_to_get_call_events_contract():
    asyncio.run(_impl_cdr())


async def _impl_cdr():
    engine, Session, tmp = await _fresh_db()
    try:
        events = parse_call_log_csv(_SAMPLES / "cdr.csv")
        assert len(events) == 8, f"parser emitted {len(events)} call events, expected 8"

        case_uuid = uuid.uuid4()
        await _persist(Session, case_uuid, "CONTRACT-CDR", events)

        async with Session() as db:
            call_events = await _get_call_events(db, case_uuid)

        assert len(call_events) == 8, f"consumer returned {len(call_events)} events, expected 8"
        for e in call_events:
            missing = _CALL_KEYS - set(e.keys())
            assert not missing, f"consumer event missing keys: {missing}"
            # subscriber → caller mapping must survive to the entity field.
            assert e["entity"] == "+91-9000000101", f"lost subscriber identity: {e['entity']!r}"
            assert e["timestamp"], "empty timestamp — parse/persist/round-trip dropped it"
            # lat/lon must survive _to_float + JSON round-trip as usable floats.
            assert isinstance(e["lat"], float) and isinstance(e["lon"], float), (e["lat"], e["lon"])
            assert e["source"] and e["source"] != "call", f"lost cell-tower id: {e['source']!r}"

        # Distinct real towers preserved (not collapsed to a placeholder).
        sources = {e["source"] for e in call_events}
        assert {"DEL-IGI-04", "CYB-HYD-03"} <= sources, sources

        # Capstone: the retrieved events are analysis-ready — feeding them to the
        # REAL engine reproduces the known physically-impossible hop. Guards the
        # whole boundary, not just individual field presence.
        findings = impossible_travel(call_events)
        assert findings, "persisted CDR round-trip no longer yields the impossible hop"
        assert max(f.velocity_kmh for f in findings) > 900, "velocity below impossible threshold"
    finally:
        await engine.dispose()
        shutil.rmtree(tmp, ignore_errors=True)


# ── Dual-mode runner ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    _tests = [(n, f) for n, f in sorted(globals().items())
              if n.startswith("test_") and callable(f)]
    _failed = 0
    try:
        for _name, _fn in _tests:
            try:
                _fn()
                print(f"[PASS] {_name}")
            except Exception as _e:  # noqa: BLE001
                _failed += 1
                import traceback
                print(f"[FAIL] {_name}: {_e!r}")
                traceback.print_exc()
    finally:
        shutil.rmtree(_TMP, ignore_errors=True)
    print(f"\n{len(_tests) - _failed}/{len(_tests)} pipeline-contract checks passed")
    sys.exit(1 if _failed else 0)

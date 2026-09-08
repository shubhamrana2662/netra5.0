"""
CyberDrishti AI / Netra 3.0 — DEMO CASE SEEDER  (Operation Shadow Mule)

Seeds ONE polished, presentation-ready case into the real dev database
(./cyberdrishti.db by default) by driving the REAL application pipeline
in-process — NOT by hand-writing fixtures.

Why in-process HTTP (httpx.ASGITransport) rather than raw INSERTs:
  • Evidence is uploaded through the actual /evidence/upload endpoint, so the
    real parsers run, the SHA-256 ingestion lock + hash-verify fire, and files
    land inside the protected UPLOAD_DIR exactly as a live upload would.
  • Correlations are computed by the real engine, not fabricated.
  • Every screen the user demos (timeline, graph, cognitive, intel, report,
    audit chain) therefore shows genuinely DERIVED analysis over REAL evidence.

Provenance: the three CSVs below are the SAME byte-exact evidence used by the
acceptance harness (_shadow_mule_e2e.py) and the contract tests. They are a
SYNTHETIC_DEMO dataset — a fictional but internally-consistent money-mule case
built for demonstration. No real PII. The badge/title makes that explicit.

Idempotent: re-running deletes any prior demo case with the same fixed case
number (via the real DELETE endpoint, which cascades evidence/events/entities/
correlations) before re-seeding, so you always get a clean, identical demo.

Run:
    cd backend && python3 seed_demo_case.py
Then log in to the frontend as  admin / admin123  and open the case.
"""
from __future__ import annotations

import asyncio
import os
import sys

# ── Point at the REAL dev DB unless the caller overrides it. Must be set before
#    importing the app (settings is an lru_cache singleton). Mirrors .env. ──────
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./cyberdrishti.db")
os.environ.setdefault("DEBUG", "false")  # silence SQL echo during seeding
os.environ.setdefault("INITIAL_ADMIN_USERNAME", "admin")
os.environ.setdefault("INITIAL_ADMIN_PASSWORD", "admin123")

import httpx  # noqa: E402

import main  # noqa: E402
from db.session import engine, AsyncSessionLocal  # noqa: E402
from db.models import Base, EvidenceFile  # noqa: E402
from sqlalchemy import select  # noqa: E402

API = "/api/v1"

# Fixed, memorable identifiers so the demo is stable across re-seeds.
DEMO_CASE_NUMBER = "CYB-2026-SHADOW-MULE"
DEMO_TITLE = "Operation Shadow Mule — DEMONSTRATION · SYNTHETIC DATASET"

# ── Real evidence (byte-exact — identical to the acceptance harness) ──────────
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


async def _bearer(client, username, password):
    r = await client.post(f"{API}/auth/login", data={"username": username, "password": password})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _await_processing(case_uuid, expected, timeout_s=40.0):
    deadline = asyncio.get_event_loop().time() + timeout_s
    while True:
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(
                select(EvidenceFile).where(EvidenceFile.case_id == case_uuid)
            )).scalars().all()
            done = [r for r in rows if r.upload_status in ("processed", "failed")]
            if len(rows) >= expected and len(done) >= len(rows):
                return rows
        if asyncio.get_event_loop().time() > deadline:
            return rows
        await asyncio.sleep(0.5)


async def _delete_existing_demo(client, admin_h):
    """Remove any prior demo case with the fixed number, so re-seeding is clean.
    Uses the real DELETE endpoint which cascades evidence/events/entities/corr."""
    r = await client.get(f"{API}/cases", params={"page_size": 100}, headers=admin_h)
    if r.status_code != 200:
        return
    for c in r.json().get("items", []):
        if c.get("case_number") == DEMO_CASE_NUMBER:
            await client.delete(f"{API}/cases/{c['id']}", headers=admin_h)
            print(f"  · removed prior demo case {c['id']}")


async def seed() -> str:
    # Ensure schema exists (lifespan does not run under ASGITransport).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = httpx.ASGITransport(app=main.app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://seed.local", timeout=90.0) as client:
        admin_h = await _bearer(client, os.environ["INITIAL_ADMIN_USERNAME"], os.environ["INITIAL_ADMIN_PASSWORD"])
        print("✓ authenticated as admin")

        await _delete_existing_demo(client, admin_h)

        # 1) Create the case (real endpoint → real audit entry).
        r = await client.post(f"{API}/cases", json={
            "title": DEMO_TITLE,
            "priority": "high",
            "crime_type": "Financial Fraud — Money Mule Network",
            "description": (
                "SYNTHETIC DEMONSTRATION DATASET. A victim account is drained via a "
                "fake-KYC UPI debit; funds are layered through a fan-out of mule and "
                "shell accounts and cashed out at two ATMs within ~20 minutes. Device "
                "CDRs place the primary subscriber in Delhi and Hyderabad seconds "
                "apart (physically-impossible travel). No real PII."
            ),
        }, headers=admin_h)
        r.raise_for_status()
        case = r.json()
        case_id = case["id"]
        import uuid as _uuid
        case_uuid = _uuid.UUID(case_id)
        print(f"✓ created case {case['case_number']}  ({case_id})")
        print(f"  (display number pinned below to {DEMO_CASE_NUMBER})")

        # 2) Upload the three real evidence files through the real pipeline.
        files = [
            ("files", ("transfers.csv", _TRANSFER_CSV.encode(), "text/csv")),
            ("files", ("ledger.csv",    _LEDGER_CSV.encode(),   "text/csv")),
            ("files", ("cdr.csv",       _CDR_CSV.encode(),      "text/csv")),
        ]
        r = await client.post(f"{API}/evidence/upload", data={"case_id": case_id}, files=files, headers=admin_h)
        r.raise_for_status()
        print(f"✓ uploaded {r.json().get('uploaded')} evidence files — parsing in background…")

        rows = await _await_processing(case_uuid, 3)
        statuses = {r.original_name: r.upload_status for r in rows}
        n_proc = sum(1 for r in rows if r.upload_status == "processed")
        print(f"✓ evidence processed: {n_proc}/{len(rows)}  {statuses}")

        # 3) Run the real correlation engine so flagged links are ready to show.
        r = await client.post(f"{API}/correlations/{case_id}/run", headers=admin_h)
        if r.status_code == 200:
            print(f"✓ correlations computed — flagged={r.json().get('flagged')}")

        # 4) Pin the display case number to the fixed demo value (direct update —
        #    the create endpoint auto-generates a random one).
        async with AsyncSessionLocal() as db:
            from db.models import Case
            c = await db.get(Case, case_uuid)
            c.case_number = DEMO_CASE_NUMBER
            await db.commit()
        print(f"✓ pinned display number → {DEMO_CASE_NUMBER}")

    await engine.dispose()
    return case_id


def main_entry():
    print("=" * 66)
    print("  Seeding demo case: Operation Shadow Mule (synthetic dataset)")
    print("=" * 66)
    try:
        case_id = asyncio.run(seed())
    except Exception as exc:  # noqa: BLE001
        print(f"\n✗ Seeding failed: {exc!r}")
        sys.exit(1)
    print("\n" + "=" * 66)
    print("  DEMO CASE READY")
    print(f"  Case number : {DEMO_CASE_NUMBER}")
    print(f"  Case id     : {case_id}")
    print("  Login       : admin / admin123")
    print("  Open the case, then walk: Evidence → Timeline → Graph →")
    print("  Cognitive (contradictions/hypotheses/freeze) → Intel → Report 65B")
    print("=" * 66)


if __name__ == "__main__":
    main_entry()

from __future__ import annotations
"""
CyberDrishti AI — Bank Statement PDF Parser
Extracts {date, narration, credit, debit, balance} rows from Indian bank
statement PDFs using pdfplumber (digital) with Camelot as fallback (scanned).

Outputs EvidenceEvent-compatible dicts with event_type='bank_txn'.
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

# Lazy imports to avoid loading heavy libs until needed
_pdfplumber = None
_camelot = None


def _get_pdfplumber():
    global _pdfplumber
    if _pdfplumber is None:
        import pdfplumber
        _pdfplumber = pdfplumber
    return _pdfplumber


def _get_camelot():
    global _camelot
    if _camelot is None:
        import camelot
        _camelot = camelot
    return _camelot


# ── Date normalisation ────────────────────────────────────────────────────────

_DATE_FMTS = [
    "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
    "%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%b %d, %Y",
]


def _parse_date(raw: str) -> str | None:
    """Try multiple date formats; return ISO string or None."""
    raw = raw.strip()
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


# ── Amount normalisation ──────────────────────────────────────────────────────

_AMOUNT_RE = re.compile(r"[\d,]+\.?\d*")


def _parse_amount(raw: str) -> float | None:
    """Extract numeric float from currency-formatted string like '1,23,456.78'."""
    if not raw or str(raw).strip() in ("", "-", "nan"):
        return None
    m = _AMOUNT_RE.search(str(raw).replace(",", ""))
    return float(m.group()) if m else None


# ── Column header fuzzy mapper ────────────────────────────────────────────────

_HEADER_PATTERNS: dict[str, list[str]] = {
    "date":       ["date", "txn date", "transaction date", "value date", "posting date"],
    "narration":  ["narration", "description", "particulars", "details", "remarks", "transaction details"],
    "debit":      ["debit", "dr", "withdrawal", "amount (dr)", "debit amount", "withdrawals"],
    "credit":     ["credit", "cr", "deposit", "amount (cr)", "credit amount", "deposits"],
    "balance":    ["balance", "running balance", "closing balance", "available balance"],
    "ref_no":     ["ref no", "reference", "chq no", "cheque no", "txn id", "utr", "ref number"],
}


def _map_columns(columns: list[str]) -> dict[str, str | None]:
    """
    Map raw column headers to canonical names using lowercased substring matching.
    Returns {canonical -> raw_column_name | None}.
    """
    lc_cols = [c.lower().strip() for c in columns]
    result = {k: None for k in _HEADER_PATTERNS}

    for canonical, patterns in _HEADER_PATTERNS.items():
        for raw_col, lc_col in zip(columns, lc_cols):
            if any(p in lc_col for p in patterns):
                result[canonical] = raw_col
                break

    return result


# ── Core extraction ──────────────────────────────────────────────────────────

def _dataframe_to_events(df: pd.DataFrame, source_doc: str, page_num: int) -> list[dict]:
    """Convert a parsed DataFrame into EvidenceEvent dicts."""
    col_map = _map_columns(list(df.columns))
    events = []

    for idx, row in df.iterrows():
        date_raw   = str(row[col_map["date"]]) if col_map["date"] else ""
        narration  = str(row[col_map["narration"]]) if col_map["narration"] else str(row.iloc[1] if len(row) > 1 else "")
        debit_val  = _parse_amount(row[col_map["debit"]]) if col_map["debit"] else None
        credit_val = _parse_amount(row[col_map["credit"]]) if col_map["credit"] else None
        balance    = _parse_amount(row[col_map["balance"]]) if col_map["balance"] else None
        ref_no     = str(row[col_map["ref_no"]]) if col_map["ref_no"] else None

        parsed_date = _parse_date(date_raw)

        # Skip header repeat rows and empty rows
        if not narration or narration.lower() in ("nan", "description", "narration", "particulars"):
            continue

        amount = credit_val or debit_val  # primary amount for text
        txn_direction = "credit" if credit_val else ("debit" if debit_val else "unknown")
        amount_str = f"₹{amount:,.2f}" if amount else ""

        text = f"{narration.strip()} | {txn_direction.upper()} {amount_str}".strip(" |")

        events.append({
            "source_doc":   source_doc,
            "timestamp":    parsed_date,
            "text":         text,
            "event_type":   "bank_txn",
            "source_line":  None,
            "source_page":  page_num,
            "metadata": {
                "narration":  narration.strip(),
                "debit":      debit_val,
                "credit":     credit_val,
                "balance":    balance,
                "ref_no":     ref_no,
                "date_raw":   date_raw,
            },
        })

    return events


def parse_bank_pdf(
    file_path: str | Path,
    source_doc: str | None = None,
    use_camelot_fallback: bool = True,
) -> list[dict]:
    """
    Parse an Indian bank statement PDF.

    Tries pdfplumber first (works for digital PDFs with embedded text).
    Falls back to camelot lattice/stream extraction for scanned tables.

    Args:
        file_path:             Path to the PDF file.
        source_doc:            Label for EvidenceEvent (defaults to filename).
        use_camelot_fallback:  Try camelot if pdfplumber finds no tables.

    Returns:
        List of EvidenceEvent-compatible dicts.
    """
    path = Path(file_path)
    source_doc = source_doc or path.name
    all_events: list[dict] = []

    # ── Attempt 1: pdfplumber ──────────────────────────────────────────────
    pdfplumber = _get_pdfplumber()
    with pdfplumber.open(str(path)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables(
                table_settings={
                    "vertical_strategy":   "lines_strict",
                    "horizontal_strategy": "lines_strict",
                }
            )
            
            if not tables:
                # Fallback to text strategy for borderless Indian bank statements
                tables = page.extract_tables(
                    table_settings={
                        "vertical_strategy":   "text",
                        "horizontal_strategy": "text",
                    }
                )

            if not tables:
                tables = page.extract_tables()

            for table in (tables or []):
                if not table or len(table) < 2:
                    continue
                try:
                    df = pd.DataFrame(table[1:], columns=table[0])
                    events = _dataframe_to_events(df, source_doc, page_num)
                    all_events.extend(events)
                except Exception as e:
                    print(f"pdfplumber table parse error on page {page_num}: {e}")

    # ── Attempt 2: camelot fallback ────────────────────────────────────────
    if not all_events and use_camelot_fallback:
        try:
            camelot = _get_camelot()
        except ImportError:
            camelot = None
            print("Camelot is not installed or missing dependencies, skipping fallback.")
        
        if camelot:
            for flavor in ("lattice", "stream"):
                try:
                    tables = camelot.read_pdf(str(path), pages="all", flavor=flavor)
                    for tbl in tables:
                        df = tbl.df
                        if df.empty or len(df) < 2:
                            continue
                        df.columns = df.iloc[0]
                        df = df.iloc[1:].reset_index(drop=True)
                        events = _dataframe_to_events(df, source_doc, tbl.page)
                        all_events.extend(events)
                    if all_events:
                        break
                except Exception as e:
                    print(f"camelot fallback error with flavor {flavor}: {e}")
                    continue

    return all_events

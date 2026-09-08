from __future__ import annotations
"""
CyberDrishti AI — CDR (Call Detail Record) Parser
Normalises varying CSV column names via fuzzy header matching and outputs
EvidenceEvent-compatible dicts with event_type='call'.
"""
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

# ── Column name aliases ───────────────────────────────────────────────────────

_ALIASES: dict[str, list[str]] = {
    "caller":        ["calling number", "caller", "a party", "msisdn a", "msisdn", "subscriber", "from", "source number", "a number", "mobile", "phone"],
    "callee":        ["called number", "callee", "b party", "msisdn b", "to", "destination number", "b number"],
    "call_datetime": ["event_time_utc", "event time", "date time", "call date time", "start time", "call start", "datetime", "timestamp", "date"],
    "duration_sec":  ["duration", "call duration", "duration (sec)", "duration seconds", "secs", "seconds"],
    "call_type":     ["call type", "event_type", "type", "direction", "call direction"],
    "cell_id":       ["cell tower", "cell_tower", "cell id", "btsl", "lac/cell", "cell", "bts", "tower"],
    "imei":          ["imei", "imei number", "device imei", "device_id", "device id"],
    "location":      ["location", "area", "cell location", "tower location"],
    "lat":           ["latitude", "lat"],
    "lon":           ["longitude", "long", "lon", "lng"],
}


def _fuzzy_map(raw_columns: list[str]) -> dict[str, str | None]:
    """
    Map raw column names to canonical names using token-set-ratio fuzzy matching.
    Threshold: 70 (loose enough for typos, strict enough to avoid false maps).
    """
    result: dict[str, str | None] = {k: None for k in _ALIASES}
    lc_raw = [c.lower().strip() for c in raw_columns]

    for canonical, aliases in _ALIASES.items():
        for alias in aliases:
            match = process.extractOne(
                alias, lc_raw,
                scorer=fuzz.token_set_ratio,
                score_cutoff=70,
            )
            if match:
                raw_idx = lc_raw.index(match[0])
                result[canonical] = raw_columns[raw_idx]
                break

    return result


# ── Date parsing ──────────────────────────────────────────────────────────────

_DT_FMTS = [
    "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d-%m-%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d/%m/%y %H:%M:%S",
    "%d/%m/%Y %I:%M:%S %p", "%d-%m-%Y %I:%M %p",
]


def _parse_dt(raw: str) -> str | None:
    raw = str(raw).strip()
    if not raw or raw.lower() in ("nan", "none"):
        return None
    # ISO-8601 first (handles trailing 'Z' / UTC offset — common in CDR exports)
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).isoformat()
    except ValueError:
        pass
    for fmt in _DT_FMTS:
        try:
            return datetime.strptime(raw, fmt).isoformat()
        except ValueError:
            continue
    return None


def _to_float(raw) -> float | None:
    if raw is None:
        return None
    try:
        return float(str(raw).strip())
    except (ValueError, TypeError):
        return None


# ── Duration normalisation ────────────────────────────────────────────────────

def _parse_duration(raw) -> int | None:
    """Return duration in seconds as integer."""
    try:
        val = str(raw).strip()
        if ":" in val:
            # HH:MM:SS or MM:SS
            parts = list(map(int, val.split(":")))
            if len(parts) == 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
            if len(parts) == 2:
                return parts[0] * 60 + parts[1]
        return int(float(val))
    except (ValueError, TypeError):
        return None


# ── Core parser ───────────────────────────────────────────────────────────────

def parse_call_log_csv(
    file_path: str | Path,
    source_doc: str | None = None,
    encoding: str = "utf-8",
) -> list[dict]:
    """
    Parse a CDR CSV file into EvidenceEvent-compatible dicts.

    Handles:
    - Varying column orderings / names across different operators.
    - Missing optional columns (cell ID, IMEI, location).
    - Duration expressed as seconds integer or HH:MM:SS.

    Args:
        file_path:  Path to the CDR CSV file.
        source_doc: Label for EvidenceEvent (defaults to filename).
        encoding:   File encoding.

    Returns:
        List of EvidenceEvent-compatible dicts.
    """
    path = Path(file_path)
    source_doc = source_doc or path.name

    # Try multiple encodings if default fails
    df: pd.DataFrame | None = None
    for enc in [encoding, "utf-8-sig", "latin-1", "cp1252"]:
        try:
            df = pd.read_csv(str(path), encoding=enc, dtype=str, skip_blank_lines=True)
            break
        except Exception:
            continue

    if df is None or df.empty:
        return []

    # Drop fully empty columns
    df.dropna(axis=1, how="all", inplace=True)
    df.columns = [str(c).strip() for c in df.columns]

    col_map = _fuzzy_map(list(df.columns))

    events: list[dict] = []
    for lineno, (_, row) in enumerate(df.iterrows(), start=2):  # +2: header row is line 1
        def _get(key: str) -> str | None:
            col = col_map.get(key)
            if col and col in row:
                val = str(row[col]).strip()
                return val if val not in ("nan", "", "-") else None
            return None

        caller    = _get("caller")
        callee    = _get("callee")
        dt_raw    = _get("call_datetime")
        dur_raw   = _get("duration_sec")
        call_type = _get("call_type")
        cell_id   = _get("cell_id")
        imei      = _get("imei")
        location  = _get("location")
        lat       = _to_float(_get("lat"))
        lon       = _to_float(_get("lon"))

        if not caller and not callee:
            continue  # Skip rows with no subscriber / phone numbers

        duration = _parse_duration(dur_raw) if dur_raw else None
        ts = _parse_dt(dt_raw) if dt_raw else None

        dur_str = f" | Duration: {duration}s" if duration is not None else ""
        text = f"Call: {caller or '?'} -> {callee or '?'}{dur_str}"
        if call_type:
            text += f" [{call_type}]"

        events.append({
            "source_doc":  source_doc,
            "timestamp":   ts,
            "text":        text,
            "event_type":  "call",
            "source_line": lineno,
            "source_page": None,
            "metadata": {
                "caller":      caller,
                "callee":      callee,
                "duration_sec": duration,
                "call_type":   call_type,
                "cell_id":     cell_id,
                "imei":        imei,
                "location":    location,
                "lat":         lat,
                "lon":         lon,
            },
        })

    return events

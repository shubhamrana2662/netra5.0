from __future__ import annotations
"""
CyberDrishti AI — WhatsApp Export Parser
Parses the standard WhatsApp `_chat.txt` export format:
  dd/mm/yyyy, h:mm am/pm - Sender: message body (multi-line)
Outputs a list of EvidenceEvent-compatible dicts.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator


_MSG_PATTERNS = [
    # 1. Standard Android/iOS export: 22/04/2026, 9:00 am - Sender: message or [22/04/2026, 09:00:15] Sender: message
    re.compile(r"^\s*\[?(\d{1,4}[/\.\-]\d{1,2}[/\.\-]\d{1,4})[,\s]+(\d{1,2}:\d{2}(?::\d{2})?\s*(?:[ap]m)?)[\]\s]*[\-:]\s*([^:]+?):\s*(.*?)$", re.IGNORECASE),
    # 2. 24-hour time export: 22/04/2026 09:00 - Sender: message
    re.compile(r"^\s*(\d{1,4}[/\.\-]\d{1,2}[/\.\-]\d{1,4})[,\s]+(\d{1,2}:\d{2}(?::\d{2})?)\s*[\-:]\s*([^:]+?):\s*(.*?)$", re.IGNORECASE),
    # 3. Plain Chat format fallback: Sender: Message
    re.compile(r"^\s*([A-Za-z0-9_\+\-\s\.\(\)]{2,30}):\s*(.+)$"),
]

# System messages (no sender colon)
_SYS_RE = re.compile(
    r"^\s*\[?(\d{1,4}[/\.\-]\d{1,2}[/\.\-]\d{1,4})[,\s]+(\d{1,2}:\d{2}(?::\d{2})?\s*(?:[ap]m)?)[\]\s]*[\-:]\s*(.+)$",
    re.IGNORECASE,
)


@dataclass
class WhatsAppMessage:
    timestamp: datetime | None
    sender: str
    text: str
    source_line: int
    is_system: bool = False
    media_omitted: bool = False
    metadata: dict = field(default_factory=dict)


def _parse_ts(date_str: str, time_str: str) -> datetime | None:
    """
    Parse WhatsApp date/time. Handles both 2-digit and 4-digit years,
    and 12-hour AM/PM & 24-hour format.
    """
    time_str = time_str.strip().lower().replace(" ", " ")
    combined = f"{date_str} {time_str}"
    for fmt in ("%d/%m/%y %I:%M %p", "%d/%m/%Y %I:%M %p",
                "%m/%d/%y %I:%M %p", "%m/%d/%Y %I:%M %p",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
                "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(combined, fmt)
        except ValueError:
            continue
    return None


def parse_whatsapp_export(
    file_path: str | Path,
    source_doc: str | None = None,
    encoding: str = "utf-8",
) -> list[dict]:
    path = Path(file_path)
    source_doc = source_doc or path.name

    messages: list[WhatsAppMessage] = []
    current: WhatsAppMessage | None = None

    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        content = path.read_text(encoding="latin-1", errors="ignore")

    for lineno, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        matched = False
        for pat in _MSG_PATTERNS:
            m = pat.match(line)
            if m:
                if current is not None:
                    messages.append(current)

                groups = m.groups()
                if len(groups) == 4:
                    date_s, time_s, sender, body = groups
                    ts = _parse_ts(date_s, time_s)
                else:
                    sender, body = groups
                    ts = None

                media = "<Media omitted>" in body or "image omitted" in body.lower()
                current = WhatsAppMessage(
                    timestamp=ts,
                    sender=sender.strip(),
                    text=body.strip(),
                    source_line=lineno,
                    media_omitted=media,
                )
                matched = True
                break

        if not matched:
            sys_m = _SYS_RE.match(line)
            if sys_m and current is None:
                date_s, time_s, body = sys_m.groups()
                ts = _parse_ts(date_s, time_s)
                messages.append(WhatsAppMessage(
                    timestamp=ts,
                    sender="__system__",
                    text=body.strip(),
                    source_line=lineno,
                    is_system=True,
                ))
            elif current is not None:
                current.text += "\n" + line

    # Flush last message
    if current is not None:
        messages.append(current)

    # Convert to EvidenceEvent dicts
    return [
        {
            "source_doc": source_doc,
            "timestamp": msg.timestamp.isoformat() if msg.timestamp and msg.timestamp.year != 1970 else None,
            "text": msg.text,
            "event_type": "whatsapp_msg",
            "source_line": msg.source_line,
            "source_page": None,
            "metadata": {
                "sender": msg.sender,
                "is_system": msg.is_system,
                "media_omitted": msg.media_omitted,
            },
        }
        for msg in messages
    ]

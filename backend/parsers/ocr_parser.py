from __future__ import annotations
"""
CyberDrishti AI — OCR Parser
Runs Tesseract on image evidence (screenshots, scanned docs).
Flags low-confidence tokens rather than silently trusting them.
Outputs EvidenceEvent-compatible dicts with event_type='ocr_text'.
"""
import os
from pathlib import Path

try:
    import pytesseract
except ImportError:
    pytesseract = None
from PIL import Image


# ── Confidence thresholds ─────────────────────────────────────────────────────
HIGH_CONF   = 80   # Token is reliably read
MEDIUM_CONF = 50   # Token is likely correct
LOW_CONF    = 0    # Token needs manual review — flagged with [?]


def _tesseract_available() -> bool:
    """Check that Tesseract binary is reachable."""
    if pytesseract is None:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _annotate_with_confidence(image: Image.Image, lang: str = "eng+hin") -> tuple[str, float, list[dict]]:
    """
    Run Tesseract image_to_data on a PIL image.
    Returns:
        - annotated_text: text with [?] markers on low-confidence tokens
        - mean_confidence: average confidence across all words
        - low_conf_tokens: list of {word, confidence, line} for flagged tokens
    """
    data = pytesseract.image_to_data(
        image,
        lang=lang,
        output_type=pytesseract.Output.DICT,
    )

    words: list[str] = []
    confidences: list[float] = []
    low_conf_tokens: list[dict] = []

    n_boxes = len(data["text"])
    for i in range(n_boxes):
        text = data["text"][i].strip()
        if not text:
            continue
        try:
            conf = float(data["conf"][i])
        except (ValueError, TypeError):
            conf = -1

        if conf < 0:
            # Structural token (line break etc.) — skip confidence tracking
            words.append(text)
            continue

        confidences.append(conf)

        if conf < MEDIUM_CONF:
            words.append(f"[?{text}]")
            low_conf_tokens.append({
                "word": text,
                "confidence": conf,
                "line_num": data["line_num"][i],
            })
        else:
            words.append(text)

    annotated = " ".join(words)
    mean_conf  = sum(confidences) / len(confidences) if confidences else 0.0
    return annotated, mean_conf, low_conf_tokens


def parse_image_ocr(
    file_path: str | Path,
    source_doc: str | None = None,
    lang: str = "eng+hin",
    dpi: int = 300,
) -> list[dict]:
    """
    Run OCR on an image file (PNG, JPEG, TIFF, WebP, BMP).

    Args:
        file_path:  Path to the image.
        source_doc: EvidenceEvent label.
        lang:       Tesseract language string (default: English + Hindi).
        dpi:        Target DPI for image upsampling (300 = good for text).

    Returns:
        A single-element list containing one EvidenceEvent dict, or empty
        list on failure.
    """
    path = Path(file_path)
    source_doc = source_doc or path.name

    if not _tesseract_available():
        return [{
            "source_doc":  source_doc,
            "timestamp":   None,
            "text":        "",
            "event_type":  "ocr_text",
            "source_line": None,
            "source_page": 1,
            "metadata": {
                "error": "Tesseract not installed or not found in PATH",
                "mean_confidence": 0.0,
                "low_conf_tokens": [],
                "needs_manual_review": True,
            },
        }]

    try:
        img = Image.open(str(path))

        # Upscale small images for better OCR accuracy
        w, h = img.size
        if w < 800 or h < 800:
            scale = max(800 / w, 800 / h, 1.0)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        annotated_text, mean_conf, low_conf_tokens = _annotate_with_confidence(img, lang)

        needs_review = mean_conf < HIGH_CONF or len(low_conf_tokens) > 3

        return [{
            "source_doc":  source_doc,
            "timestamp":   None,  # OCR images rarely embed timestamps
            "text":        annotated_text,
            "event_type":  "ocr_text",
            "source_line": None,
            "source_page": 1,
            "metadata": {
                "mean_confidence":    round(mean_conf, 2),
                "low_conf_tokens":    low_conf_tokens[:20],  # Cap to avoid huge payloads
                "needs_manual_review": needs_review,
                "language":           lang,
                "image_size":         list(img.size),
            },
        }]

    except Exception as exc:
        return [{
            "source_doc":  source_doc,
            "timestamp":   None,
            "text":        "",
            "event_type":  "ocr_text",
            "source_line": None,
            "source_page": 1,
            "metadata": {
                "error": str(exc),
                "mean_confidence":    0.0,
                "low_conf_tokens":    [],
                "needs_manual_review": True,
            },
        }]

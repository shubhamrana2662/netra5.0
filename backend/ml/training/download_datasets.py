from __future__ import annotations
"""
CyberDrishti AI — Automatic Kaggle Dataset Ingestion & Inspection Service

Features:
  1. Accepts Kaggle URL or dataset slug (e.g. omsshete/upi-fraud-detection-dataset).
  2. Downloads via Kaggle API / CLI into backend/ml/data/raw/kaggle/<dataset_slug>/.
  3. Preserves original downloaded files unchanged.
  4. Generates dataset_metadata.json with provenance, hashes, file sizes, and timestamps.
  5. Inspects CSV, JSON, JSONL, TXT files for schema, row counts, dtypes, missing values, samples.
  6. Automatically identifies candidate target, text, and entity columns.
  7. Classifies dataset type: NER, FRAUD_CLASSIFICATION, CYBER_THREAT_CLASSIFICATION,
     PHISHING_CLASSIFICATION, TRANSACTION_DATA, CDR_DATA, or UNKNOWN.
  8. If classification is uncertain, stops and reports structure without guessing.

Usage:
    python3 -m ml.training.download_datasets --url "https://www.kaggle.com/datasets/omsshete/upi-fraud-detection-dataset"
    python3 -m ml.training.download_datasets --url "omsshete/upi-fraud-detection-dataset"
"""
import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_KAGGLE_DIR = BASE_DIR / "ml" / "data" / "raw" / "kaggle"

CLASSIFICATION_TYPES = [
    "NER",
    "FRAUD_CLASSIFICATION",
    "CYBER_THREAT_CLASSIFICATION",
    "PHISHING_CLASSIFICATION",
    "TRANSACTION_DATA",
    "CDR_DATA",
    "UNKNOWN",
]

# ── URL & Slug Parsing ────────────────────────────────────────────────────────

def extract_kaggle_slug(url_or_slug: str) -> str:
    """
    Extract canonical Kaggle dataset slug (owner/dataset-name) from URL or raw string.

    Examples:
      https://www.kaggle.com/datasets/omsshete/upi-fraud-detection-dataset -> omsshete/upi-fraud-detection-dataset
      https://www.kaggle.com/datasets/omsshete/upi-fraud-detection-dataset/data -> omsshete/upi-fraud-detection-dataset
      datasets/omsshete/upi-fraud-detection-dataset -> omsshete/upi-fraud-detection-dataset
      omsshete/upi-fraud-detection-dataset -> omsshete/upi-fraud-detection-dataset
    """
    s = url_or_slug.strip()
    if not s:
        raise ValueError("Dataset URL or slug cannot be empty.")

    # Strip query parameters and fragments
    s = s.split("?")[0].split("#")[0].rstrip("/")

    # Parse full Kaggle URLs
    if "kaggle.com" in s:
        parsed = urllib.parse.urlparse(s)
        parts = [p for p in parsed.path.split("/") if p]
        if "datasets" in parts:
            idx = parts.index("datasets")
            if len(parts) >= idx + 3:
                return f"{parts[idx+1]}/{parts[idx+2]}"

    if s.startswith("datasets/"):
        parts = s.split("/")
        if len(parts) >= 3:
            return f"{parts[1]}/{parts[2]}"

    parts = s.split("/")
    if len(parts) == 2 and parts[0] and parts[1]:
        return f"{parts[0]}/{parts[1]}"

    raise ValueError(
        f"Could not parse Kaggle dataset slug from '{url_or_slug}'.\n"
        "Expected format: 'owner/dataset-name' or "
        "'https://www.kaggle.com/datasets/owner/dataset-name'"
    )


# ── File Hashing ──────────────────────────────────────────────────────────────

def compute_sha256(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


# ── Kaggle Downloader ─────────────────────────────────────────────────────────

def find_kaggle_cli() -> Optional[str]:
    """Find location of kaggle CLI executable if installed."""
    cli = shutil.which("kaggle")
    if cli:
        return cli
    # Common user bin locations on macOS / Linux
    candidates = [
        Path.home() / "Library" / "Python" / "3.9" / "bin" / "kaggle",
        Path.home() / "Library" / "Python" / "3.10" / "bin" / "kaggle",
        Path.home() / "Library" / "Python" / "3.11" / "bin" / "kaggle",
        Path.home() / ".local" / "bin" / "kaggle",
        Path("/usr/local/bin/kaggle"),
    ]
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def download_kaggle_dataset(slug: str, output_dir: Path) -> bool:
    """
    Download and unzip a Kaggle dataset into output_dir.
    Requires KAGGLE_USERNAME & KAGGLE_KEY or ~/.kaggle/kaggle.json.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    kaggle_user = os.environ.get("KAGGLE_USERNAME")
    kaggle_key = os.environ.get("KAGGLE_KEY")
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"

    has_creds = (kaggle_user and kaggle_key) or kaggle_json.exists()

    if not has_creds:
        print("\n" + "=" * 70)
        print("⚠️  KAGGLE CREDENTIALS NOT FOUND")
        print("=" * 70)
        print("To download real Kaggle datasets automatically, set your credentials:")
        print("  Option A: Set environment variables:")
        print("            export KAGGLE_USERNAME='your_username'")
        print("            export KAGGLE_KEY='your_api_key'")
        print("  Option B: Place your API key file at:")
        print(f"            {kaggle_json}")
        print("=" * 70 + "\n")
        return False

    # Attempt 1: Kaggle Python API
    try:
        import kaggle
        print(f"📥 Downloading Kaggle dataset '{slug}' via Python API...")
        kaggle.api.dataset_download_files(slug, path=str(output_dir), unzip=True)
        print(f"✅ Successfully downloaded and extracted '{slug}' to {output_dir}")
        return True
    except (ImportError, IOError, OSError, Exception) as api_err:
        logger.debug("[Kaggle API] Python API download failed (%s). Trying CLI...", api_err)

    # Attempt 2: Kaggle CLI
    cli_path = find_kaggle_cli()
    if cli_path:
        try:
            print(f"📥 Downloading Kaggle dataset '{slug}' via CLI ({cli_path})...")
            cmd = [cli_path, "datasets", "download", "-d", slug, "-p", str(output_dir), "--unzip"]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                print(f"✅ Successfully downloaded and extracted '{slug}' to {output_dir}")
                return True
            else:
                print(f"❌ Kaggle CLI error: {res.stderr.strip()}")
                return False
        except Exception as cli_err:
            print(f"❌ Failed to run Kaggle CLI: {cli_err}")
            return False

    print("❌ Failed to download dataset using Kaggle API and CLI.")
    return False


# ── Dataset Inspection ────────────────────────────────────────────────────────

def inspect_file(file_path: Path) -> Dict[str, Any]:
    """Inspect a single data file (CSV, TSV, JSON, JSONL, TXT) and report schema and stats."""
    ext = file_path.suffix.lower()
    rel_name = file_path.name

    stats: Dict[str, Any] = {
        "filename": rel_name,
        "extension": ext,
        "size_bytes": file_path.stat().st_size,
        "row_count": 0,
        "column_count": 0,
        "columns": [],
        "dtypes": {},
        "missing_values": {},
        "sample_records": [],
        "possible_target_cols": [],
        "possible_text_cols": [],
        "possible_entity_cols": [],
        "is_ner_format": False,
    }

    if ext in (".csv", ".tsv", ".txt"):
        sep = "\t" if ext == ".tsv" else ","
        try:
            import pandas as pd
            # Quick check if tab or comma
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                first_line = f.readline()
                if "\t" in first_line and ext != ".csv":
                    sep = "\t"

            df = pd.read_csv(file_path, sep=sep, nrows=1000, on_bad_lines="skip")
            # Calculate total rows efficiently
            with open(file_path, "rb") as f:
                total_lines = sum(1 for _ in f) - 1  # Minus header line
            stats["row_count"] = max(total_lines, len(df))

            stats["column_count"] = len(df.columns)
            stats["columns"] = [str(c) for c in df.columns]
            stats["dtypes"] = {str(col): str(dtype) for col, dtype in df.dtypes.items()}

            # Missing values count and pct (sample of 1000)
            missing = {}
            for col in df.columns:
                null_cnt = int(df[col].isna().sum())
                pct = round((null_cnt / max(len(df), 1)) * 100.0, 2)
                missing[str(col)] = {"count_sample": null_cnt, "percentage_sample": pct}
            stats["missing_values"] = missing

            # Sample records
            stats["sample_records"] = df.head(3).to_dict(orient="records")

            # Candidate column detection
            _identify_candidates(stats, df)

        except Exception as exc:
            stats["error"] = f"Failed to parse tabular file: {exc}"
            # Fallback line count
            with open(file_path, "rb") as f:
                stats["row_count"] = sum(1 for _ in f)

    elif ext in (".json", ".jsonl"):
        try:
            records = []
            is_jsonl = False
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                first_char = f.read(1)
                f.seek(0)
                if first_char == "{":
                    is_jsonl = True
                    for i, line in enumerate(f):
                        if i >= 1000:
                            break
                        line = line.strip()
                        if line:
                            records.append(json.loads(line))
                elif first_char == "[":
                    data = json.load(f)
                    if isinstance(data, list):
                        records = data[:1000]

            stats["row_count"] = len(records)
            if records and isinstance(records[0], dict):
                cols = list(records[0].keys())
                stats["column_count"] = len(cols)
                stats["columns"] = cols
                stats["sample_records"] = records[:3]

                # Check if NER format
                if "tokens" in cols and "tags" in cols:
                    stats["is_ner_format"] = True

                try:
                    import pandas as pd
                    df = pd.DataFrame(records)
                    _identify_candidates(stats, df)
                except Exception:
                    pass

        except Exception as exc:
            stats["error"] = f"Failed to parse JSON file: {exc}"

    return stats


def _identify_candidates(stats: Dict[str, Any], df) -> None:
    """Identify candidate target, text, and entity columns based on naming & data patterns."""
    cols = [str(c) for c in df.columns]

    target_keywords = re.compile(
        r"^(is_)?(fraud|label|target|class|category|type|phishing|attack|scam|result|status|malware)",
        re.IGNORECASE,
    )
    entity_keywords = re.compile(
        r"(phone|mobile|upi|vpa|account|acc|card|ip|email|url|domain|sender|receiver|user|person|name|imei|imsi|ifsc|bank)",
        re.IGNORECASE,
    )
    text_keywords = re.compile(
        r"(text|body|message|content|description|comment|tweet|post|sentence|payload|raw)",
        re.IGNORECASE,
    )

    targets = []
    entities = []
    texts = []

    for col in cols:
        col_clean = col.strip()
        # Target check
        if target_keywords.search(col_clean) or df[col_clean].nunique() in (2, 3):
            targets.append(col_clean)

        # Entity check
        if entity_keywords.search(col_clean):
            entities.append(col_clean)

        # Text check
        if text_keywords.search(col_clean):
            texts.append(col_clean)
        elif df[col_clean].dtype == "object":
            # Check mean length of non-null strings
            lens = df[col_clean].dropna().astype(str).str.len()
            if len(lens) > 0 and lens.mean() > 20:
                if col_clean not in texts:
                    texts.append(col_clean)

    stats["possible_target_cols"] = list(dict.fromkeys(targets))
    stats["possible_text_cols"] = list(dict.fromkeys(texts))
    stats["possible_entity_cols"] = list(dict.fromkeys(entities))


# ── Dataset Classification ───────────────────────────────────────────────────

def classify_dataset(
    file_inspections: List[Dict[str, Any]], slug: str
) -> Tuple[str, float, str]:
    """
    Classify dataset into one of:
      NER, FRAUD_CLASSIFICATION, CYBER_THREAT_CLASSIFICATION,
      PHISHING_CLASSIFICATION, TRANSACTION_DATA, CDR_DATA, UNKNOWN.

    Returns:
        (category: str, confidence: float, explanation: str)
    """
    all_cols = []
    all_targets = []
    all_texts = []
    all_entities = []
    has_ner_format = False

    slug_lower = slug.lower()

    for insp in file_inspections:
        all_cols.extend([c.lower() for c in insp.get("columns", [])])
        all_targets.extend([c.lower() for c in insp.get("possible_target_cols", [])])
        all_texts.extend([c.lower() for c in insp.get("possible_text_cols", [])])
        all_entities.extend([c.lower() for c in insp.get("possible_entity_cols", [])])
        if insp.get("is_ner_format"):
            has_ner_format = True

    all_cols_set = set(all_cols)

    # Rule 1: NER
    if has_ner_format or ("tokens" in all_cols_set and "tags" in all_cols_set) or "ner" in slug_lower:
        return (
            "NER",
            0.95 if has_ner_format else 0.80,
            "Dataset contains 'tokens' and 'tags' fields or explicitly states NER task.",
        )

    # Rule 2: CDR_DATA
    cdr_keywords = {"calling_num", "called_num", "caller", "receiver", "duration", "call_type", "cell_id", "imei", "imsi", "cdr"}
    if len(all_cols_set & cdr_keywords) >= 2 or "cdr" in slug_lower or "call_log" in slug_lower:
        return (
            "CDR_DATA",
            0.90,
            f"Contains Call Detail Record fields: {all_cols_set & cdr_keywords}",
        )

    # Rule 3: PHISHING_CLASSIFICATION
    phishing_keywords = {"phishing", "url", "domain", "spam", "email_body", "mail_text"}
    if any(k in slug_lower for k in ["phishing", "spam", "url_fraud"]) or any(k in all_targets for k in ["phishing", "spam"]):
        return (
            "PHISHING_CLASSIFICATION",
            0.88,
            "Dataset contains URL/Email features with phishing or spam target labels.",
        )

    # Rule 4: CYBER_THREAT_CLASSIFICATION
    threat_keywords = {"attack", "malware", "cve", "ddos", "intrusion", "packet", "protocol", "port", "threat"}
    if any(k in slug_lower for k in threat_keywords) or any(k in all_cols_set for k in ["attack_type", "malware_family", "cve_id"]):
        return (
            "CYBER_THREAT_CLASSIFICATION",
            0.85,
            "Dataset contains cyber threat, network traffic, or malware classification features.",
        )

    # Rule 5: FRAUD_CLASSIFICATION vs TRANSACTION_DATA
    fraud_keywords = {"fraud", "is_fraud", "fraud_flag", "upi_fraud", "scam"}
    has_fraud_target = any(k in all_targets for k in ["is_fraud", "fraud", "label", "target", "class"]) or "fraud" in slug_lower
    has_financial_entities = any(k in all_entities for k in ["upi", "account", "amount", "vpa", "card", "bank"]) or "upi" in slug_lower

    if has_fraud_target and has_financial_entities:
        return (
            "FRAUD_CLASSIFICATION",
            0.92,
            "Dataset contains financial transaction features and an explicit fraud target column.",
        )
    elif has_fraud_target:
        return (
            "FRAUD_CLASSIFICATION",
            0.80,
            "Dataset contains an explicit classification target column related to fraud/scams.",
        )
    elif has_financial_entities and not has_fraud_target:
        return (
            "TRANSACTION_DATA",
            0.85,
            "Dataset contains financial transaction fields (account, UPI, amount) without an explicit target label.",
        )

    # Default: UNKNOWN
    return (
        "UNKNOWN",
        0.0,
        "Dataset structure is ambiguous or lacks clear target/label indicators. Manual schema mapping required.",
    )


# ── Orchestrator ──────────────────────────────────────────────────────────────

def process_kaggle_ingestion(
    url_or_slug: str,
    raw_kaggle_base: Path = RAW_KAGGLE_DIR,
) -> Dict[str, Any]:
    """
    Ingest, inspect, and classify a Kaggle dataset.

    Steps:
      1. Extract slug.
      2. Download into backend/ml/data/raw/kaggle/<dataset_slug>/.
      3. Compute file sizes, hashes, provenance.
      4. Inspect data files.
      5. Classify dataset.
      6. Write dataset_metadata.json.
    """
    slug = extract_kaggle_slug(url_or_slug)
    kaggle_url = f"https://www.kaggle.com/datasets/{slug}"

    # Destination directory: backend/ml/data/raw/kaggle/<owner>/<dataset_name>/
    dataset_dir = raw_kaggle_base / Path(slug)
    dataset_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 75)
    print("  CYBERDRISHTI AI — KAGGLE DATASET INGESTION & INSPECTION  ")
    print("=" * 75)
    print(f"  Input URL/Slug: {url_or_slug}")
    print(f"  Extracted Slug: {slug}")
    print(f"  Destination:    {dataset_dir.absolute()}")
    print("=" * 75 + "\n")

    # 1. Download
    download_ok = download_kaggle_dataset(slug, dataset_dir)
    if not download_ok:
        print("❌ Dataset download failed. Checking if files already exist in destination...")
        existing_files = [f for f in dataset_dir.rglob("*") if f.is_file() and f.name != "dataset_metadata.json"]
        if not existing_files:
            raise RuntimeError(
                f"Dataset '{slug}' could not be downloaded and destination directory is empty.\n"
                "Provide Kaggle credentials (KAGGLE_USERNAME & KAGGLE_KEY) or place files in:\n"
                f"  {dataset_dir}"
            )
        print(f"ℹ️ Found {len(existing_files)} existing file(s) in {dataset_dir}. Proceeding with inspection.")

    # 2. Collect files and calculate hashes
    downloaded_files = []
    file_inspections = []

    for path in sorted(dataset_dir.rglob("*")):
        if path.is_file() and path.name != "dataset_metadata.json" and not path.name.startswith("."):
            rel_path = str(path.relative_to(dataset_dir))
            size = path.stat().st_size
            sha256 = compute_sha256(path)
            downloaded_files.append({
                "filename": rel_path,
                "size_bytes": size,
                "sha256": sha256,
            })

            # Inspect data files
            if path.suffix.lower() in (".csv", ".tsv", ".json", ".jsonl", ".txt"):
                insp = inspect_file(path)
                insp["relative_path"] = rel_path
                file_inspections.append(insp)

    # 3. Classify dataset
    category, confidence, explanation = classify_dataset(file_inspections, slug)

    # 4. Generate dataset_metadata.json
    metadata = {
        "kaggle_url": kaggle_url,
        "dataset_slug": slug,
        "download_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_files": len(downloaded_files),
        "files": downloaded_files,
        "classification": {
            "category": category,
            "confidence": confidence,
            "explanation": explanation,
        },
        "file_inspections": file_inspections,
    }

    metadata_path = dataset_dir / "dataset_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 75)
    print("📊 DATASET INSPECTION & CLASSIFICATION REPORT")
    print("=" * 75)
    print(f"  Dataset Slug:  {slug}")
    print(f"  Total Files:   {len(downloaded_files)}")
    print(f"  Classification: {category} (confidence: {confidence:.2f})")
    print(f"  Reason:        {explanation}")
    print("-" * 75)

    for insp in file_inspections:
        print(f"\n  📄 File: {insp['filename']}")
        print(f"     Rows: {insp.get('row_count', 0):,}")
        print(f"     Columns ({insp.get('column_count', 0)}): {insp.get('columns', [])[:10]}")
        print(f"     Possible Targets:  {insp.get('possible_target_cols', [])}")
        print(f"     Possible Text:     {insp.get('possible_text_cols', [])}")
        print(f"     Possible Entities: {insp.get('possible_entity_cols', [])}")

        if insp.get("sample_records"):
            print("     Sample Record 1:")
            print(f"       {json.dumps(insp['sample_records'][0], ensure_ascii=False)[:120]}...")

    print("\n" + "=" * 75)
    print(f"✅ Ingestion complete. Provenance saved to: {metadata_path}")
    print("=" * 75 + "\n")

    if category == "UNKNOWN":
        print(
            "⚠️  NOTICE: Classification is UNKNOWN / UNCERTAIN.\n"
            "Review the column inspection above and specify a custom schema mapping before training."
        )

    return metadata


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="CyberDrishti AI — Automatic Kaggle Dataset Downloader & Inspector"
    )
    parser.add_argument(
        "--url", "-u", required=True,
        help="Kaggle dataset URL or slug (e.g. 'omsshete/upi-fraud-detection-dataset')"
    )
    parser.add_argument(
        "--output_dir", default=str(RAW_KAGGLE_DIR),
        help=f"Base output directory for Kaggle downloads (default: {RAW_KAGGLE_DIR})"
    )

    args = parser.parse_args()
    raw_base = Path(args.output_dir)

    try:
        process_kaggle_ingestion(args.url, raw_kaggle_base=raw_base)
    except Exception as exc:
        print(f"\n❌ Ingestion error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

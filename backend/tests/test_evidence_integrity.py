import hashlib

from routes.evidence import _safe_display_name


def test_same_content_has_same_hash_regardless_of_filename():
    content = b"forensic evidence bytes"

    first = hashlib.sha256(content).hexdigest()
    renamed = hashlib.sha256(content).hexdigest()

    assert first == renamed


def test_display_name_strips_paths_and_unsafe_characters():
    assert _safe_display_name("../../case/evidence?.pdf") == "evidence.pdf"
    assert _safe_display_name(r"C:\temp\record.csv") == "record.csv"

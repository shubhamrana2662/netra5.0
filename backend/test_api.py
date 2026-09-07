import sys
import httpx
from pathlib import Path

# Add backend dir to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import settings

def test_gemini():
    api_key = settings.gemini_api_key.strip()
    log_lines = []
    log_lines.append(f"Testing GEMINI_API_KEY: '{api_key[:10]}...' (length: {len(api_key)})")

    endpoints = [
        ("v1beta", "gemini-1.5-flash"),
        ("v1beta", "gemini-1.5-pro"),
        ("v1", "gemini-1.5-flash"),
        ("v1beta", "gemini-2.0-flash-exp"),
    ]

    payload = {
        "contents": [{"role": "user", "parts": [{"text": "Hello, respond with OK."}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 100}
    }

    headers_options = [
        ("x-goog-api-key", {"x-goog-api-key": api_key, "Content-Type": "application/json"}),
        ("Bearer", {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}),
        ("query_only", {"Content-Type": "application/json"}),
    ]

    success = False
    for ver, model in endpoints:
        for name, headers in headers_options:
            url = f"https://generativelanguage.googleapis.com/{ver}/models/{model}:generateContent?key={api_key}"
            try:
                with httpx.Client(timeout=15.0) as c:
                    resp = c.post(url, json=payload, headers=headers)
                    log_lines.append(f"[{ver}/{model}] Header: {name} -> Status {resp.status_code}")
                    if resp.status_code == 200:
                        log_lines.append(f"SUCCESS! Response: {resp.text[:200]}")
                        success = True
                        break
                    else:
                        log_lines.append(f"   Body: {resp.text[:250]}")
            except Exception as e:
                log_lines.append(f"[{ver}/{model}] Header: {name} -> Exception: {e}")
        if success:
            break

    out_file = Path(__file__).resolve().parent / "api_test.log"
    out_file.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"Logged to {out_file}")

if __name__ == "__main__":
    test_gemini()

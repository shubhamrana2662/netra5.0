import sys
import os
from pathlib import Path

# Add backend directory to sys.path so all application modules are found
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure SQLite database path and environment
is_serverless = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
if is_serverless or not os.access(BACKEND_DIR, os.W_OK):
    db_path = Path("/tmp/cyberdrishti.db")
    src_db = BACKEND_DIR / "cyberdrishti.db"
    if src_db.exists() and not db_path.exists():
        import shutil
        shutil.copy2(src_db, db_path)
else:
    db_path = BACKEND_DIR / "cyberdrishti.db"

os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
os.environ.setdefault("ENVIRONMENT", "production")

from main import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


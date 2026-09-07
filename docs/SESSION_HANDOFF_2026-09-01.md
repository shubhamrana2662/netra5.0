# Session Handoff - 2026-09-01

## Pause Point

The full-stack startup was paused at the user's request. The frontend, FastAPI backend, and Ollama were stopped after this note was created. PostgreSQL remains running as a Windows service because the current shell does not have permission to stop its service account; it was not force-killed to avoid database recovery risk. Installed software, the PostgreSQL database, schema, migration, administrator account, model files, and source changes were preserved.

## Completed

- PostgreSQL 16.15 installed through `winget`.
- Windows service name: `postgresql-x64-16`.
- PostgreSQL application role created: `cyberdrishti`.
- PostgreSQL database created: `cyberdrishti`.
- Base schema applied from `backend/db/init_db.sql`.
- Evidence-integrity migration applied from `backend/db/migrations/20260902_evidence_integrity.sql`.
- Case-scoped evidence hash and storage-path uniqueness constraints are active.
- Local application administrator seeded:
  - Username: `admin`
  - Password: `admin123`
  - Role: `admin`
- Ollama 0.32.6 detected and started successfully.
- Ollama model available: `llama3.2:1b`.
- Backend dependencies resolve through `uv` with Python 3.11.
- FastAPI application import verified.
- Backend source compilation passed.
- Focused backend tests passed: `4 passed`.
- Frontend TypeScript check passed.
- Frontend production build passed.

## Important Runtime Facts

- Docker is not installed.
- Redis is not installed.
- Redis is not currently required by the verified synchronous request paths, but queue/cache behavior remains unavailable.
- ChromaDB is embedded in the backend and does not require a separate server process.
- Cloud AI is disabled by default with `ALLOW_CLOUD_AI=false`.
- PostgreSQL is the intended runtime database. The old `backend/cyberdrishti.db` SQLite file is incomplete and must not be used for full-stack validation.
- The frontend uses `http://localhost:8000/api/v1`.
- The current frontend development port is `3100`.

## Backend Start Command

Run from `backend` with these environment variables:

```powershell
$env:DATABASE_URL='postgresql://cyberdrishti:cyberdrishti_secret@localhost:5432/cyberdrishti'
$env:REDIS_URL='redis://localhost:6379/0'
$env:OLLAMA_BASE_URL='http://localhost:11434'
$env:ALLOW_CLOUD_AI='false'
uv run --python 3.11 --with-requirements requirements.txt uvicorn main:app --host 127.0.0.1 --port 8000
```

## Tomorrow's Sequence

1. Start the PostgreSQL service: `Start-Service postgresql-x64-16`.
2. Start Ollama and verify `http://localhost:11434/api/tags`.
3. Start FastAPI using the command above.
4. Verify `http://localhost:8000/health`.
5. Authenticate with `admin` / `admin123` using `/api/v1/auth/login`.
6. Verify `/api/v1/auth/me` with the returned bearer token.
7. Start the frontend on port `3100`.
8. Test the animated login through the browser.
9. Create a case and validate assigned-case access boundaries.
10. Upload identical bytes under the same and different filenames and confirm duplicate alerts.
11. Upload different bytes under the same filename and confirm no overwrite.
12. Validate evidence processing, Chroma indexing, graph caps, and absence of fabricated links.
13. Run concurrent duplicate-upload and authorization integration tests.

## Remaining Blockers and Decisions

- Redis and durable parsing jobs are not available yet.
- In-process FastAPI background parsing must be replaced with durable, idempotent jobs.
- Envelope encryption and independent key custody are not implemented.
- The system must not be described as absolutely leak-proof.
- The external AI credential found in local configuration must be rotated before production use.
- Full PostgreSQL-backed end-to-end validation had not yet run when the session was paused.

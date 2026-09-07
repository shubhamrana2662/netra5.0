-- Evidence-integrity migration for databases created before 2026-09-02.
-- Review duplicate rows before applying the unique content constraint.

BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'evidence_events'
          AND column_name = 'event_metadata'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'evidence_events'
          AND column_name = 'metadata'
    ) THEN
        ALTER TABLE evidence_events RENAME COLUMN event_metadata TO metadata;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM evidence_files
        GROUP BY case_id, sha256_hash
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Duplicate evidence hashes exist. Reconcile acquisitions before applying this migration.';
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_evidence_case_sha256
    ON evidence_files(case_id, sha256_hash);

CREATE UNIQUE INDEX IF NOT EXISTS uq_evidence_storage_path
    ON evidence_files(storage_path);

ALTER TABLE evidence_files
    DROP CONSTRAINT IF EXISTS ck_evidence_size;
ALTER TABLE evidence_files
    ADD CONSTRAINT ck_evidence_size
    CHECK (file_size_bytes IS NULL OR file_size_bytes >= 0);

COMMIT;

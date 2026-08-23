ALTER TABLE users
    ADD COLUMN IF NOT EXISTS audience TEXT NOT NULL DEFAULT 'ADULT';

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS guardian_email TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'users_audience_check'
    ) THEN
        ALTER TABLE users
            ADD CONSTRAINT users_audience_check
            CHECK (audience IN ('CHILD', 'TEEN', 'ADULT'));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'users_child_guardian_check'
    ) THEN
        ALTER TABLE users
            ADD CONSTRAINT users_child_guardian_check
            CHECK (audience <> 'CHILD' OR guardian_email IS NOT NULL);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS users_audience_idx ON users(audience);

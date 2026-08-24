ALTER TABLE scheduled_streams
    ADD COLUMN IF NOT EXISTS live_started_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS live_ended_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS live_room_id TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'scheduled_streams_live_lifecycle_ck'
    ) THEN
        ALTER TABLE scheduled_streams
            ADD CONSTRAINT scheduled_streams_live_lifecycle_ck CHECK (
                (live_started_at IS NULL AND live_ended_at IS NULL AND live_room_id IS NULL)
                OR
                (live_started_at IS NOT NULL AND live_room_id IS NOT NULL
                 AND length(trim(live_room_id)) BETWEEN 6 AND 128
                 AND (live_ended_at IS NULL OR live_ended_at >= live_started_at))
            );
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS scheduled_streams_active_room_uidx
    ON scheduled_streams(live_room_id)
    WHERE live_started_at IS NOT NULL AND live_ended_at IS NULL;

CREATE INDEX IF NOT EXISTS scheduled_streams_active_idx
    ON scheduled_streams(live_started_at DESC)
    WHERE live_started_at IS NOT NULL AND live_ended_at IS NULL;

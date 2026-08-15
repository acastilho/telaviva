CREATE TABLE IF NOT EXISTS recordings (
    id UUID PRIMARY KEY,
    stream_id UUID NOT NULL UNIQUE REFERENCES scheduled_streams(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('RECORDING','PROCESSING','READY','FAILED')),
    source_key TEXT NOT NULL,
    playback_key TEXT,
    thumbnail_key TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at TIMESTAMPTZ,
    duration_seconds INTEGER CHECK (duration_seconds >= 0),
    metadata JSONB NOT NULL DEFAULT '{}',
    failure_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (status <> 'READY' OR (
        ended_at IS NOT NULL AND playback_key IS NOT NULL AND thumbnail_key IS NOT NULL
        AND duration_seconds IS NOT NULL
    )),
    CHECK (status <> 'FAILED' OR failure_reason IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS recordings_status_updated_idx ON recordings(status, updated_at);

-- RECORDING/PROCESSING rows are a durable work queue. A media adapter captures the source,
-- transcodes it, creates the thumbnail and reports completion through the normalized API.

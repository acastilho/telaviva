CREATE TABLE IF NOT EXISTS viewing_progress (
    recording_id UUID NOT NULL REFERENCES recordings(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    position_seconds INTEGER NOT NULL DEFAULT 0 CHECK (position_seconds >= 0),
    completed BOOLEAN NOT NULL DEFAULT false,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (recording_id, user_id)
);

CREATE INDEX IF NOT EXISTS viewing_progress_history_idx
    ON viewing_progress(user_id, updated_at DESC);

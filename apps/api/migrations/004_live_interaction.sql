CREATE TABLE IF NOT EXISTS stream_interaction_settings (
    stream_id UUID PRIMARY KEY REFERENCES scheduled_streams(id) ON DELETE CASCADE,
    chat_enabled BOOLEAN NOT NULL DEFAULT true,
    questions_enabled BOOLEAN NOT NULL DEFAULT true,
    reactions_enabled BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS stream_events (
    id UUID PRIMARY KEY,
    stream_id UUID NOT NULL REFERENCES scheduled_streams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('message','question','reaction')),
    content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS stream_events_feed_idx ON stream_events(stream_id, created_at DESC);

CREATE TABLE IF NOT EXISTS stream_moderation (
    id UUID PRIMARY KEY,
    stream_id UUID NOT NULL REFERENCES scheduled_streams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    moderator_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action TEXT NOT NULL CHECK (action IN ('mute','ban')),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS stream_moderation_active_idx ON stream_moderation(stream_id, user_id, expires_at);

CREATE TABLE IF NOT EXISTS interaction_reports (
    id UUID PRIMARY KEY,
    stream_id UUID NOT NULL REFERENCES scheduled_streams(id) ON DELETE CASCADE,
    reporter_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES stream_events(id) ON DELETE CASCADE,
    reason TEXT NOT NULL CHECK (length(trim(reason)) BETWEEN 3 AND 500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (reporter_id, event_id)
);

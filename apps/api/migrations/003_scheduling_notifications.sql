CREATE TABLE IF NOT EXISTS scheduled_streams (
    id UUID PRIMARY KEY,
    creator_id UUID NOT NULL REFERENCES creator_profiles(user_id) ON DELETE CASCADE,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    description TEXT NOT NULL DEFAULT '',
    objective TEXT NOT NULL CHECK (length(trim(objective)) > 0),
    starts_at TIMESTAMPTZ NOT NULL,
    estimated_duration_minutes INTEGER NOT NULL CHECK (estimated_duration_minutes BETWEEN 5 AND 720),
    category_id UUID NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    level TEXT NOT NULL CHECK (level IN ('BEGINNER','INTERMEDIATE','ADVANCED','ALL_LEVELS')),
    price NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (price >= 0),
    access_type TEXT NOT NULL CHECK (access_type IN ('PUBLIC','FOLLOWERS')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (access_type <> 'FOLLOWERS' OR price = 0)
);
CREATE INDEX IF NOT EXISTS scheduled_streams_starts_at_idx ON scheduled_streams(starts_at);
CREATE INDEX IF NOT EXISTS scheduled_streams_creator_idx ON scheduled_streams(creator_id, starts_at);

CREATE TABLE IF NOT EXISTS creator_follows (
    follower_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    creator_id UUID NOT NULL REFERENCES creator_profiles(user_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (follower_id, creator_id),
    CHECK (follower_id <> creator_id)
);

CREATE TABLE IF NOT EXISTS stream_reminders (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stream_id UUID NOT NULL REFERENCES scheduled_streams(id) ON DELETE CASCADE,
    notify_at TIMESTAMPTZ NOT NULL,
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, stream_id)
);
CREATE INDEX IF NOT EXISTS stream_reminders_due_idx
    ON stream_reminders(notify_at) WHERE delivered_at IS NULL;

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('STREAM_SCHEDULED','STREAM_REMINDER')),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    read_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS notifications_user_feed_idx
    ON notifications(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS notifications_user_unread_idx
    ON notifications(user_id, created_at DESC) WHERE read_at IS NULL;

-- Reminders are a durable delivery queue. IN_APP is materialized by the API today;
-- future workers can add EMAIL/PUSH adapters without changing reminder semantics.

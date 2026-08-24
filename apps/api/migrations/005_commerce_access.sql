ALTER TABLE scheduled_streams DROP CONSTRAINT IF EXISTS scheduled_streams_access_type_check;
ALTER TABLE scheduled_streams DROP CONSTRAINT IF EXISTS scheduled_streams_check;
ALTER TABLE scheduled_streams DROP CONSTRAINT IF EXISTS scheduled_streams_price_access_check;
UPDATE scheduled_streams SET access_type = CASE
    WHEN access_type = 'FOLLOWERS' THEN 'PRIVATE'
    WHEN price > 0 THEN 'PAID'
    ELSE 'FREE'
END;
ALTER TABLE scheduled_streams ADD CONSTRAINT scheduled_streams_access_type_check
    CHECK (access_type IN ('FREE','PAID','SUBSCRIBERS','PRIVATE'));
ALTER TABLE scheduled_streams ADD CONSTRAINT scheduled_streams_price_access_check
    CHECK ((access_type = 'PAID' AND price > 0) OR (access_type <> 'PAID' AND price = 0));

CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY,
    creator_id UUID NOT NULL REFERENCES creator_profiles(user_id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('CLASS','SUBSCRIPTION')),
    stream_id UUID REFERENCES scheduled_streams(id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    price NUMERIC(10,2) NOT NULL CHECK (price > 0),
    currency CHAR(3) NOT NULL,
    subscription_days INTEGER CHECK (subscription_days BETWEEN 1 AND 366),
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK ((kind = 'CLASS') = (stream_id IS NOT NULL)),
    CHECK ((kind = 'SUBSCRIPTION') = (subscription_days IS NOT NULL)),
    UNIQUE (stream_id)
);

CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    amount NUMERIC(10,2) NOT NULL CHECK (amount > 0),
    currency CHAR(3) NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING','PAID','CANCELLED','REFUNDED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS orders_user_idx ON orders(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE RESTRICT,
    provider TEXT NOT NULL,
    provider_reference TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('SUCCEEDED','FAILED','REFUNDED')),
    amount NUMERIC(10,2) NOT NULL CHECK (amount > 0),
    currency CHAR(3) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, provider_reference)
);

CREATE TABLE IF NOT EXISTS entitlements (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('STREAM','CREATOR_SUBSCRIPTION')),
    resource_id UUID NOT NULL,
    source_order_id UUID REFERENCES orders(id) ON DELETE RESTRICT,
    starts_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    CHECK (expires_at IS NULL OR expires_at > starts_at)
);
CREATE UNIQUE INDEX IF NOT EXISTS entitlements_active_resource_idx
    ON entitlements(user_id, kind, resource_id) WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS stream_invites (
    stream_id UUID NOT NULL REFERENCES scheduled_streams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    invited_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (stream_id, user_id)
);

-- Preserve the audience of legacy followers-only streams as explicit invitations.
INSERT INTO stream_invites (stream_id,user_id,invited_by)
SELECT s.id,f.follower_id,s.creator_id
FROM scheduled_streams s
JOIN creator_follows f ON f.creator_id=s.creator_id
WHERE s.access_type='PRIVATE'
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS stream_accesses (
    id UUID PRIMARY KEY,
    stream_id UUID NOT NULL REFERENCES scheduled_streams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    granted BOOLEAN NOT NULL,
    reason TEXT NOT NULL,
    entitlement_id UUID REFERENCES entitlements(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS stream_accesses_audit_idx
    ON stream_accesses(stream_id, user_id, created_at DESC);

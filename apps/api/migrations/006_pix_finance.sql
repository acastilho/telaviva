CREATE TABLE IF NOT EXISTS pix_charges (
    id UUID PRIMARY KEY,
    payer_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    creator_id UUID NOT NULL REFERENCES creator_profiles(user_id) ON DELETE RESTRICT,
    purpose TEXT NOT NULL CHECK (purpose IN ('TIP','CLASS_PURCHASE')),
    order_id UUID REFERENCES orders(id) ON DELETE RESTRICT,
    provider TEXT NOT NULL,
    provider_reference TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING','SUCCEEDED','FAILED','EXPIRED','REFUNDED')),
    amount NUMERIC(10,2) NOT NULL CHECK (amount > 0),
    currency CHAR(3) NOT NULL CHECK (currency = 'BRL'),
    pix_copy_paste TEXT,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK ((purpose = 'CLASS_PURCHASE') = (order_id IS NOT NULL)),
    UNIQUE (provider, provider_reference)
);
CREATE UNIQUE INDEX IF NOT EXISTS pix_charges_active_order_idx
    ON pix_charges(order_id) WHERE order_id IS NOT NULL AND status IN ('PENDING','SUCCEEDED');

CREATE TABLE IF NOT EXISTS payment_webhook_events (
    provider TEXT NOT NULL,
    event_id TEXT NOT NULL,
    charge_id UUID NOT NULL REFERENCES pix_charges(id) ON DELETE RESTRICT,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (provider, event_id)
);

CREATE TABLE IF NOT EXISTS withdrawals (
    id UUID PRIMARY KEY,
    creator_id UUID NOT NULL REFERENCES creator_profiles(user_id) ON DELETE RESTRICT,
    amount NUMERIC(10,2) NOT NULL CHECK (amount > 0),
    currency CHAR(3) NOT NULL CHECK (currency = 'BRL'),
    destination_reference TEXT NOT NULL CHECK (destination_reference LIKE 'dest\_%'),
    status TEXT NOT NULL CHECK (status IN ('REQUESTED','PROCESSING','PAID','FAILED')),
    provider_reference TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS financial_entries (
    id UUID PRIMARY KEY,
    creator_id UUID NOT NULL REFERENCES creator_profiles(user_id) ON DELETE RESTRICT,
    charge_id UUID REFERENCES pix_charges(id) ON DELETE RESTRICT,
    withdrawal_id UUID REFERENCES withdrawals(id) ON DELETE RESTRICT,
    kind TEXT NOT NULL CHECK (kind IN (
        'GROSS_CREDIT','PLATFORM_FEE','CREATOR_CREDIT','WITHDRAWAL_DEBIT','REFUND_DEBIT'
    )),
    amount NUMERIC(10,2) NOT NULL CHECK (amount <> 0),
    currency CHAR(3) NOT NULL CHECK (currency = 'BRL'),
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK ((charge_id IS NOT NULL)::int + (withdrawal_id IS NOT NULL)::int = 1)
);
CREATE INDEX IF NOT EXISTS financial_entries_creator_idx
    ON financial_entries(creator_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS financial_entries_charge_kind_idx
    ON financial_entries(charge_id, kind)
    WHERE charge_id IS NOT NULL AND kind <> 'REFUND_DEBIT';

CREATE TABLE learning_paths (
    id UUID PRIMARY KEY,
    creator_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(160) NOT NULL,
    description VARCHAR(4000) NOT NULL DEFAULT '',
    level VARCHAR(20) NOT NULL CHECK (level IN ('BEGINNER','INTERMEDIATE','ADVANCED','ALL_LEVELS')),
    price NUMERIC(10,2) CHECK (price IS NULL OR price >= 0),
    published BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE learning_path_modules (
    id UUID PRIMARY KEY,
    path_id UUID NOT NULL REFERENCES learning_paths(id) ON DELETE CASCADE,
    title VARCHAR(160) NOT NULL,
    description VARCHAR(2000) NOT NULL DEFAULT '',
    position INTEGER NOT NULL CHECK (position >= 0),
    UNIQUE (path_id, position)
);

CREATE TABLE learning_path_lessons (
    id UUID PRIMARY KEY,
    module_id UUID NOT NULL REFERENCES learning_path_modules(id) ON DELETE CASCADE,
    recording_id UUID NOT NULL REFERENCES recordings(id) ON DELETE RESTRICT,
    title VARCHAR(160) NOT NULL,
    description VARCHAR(2000) NOT NULL DEFAULT '',
    position INTEGER NOT NULL CHECK (position >= 0),
    UNIQUE (module_id, position),
    UNIQUE (module_id, recording_id)
);

CREATE TABLE learning_path_progress (
    lesson_id UUID NOT NULL REFERENCES learning_path_lessons(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    completed BOOLEAN NOT NULL DEFAULT false,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (lesson_id, user_id)
);

CREATE INDEX learning_paths_catalog_idx ON learning_paths(published, created_at DESC);
CREATE INDEX learning_path_progress_user_idx ON learning_path_progress(user_id, updated_at DESC);

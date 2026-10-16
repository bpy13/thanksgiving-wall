-- Runs only when the Postgres volume is created for the first time.
-- For an existing database, run migrations/ instead (see README).

-- Make Hong Kong time the default for every future session on this database.
-- (A plain SET would only last for this script's session.)
DO $$
BEGIN
    EXECUTE format('ALTER DATABASE %I SET timezone = %L', current_database(), 'Asia/Hong_Kong');
END
$$;

CREATE TABLE IF NOT EXISTS messages (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    message TEXT NOT NULL,
    has_image BOOLEAN NOT NULL DEFAULT FALSE,
    user_name TEXT,
    group_name TEXT,
    event TEXT,
    upload_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS messages_upload_time_idx ON messages (upload_time DESC);

-- One row per photo, linked to the message it was posted with.
CREATE TABLE IF NOT EXISTS images (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    message_id BIGINT NOT NULL REFERENCES messages (id) ON DELETE CASCADE,
    image BYTEA NOT NULL
);

CREATE INDEX IF NOT EXISTS images_message_id_idx ON images (message_id);

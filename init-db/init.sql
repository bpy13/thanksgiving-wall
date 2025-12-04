CREATE TABLE IF NOT EXISTS messages (
    message TEXT NOT NULL,
    image BYTEA,
    user_name TEXT,
    group_name TEXT,
    event TEXT,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
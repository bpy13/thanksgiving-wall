SET timezone = 'Asia/Hong_Kong';

CREATE TABLE IF NOT EXISTS messages (
    message TEXT NOT NULL,
    has_image BOOLEAN,
    user_name TEXT,
    group_name TEXT,
    event TEXT,
    upload_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS images (
    message TEXT NOT NULL,
    image BYTEA,
    user_name TEXT,
    group_name TEXT,
    event TEXT,
    upload_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

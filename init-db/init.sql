CREATE TABLE IF NOT EXISTS messages (
    message TEXT NOT NULL,
    user_name TEXT,
    group_name TEXT,
    event TEXT,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS images (
    message TEXT NOT NULL,
    image BYTEA,
    user_name TEXT,
    group_name TEXT,
    event TEXT,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS display (
    message_start_index INT,
    message_end_index INT,
    image_start_index INT,
    image_end_index INT
);
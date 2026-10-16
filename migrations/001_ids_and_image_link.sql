-- Migration 001: add id primary keys and link images to their message.
--
-- For databases created before 2026-10-16 (old init.sql). Keeps every existing row.
-- Safe to run twice: the second run does nothing.
--
-- Old schema: messages and images had no ids; each images row repeated the message text,
-- name, group, event and upload time of its message.
-- New schema: messages(id, ...), images(id, message_id -> messages.id, image).
--
-- How old rows are matched: the old upload code inserted the message and its image in one
-- transaction, and both rows took their upload_time default from that transaction's start,
-- so a message and its image have the same upload_time and message text.
--
-- Run (from the repo folder, with the stack up; take a backup first, see README):
--   docker compose exec postgres sh -c 'psql -v ON_ERROR_STOP=1 -U $POSTGRES_USER -d $POSTGRES_DB -f /migrations/001_ids_and_image_link.sql'

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema() AND table_name = 'images'
          AND column_name = 'message_id'
    ) THEN
        RAISE NOTICE 'Migration 001 already applied; nothing to do.';
        RETURN;
    END IF;

    -- Persist Hong Kong time as the database default (the old SET only lasted one session).
    EXECUTE format('ALTER DATABASE %I SET timezone = %L', current_database(), 'Asia/Hong_Kong');

    -- 1. Give every message an id (existing rows are numbered automatically).
    ALTER TABLE messages ADD COLUMN id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY;

    -- 2. Link each image to its message.
    ALTER TABLE images ADD COLUMN message_id BIGINT;

    UPDATE images i SET message_id = (
        SELECT m.id FROM messages m
        WHERE m.upload_time = i.upload_time AND m.message = i.message
        ORDER BY m.id LIMIT 1
    );

    -- Images whose message row can't be found (not expected): recreate the message from
    -- the details stored on the image row, so no photo is lost, then link them.
    INSERT INTO messages (message, has_image, user_name, group_name, event, upload_time)
    SELECT i.message, TRUE, i.user_name, i.group_name, i.event, i.upload_time
    FROM images i WHERE i.message_id IS NULL;

    UPDATE images i SET message_id = (
        SELECT m.id FROM messages m
        WHERE m.upload_time = i.upload_time AND m.message = i.message
        ORDER BY m.id LIMIT 1
    )
    WHERE i.message_id IS NULL;

    -- 3. Tighten the tables and drop the duplicated columns from images.
    ALTER TABLE images ADD COLUMN id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY;
    DELETE FROM images WHERE image IS NULL;  -- empty rows carried no photo
    ALTER TABLE images
        ALTER COLUMN message_id SET NOT NULL,
        ALTER COLUMN image SET NOT NULL,
        ADD CONSTRAINT images_message_id_fkey
            FOREIGN KEY (message_id) REFERENCES messages (id) ON DELETE CASCADE,
        DROP COLUMN message,
        DROP COLUMN user_name,
        DROP COLUMN group_name,
        DROP COLUMN event,
        DROP COLUMN upload_time;

    -- 4. has_image was set true even when the file was not a valid image; correct it from
    --    whether a photo is actually stored.
    UPDATE messages m SET has_image = EXISTS (SELECT 1 FROM images i WHERE i.message_id = m.id);
    UPDATE messages SET upload_time = CURRENT_TIMESTAMP WHERE upload_time IS NULL;
    ALTER TABLE messages
        ALTER COLUMN has_image SET DEFAULT FALSE,
        ALTER COLUMN has_image SET NOT NULL,
        ALTER COLUMN upload_time SET NOT NULL;

    CREATE INDEX IF NOT EXISTS messages_upload_time_idx ON messages (upload_time DESC);
    CREATE INDEX IF NOT EXISTS images_message_id_idx ON images (message_id);

    RAISE NOTICE 'Migration 001 applied.';
END
$$;

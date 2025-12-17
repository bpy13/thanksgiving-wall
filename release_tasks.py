import os
import psycopg

database_url = os.getenv("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

with psycopg.connect(database_url) as conn:
    with conn.cursor() as cur:
        cur.execute("""SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'messages'
        );""")
        tables_exist = cur.fetchone()[0]
        if not tables_exist:
            with open('init-db/init.sql', 'r') as f:
                cur.execute(f.read())
            conn.commit()

#!/bin/bash
# Release phase tasks - runs before each deployment

set -e

echo "Running release tasks..."

# Initialize database schema if tables don't exist
python3 - <<'EOF'
import os
import psycopg

database_url = os.getenv("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

print("Connecting to database...")
with psycopg.connect(database_url) as conn:
    with conn.cursor() as cur:
        # Check if tables exist
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'messages'
            );
        """)
        tables_exist = cur.fetchone()[0]
        
        if not tables_exist:
            print("Initializing database schema...")
            with open('init-db/init.sql', 'r') as f:
                cur.execute(f.read())
            conn.commit()
            print("Database schema initialized successfully!")
        else:
            print("Database schema already exists, skipping initialization.")

print("Release tasks completed successfully!")
EOF

import sqlite3
import os

db_paths = [
    "resume_ranker.db",
    "backend/resume_ranker.db"
]

for db in db_paths:
    if os.path.exists(db):
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(match_results);")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"Columns in {db}:", columns)
        if "raw_cosine" not in columns:
            print(f"Adding raw_cosine to {db}...")
            cursor.execute("ALTER TABLE match_results ADD COLUMN raw_cosine REAL DEFAULT 0.0;")
            conn.commit()
            print("Added raw_cosine successfully.")
        conn.close()

# db.py
import os
import psycopg2
from psycopg2.extras import execute_batch, RealDictCursor
from datetime import datetime
import pandas as pd

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")

def get_connection():
    # For GitHub Actions Postgres service, sslmode not required
    return psycopg2.connect(DATABASE_URL)

def ensure_schema():
    with get_connection() as conn:
        with conn.cursor() as cur:
            sql = open("schema.sql", "r", encoding="utf-8").read()
            cur.execute(sql)
        conn.commit()

def upsert_repository(repo):
    """
    repo: dict with keys repo_id, owner, name, full_name, url, stars, forks, language, description, created_at
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO repositories (repo_id, name, owner, full_name, url, stars, forks, language, description, created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
            ON CONFLICT (repo_id) DO UPDATE
              SET stars = EXCLUDED.stars,
                  forks = EXCLUDED.forks,
                  language = EXCLUDED.language,
                  description = EXCLUDED.description,
                  updated_at = now();
            """, (
                repo.get("repo_id"),
                repo.get("name"),
                repo.get("owner"),
                repo.get("full_name"),
                repo.get("url"),
                repo.get("stars"),
                repo.get("forks"),
                repo.get("language"),
                repo.get("description"),
                repo.get("created_at")
            ))

            # append history
            cur.execute("INSERT INTO stars_history (repo_id, stars, fetched_at) VALUES (%s, %s, now())",
                        (repo.get("repo_id"), repo.get("stars")))
        conn.commit()

def bulk_upsert(repos):
    if not repos:
        return
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Use execute_batch for moderate bulk performance
            insert_repo = """
            INSERT INTO repositories (repo_id, name, owner, full_name, url, stars, forks, language, description, created_at, updated_at)
            VALUES (%(repo_id)s, %(name)s, %(owner)s, %(full_name)s, %(url)s, %(stars)s, %(forks)s, %(language)s, %(description)s, %(created_at)s, now())
            ON CONFLICT (repo_id) DO UPDATE
              SET stars = EXCLUDED.stars,
                  forks = EXCLUDED.forks,
                  language = EXCLUDED.language,
                  description = EXCLUDED.description,
                  updated_at = now();
            """
            execute_batch(cur, insert_repo, repos, page_size=100)

            history_rows = [(r['repo_id'], r['stars']) for r in repos]
            execute_batch(cur, "INSERT INTO stars_history (repo_id, stars) VALUES (%s, %s)", history_rows, page_size=200)
        conn.commit()

def save_checkpoint(partition_key, end_cursor, fetched_count):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO crawl_checkpoints (partition_key, end_cursor, fetched_count, updated_at)
            VALUES (%s, %s, %s, now())
            ON CONFLICT (partition_key) DO UPDATE
              SET end_cursor = EXCLUDED.end_cursor,
                  fetched_count = crawl_checkpoints.fetched_count + EXCLUDED.fetched_count,
                  updated_at = now();
            """, (partition_key, end_cursor, fetched_count))
        conn.commit()

def get_checkpoint(partition_key):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT end_cursor, fetched_count FROM crawl_checkpoints WHERE partition_key = %s", (partition_key,))
            row = cur.fetchone()
            return row or {"end_cursor": None, "fetched_count": 0}

def dump_to_csv(path="repos_dump.csv"):
    # pandas prefers SQLAlchemy but this will continue to work (warning is OK)
    with get_connection() as conn:
        df = pd.read_sql("SELECT * FROM repositories", conn)
        df.to_csv(path, index=False)

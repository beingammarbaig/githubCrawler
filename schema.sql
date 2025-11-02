-- repositories: latest snapshot
CREATE TABLE IF NOT EXISTS repositories (
  repo_id TEXT PRIMARY KEY,
  name TEXT,
  owner TEXT,
  full_name TEXT,
  url TEXT,
  stars INTEGER,
  forks INTEGER,
  language TEXT,
  description TEXT,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- append-only star history for time series
CREATE TABLE IF NOT EXISTS stars_history (
  id BIGSERIAL PRIMARY KEY,
  repo_id TEXT REFERENCES repositories(repo_id) ON DELETE CASCADE,
  stars INTEGER,
  fetched_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_stars_history_repo_id ON stars_history(repo_id);

-- checkpoint table for resumable crawl (cursor per partition)
CREATE TABLE IF NOT EXISTS crawl_checkpoints (
  partition_key TEXT PRIMARY KEY,
  end_cursor TEXT,
  fetched_count BIGINT DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT now()
);

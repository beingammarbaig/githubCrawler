# crawler.py
import os, time, math, requests, json
from datetime import datetime, timedelta
from db import ensure_schema, bulk_upsert, save_checkpoint, get_checkpoint, dump_to_csv

GITHUB_GRAPHQL = "https://api.github.com/graphql"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")  # provided automatically in Actions via secrets.GITHUB_TOKEN
HEADERS = {"Authorization": f"bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}

# GraphQL template: uses fragment for Repository
GRAPHQL_SEARCH = """
query ($q: String!, $cursor: String) {
  rateLimit {
    limit
    cost
    remaining
    resetAt
  }
  search(query: $q, type: REPOSITORY, first: 100, after: $cursor) {
    repositoryCount
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        ... on Repository {
          id
          databaseId
          name
          owner { login }
          url
          stargazerCount
          forkCount
          primaryLanguage { name }
          description
          createdAt
        }
      }
    }
  }
}
"""

def graphql_post(query, variables=None, max_retries=6):
    variables = variables or {}
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.post(GITHUB_GRAPHQL, headers=HEADERS, json={"query": query, "variables": variables}, timeout=30)
            r.raise_for_status()
            data = r.json()
            # if GitHub returns errors, propagate
            if "errors" in data:
                return {"errors": data["errors"]}
            return data
        except requests.exceptions.RequestException as e:
            wait = min(60, 2 ** attempt)
            print(f"[HTTP] attempt {attempt} error: {e}. retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError("Failed GraphQL post after retries")

def parse_repo_node(node):
    n = node.get("databaseId") or node.get("id")
    repo_id = str(n)
    return {
        "repo_id": repo_id,
        "name": node.get("name"),
        "owner": node.get("owner", {}).get("login"),
        "full_name": f"{node.get('owner', {}).get('login')}/{node.get('name')}",
        "url": node.get("url"),
        "stars": node.get("stargazerCount") or 0,
        "forks": node.get("forkCount") or 0,
        "language": (node.get("primaryLanguage") or {}).get("name"),
        "description": node.get("description"),
        "created_at": node.get("createdAt")
    }

def fetch_partition_count(query):
    # Query repositoryCount quickly by requesting first:1 and reading repositoryCount
    data = graphql_post(GRAPHQL_SEARCH, {"q": query, "cursor": None})
    if data is None or "errors" in data:
        raise RuntimeError(f"Error fetching count: {data.get('errors') if data else 'no data'}")
    return data["data"]["search"]["repositoryCount"]

def crawl_partition(partition_key, query, max_from_partition):
    """
    Crawl a single partition (e.g., 'created:2023-01-01..2023-01-07')
    partition_key: unique string for checkpointing
    query: full search query string
    max_from_partition: total repos to fetch from this partition (upper bound)
    """
    print(f"[PART] start partition={partition_key} max={max_from_partition}")
    checkpoint = get_checkpoint(partition_key)
    cursor = checkpoint.get("end_cursor")
    already = checkpoint.get("fetched_count") or 0
    fetched = already
    batch = []
    batch_size = 50

    while fetched < max_from_partition:
        variables = {"q": query, "cursor": cursor}
        data = graphql_post(GRAPHQL_SEARCH, variables)
        if "errors" in data:
            print("[ERR] GraphQL errors:", data["errors"])
            time.sleep(10)
            continue

        # Rate limit handling
        rl = data.get("data", {}).get("rateLimit")
        if rl:
            rem = rl.get("remaining", 0)
            reset = rl.get("resetAt")
            if rem is not None and rem < 10:
                reset_ts = datetime.fromisoformat(reset.replace("Z", "+00:00"))
                wait = max(5, (reset_ts - datetime.utcnow()).total_seconds() + 5)
                print(f"[RATE] remaining={rem}. sleeping {int(wait)}s until reset {reset}")
                time.sleep(wait)
                continue

        search = data["data"]["search"]
        edges = search.get("edges", [])
        for e in edges:
            node = e.get("node") or {}
            repo = parse_repo_node(node)
            batch.append(repo)
            fetched += 1

            if len(batch) >= batch_size:
                bulk_upsert(batch)
                save_checkpoint(partition_key, cursor, len(batch))
                print(f"[DB] upserted {len(batch)} rows (fetched {fetched})")
                batch = []

            if fetched >= max_from_partition:
                break

        pageInfo = search.get("pageInfo", {})
        if pageInfo.get("hasNextPage"):
            cursor = pageInfo.get("endCursor")
        else:
            # flush batch then break
            if batch:
                bulk_upsert(batch)
                save_checkpoint(partition_key, cursor, len(batch))
                print(f"[DB] upserted final {len(batch)} rows for partition")
                batch = []
            break

        # polite pause
        time.sleep(0.5)

    print(f"[PART] done partition={partition_key} fetched={fetched}")
    return fetched

def partition_and_crawl(total_target=100000):
    """
    Partition strategy: split by created date window (day/week) until repositoryCount <= 1000 per partition.
    Simpler heuristic: iterate recent years and weeks until we gather total_target.
    """
    # Example: crawl recent 5 years weekly until total_target reached
    end = datetime.utcnow().date()
    start = end - timedelta(days=365*5)  # 5 years back
    current = start
    collected = 0

    while current < end and collected < total_target:
        window_days = 7  # weekly
        window_start = current
        window_end = min(end, current + timedelta(days=window_days - 1))
        created_range = f"created:{window_start.isoformat()}..{window_end.isoformat()}"
        query_base = f"stars:>0 language:Python {created_range}"

        try:
            count = fetch_partition_count(query_base)
        except Exception as e:
            print("[WARN] failed to get partition count:", e)
            # fallback: assume small count and try crawling this week
            count = 1000

        # If count > 1000, we might need smaller window
        if count > 1000 and window_days > 1:
            # split into single-day windows (simple fallback)
            window_days = 1
            window_end = window_start
            created_range = f"created:{window_start.isoformat()}..{window_end.isoformat()}"
            query_base = f"stars:>0 language:Python {created_range}"
            try:
                count = fetch_partition_count(query_base)
            except:
                count = min(1000, count)

        # set limit for partition to avoid chasing too many for one partition
        to_fetch = min(count, total_target - collected)

        partition_key = f"{window_start.isoformat()}_{window_end.isoformat()}"
        fetched = crawl_partition(partition_key, query_base, to_fetch)
        collected += fetched

        print(f"[AGG] total collected so far: {collected}/{total_target}")

        # move to next window
        current = window_end + timedelta(days=1)

    print(f"[DONE] Completed partitioned crawl: collected {collected}")
    return collected

if __name__ == "__main__":
    ensure_schema()
    # target default 100000; for CI runs you may set a lower value via env CRAWL_TARGET
    target = int(os.environ.get("CRAWL_TARGET", "100000"))
    print(f"[MAIN] target={target}")
    total = partition_and_crawl(target)
    dump_to_csv("repos_dump.csv")
    print("[MAIN] done, CSV written repos_dump.csv")

# GitHub Crawle Simple

A small Python crawler using GitHub’s GraphQL API to collect repository stars and store them in PostgreSQL.

## How it works
- Uses GitHub GraphQL API
- Stores repo data in Postgres
- Runs daily with GitHub Actions
- Uploads a CSV artifact of crawled data

## Run locally
```bash
pip install -r requirements.txt
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/postgres"
export GITHUB_TOKEN="ghp_xxx"
python crawler.py

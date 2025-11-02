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
# 🚀 GitHub Stars Crawler

A fully automated GitHub repository crawler using the **GraphQL API** that collects and stores repository star data in **PostgreSQL**, runs via **GitHub Actions**, and exports the results as a **CSV artifact**.

---

## ⚙️ Overview

- Fetches data of **100,000 repositories** using GitHub’s GraphQL API  
- Stores results in a **PostgreSQL database** with a flexible schema  
- Uses **cursor-based pagination** and **rate-limit handling**  
- Runs **daily at 03:00 UTC** via GitHub Actions or manually  
- Exports data to **`repos_dump.csv`** as a downloadable artifact  

---

## 🧩 Workflow Summary

| Step                 | Description                                     |
|----------------------|-------------------------------------------------|
| PostgreSQL Service   | Creates temporary Postgres container            |
| Checkout Repo        | Pulls source code into the runner               |
| Setup Python         | Installs Python 3.10 and dependencies           |
| Initialize Schema    | Creates required DB tables                      |
| Run Crawler          | Fetches repo stars using GraphQL API            |
| Dump & Upload CSV    | Saves database data as CSV artifact             |

Each run is stateless, self-contained, and reproducible.

---

## 🗄️ Database Schema

```sql
CREATE TABLE IF NOT EXISTS repositories (
  id SERIAL PRIMARY KEY,
  repo_id BIGINT UNIQUE,
  name TEXT,
  owner TEXT,
  stars INTEGER,
  fetched_at TIMESTAMP DEFAULT NOW()
);


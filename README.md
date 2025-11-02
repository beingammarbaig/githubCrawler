# GitHub Crawle Simple

A small Python crawler using GitHub’s GraphQL API to collect repository stars and store them in PostgreSQL.

## How it works
- Uses GitHub GraphQL API
- Stores repo data in Postgres
- Runs daily with GitHub Actions
- Uploads a CSV artifact of crawled data

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
```
## 🧠 Software Design

- **crawler.py** → Handles only fetching repository data  
- **db.py** → Handles schema creation, inserts, and CSV dumps  
- **crawl.yml** → Automates the workflow in GitHub Actions  

Follows **separation of concerns**, immutability of configuration, and clean architecture principles. Each run is independent and stateless.

---

## ⚡ Scaling for 500M Repositories

| Area       | Current          | Scaled                         |
|------------|-----------------|--------------------------------|
| Storage    | Single Postgres  | Sharded / Cloud DB            |
| Crawling   | Single-threaded  | Distributed workers           |
| API        | Single token     | Multiple tokens / async       |
| Updates    | Full refresh     | Incremental deltas            |

---

## 🧬 Future Schema Example

```sql
CREATE TABLE issues (
  id SERIAL PRIMARY KEY,
  repo_id BIGINT REFERENCES repositories(repo_id),
  issue_number INT,
  comments_count INT,
  updated_at TIMESTAMP
);
```
```sql
INSERT INTO issues (...) VALUES (...)
ON CONFLICT (repo_id, issue_number) DO UPDATE
SET comments_count = EXCLUDED.comments_count,
    updated_at = EXCLUDED.updated_at;
```

---

## 🧰 Tech Stack

| Component | Tool |
|------------|------|
| **Language** | Python 3.10 |
| **API** | GitHub GraphQL |
| **Database** | PostgreSQL |
| **CI/CD** | GitHub Actions |
| **Output** | CSV Artifact |

---

## ✅ Deliverables

- PostgreSQL service container ✅  
- Schema creation ✅  
- Crawling 100k repositories ✅  
- Data dump & artifact upload ✅  
- Default GitHub Token used ✅  
- Successful workflow run ✅  

---

**Author:** Mirza Muhammad Ammar Baig  
**Role:** Software Engineer – GitHub Crawler Assignment

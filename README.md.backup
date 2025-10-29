<div align="center"><h1 align="center">🧠 Notion-X Scheduler</h1>

  <h1>AI Content Scheduler</h1><p align="center">

  <p><strong>Enterprise AI News → X & LinkedIn Automation</strong></p>  <i>Daily AI news → summarized → queued in Notion → posted to X (Twitter) — fully automated.</i>

  <p>RSS → GPT-4o-mini → Notion → GitHub Actions → X + LinkedIn</p></p>

</div>

<p align="center">

![Python](https://img.shields.io/badge/Python-3.11-yellow?style=for-the-badge&logo=python)  <img src="https://img.shields.io/badge/version-v1.0.0-blue?style=for-the-badge"/>

![OpenAI](https://img.shields.io/badge/OpenAI-gpt--4o--mini-2ea44f?style=for-the-badge&logo=openai)  <img src="https://img.shields.io/github/actions/workflow/status/skalaliya/notion-x-scheduler/fetch.yml?label=AI%20Fetcher&style=for-the-badge"/>

![Notion](https://img.shields.io/badge/Notion-API-black?style=for-the-badge&logo=notion)  <img src="https://img.shields.io/github/actions/workflow/status/skalaliya/notion-x-scheduler/post.yml?label=X%20Poster&style=for-the-badge"/>

![X](https://img.shields.io/badge/X-API-000000?style=for-the-badge&logo=x)  <img src="https://img.shields.io/badge/OpenAI-gpt--4o--mini-2ea44f?style=for-the-badge&logo=openai"/>

![LinkedIn](https://img.shields.io/badge/LinkedIn-API-0A66C2?style=for-the-badge&logo=linkedin)  <img src="https://img.shields.io/badge/Notion-API-black?style=for-the-badge&logo=notion"/>

  <img src="https://img.shields.io/badge/Python-3.11-yellow?style=for-the-badge&logo=python"/>

---</p>



## Overview---



This repo **automatically curates, summarizes, and posts** the freshest AI news to **X (Twitter) and LinkedIn** — fully managed via **Notion** and **GitHub Actions**.## Overview



- **<6h old news** gets +15 pointsThis repo automatically curates and posts AI news to X (Twitter) using an efficient two-stage pipeline:

- **Duplicate prevention** (7-day Notion history)

- **Source diversity** (no single feed dominates)1. **Fetcher** runs once daily at ~10:05 AM Europe/Paris time (DST-aware), parses 7 trusted AI RSS feeds, scores articles by relevance and recency, summarizes the top pick with OpenAI's `gpt-4o-mini`, and queues it in your Notion database with `Status=Scheduled`.

- **OpenAI fallback** if API fails

- **Full observability** in Notion + Actions logs2. **Poster** runs at ~10:10 AM (5 minutes after fetcher) to publish queued content. Also triggers immediately when fetcher completes successfully via event-chaining for zero-delay posting.



**Built and maintained by:** Algorythmos**Built and maintained by:** @skalaliya



------



## Workflow## Architecture



```mermaid```mermaid

graph LRgraph TD

    A[10:05 AM] --> B[fetch_ai_news.py]    A[AI RSS Feeds] --> B[fetch_ai_news.py]

    B --> C[Score & Summarize]    B -->|Summarize with gpt-4o-mini| C[Notion DB]

    C --> D[Write to Notion: Scheduled]    C -->|Status=Scheduled & Time ready| D[X Poster]

    D --> E[10:10 AM: main.py]    D -->|X API| E[Tweet Published 🚀]

    E --> F[Post to X]```

    E --> G[Post to LinkedIn]

    F & G --> H[Update Notion: Posted + URLs]---

```

## Features

---

* 📰 **Multi-source AI feeds** (OpenAI, Google AI, DeepMind, NVIDIA, AWS ML, TechCrunch, VentureBeat)

## Setup (GitHub Secrets)* 🧠 **Smart summarization** with `gpt-4o-mini` (cost-effective, high-quality) — graceful fallback to heuristics

* 🗂️ **Notion as content queue** (`Status=Scheduled` + `Scheduled Time` properties)

| Secret | Description |* ⏰ **DST-aware scheduling**: Runs once daily at ~10:05 AM Paris time year-round (dual UTC crons)

|--------|-------------|* 🔁 **Event-chained workflows**: Poster auto-triggers after successful fetch for instant publishing

| `NOTION_TOKEN` | Notion Internal Integration Token |* 🛡️ **Pre-check validation**: Skips poster run if no ready posts exist (saves compute minutes)

| `NOTION_DB_ID` | Database ID for posts |* 🧪 **Dry-run mode**: Test with `--dry-run` flag or workflow dispatch for JSON output

| `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET` | X Developer App |* 🎯 **Relevance scoring**: Keyword matching + recency decay (48h window)

| `LINKEDIN_ACCESS_TOKEN` | LinkedIn API (User-to-Organization) |* 💰 **Compute-optimized**: ~45 minutes/month usage (2% of GitHub free tier)

| `OPENAI_API_KEY` | OpenAI API Key |

---

---

## Quick Start

## Run Locally

### 1. Setup Secrets

```bash

pip install -r requirements.txtNavigate to **GitHub → Settings → Secrets → Actions** and add:

python fetch_ai_news.py --dry-run

```**Required:**

* `NOTION_TOKEN` - Your Notion integration token

---* `NOTION_DB_ID` - Target database ID

* `ACCESS_TOKEN`, `ACCESS_TOKEN_SECRET` - X/Twitter OAuth tokens

## Features* `API_KEY`, `API_KEY_SECRET` - X/Twitter API credentials



* 📰 **Multi-source AI feeds** (OpenAI, Google AI, DeepMind, NVIDIA, AWS ML, TechCrunch, VentureBeat)**Optional:**

* 🧠 **Smart summarization** with `gpt-4o-mini` (cost-effective, high-quality) — graceful fallback to heuristics* `OPENAI_API_KEY` - Enables AI summarization (without it, uses heuristic fallback)

* 🗂️ **Notion as content queue** (`Status=Scheduled` + `Scheduled Time` properties)* `OPENAI_MODEL` - Override model (default: `gpt-4o-mini`)

* 🎯 **Relevance scoring**: Keyword matching + recency decay (48h window, <6h gets +15 points)

* 🔄 **Dual platform posting**: Automatically posts to both X (Twitter) and LinkedIn### 2. Test Locally (Dry Run)

* 🔗 **URL tracking**: Stores tweet_url and linkedin_url back in Notion after posting

* 🛡️ **Duplicate prevention**: 7-day Notion history check```bash

* 💰 **Compute-optimized**: ~60 minutes/month usage (3% of GitHub free tier)python fetch_ai_news.py --dry-run

```

---

Expected output: JSON with top article details or "No fresh items (≤48h); Skipped."

## Scheduling

### 3. Run in Production

Both workflows use **dual UTC cron schedules** to maintain consistent Paris local time:

**Option A: Manual trigger**

**Fetcher Schedule:*** Go to **Actions → AI Content Fetcher → Run workflow**

* **Mar–Oct (CEST, UTC+2)**: `5 8 * 3-10 *` → 08:05 UTC = 10:05 Paris* Set `dry_run=false`

* **Nov–Feb (CET, UTC+1)**: `5 9 * 11,12,1,2 *` → 09:05 UTC = 10:05 Paris* Click **Run**



**Poster Schedule:****Option B: Automatic schedule**

* **Mar–Oct (CEST, UTC+2)**: `10 8 * 3-10 *` → 08:10 UTC = 10:10 Paris* Fetcher runs daily at ~10:05 AM Europe/Paris time

* **Nov–Feb (CET, UTC+1)**: `10 9 * 11,12,1,2 *` → 09:10 UTC = 10:10 Paris* Poster runs at ~10:10 AM (5 min buffer) or immediately after fetch completes



The 5-minute gap ensures Notion writes complete before posting.### 4. Monitor Execution



---* **Fetcher**: Creates 1 `Status=Scheduled` row in Notion per run (if news found)

* **Poster**: Publishes scheduled posts and updates their status

## Algorythmos Integration* Check **Actions** tab for workflow logs and status



- Plug into **Document Intelligence** for image tweets---

- Monitor engagement via **MLOps-Algorythmos**

- Scale to 100+ accounts with org-level secrets## How It Works



---### Scheduling (DST-Aware & Compute-Optimized)



## Project StructureBoth workflows use **dual UTC cron schedules** to maintain consistent Paris local time while minimizing compute usage:



```**Fetcher Schedule:**

algorythmos-ai-content-scheduler/* **Mar–Oct (CEST, UTC+2)**: `5 8 * 3-10 *` → 08:05 UTC = 10:05 Paris

├── fetch_ai_news.py          # AI news fetcher (RSS → scoring → summarize → Notion)* **Nov–Feb (CET, UTC+1)**: `5 9 * 11,12,1,2 *` → 09:05 UTC = 10:05 Paris

├── main.py                   # X/Twitter & LinkedIn poster (Notion → Social APIs)

├── check_ready_to_post.py    # Pre-check validation for poster**Poster Schedule:**

├── requirements.txt          # Python dependencies* **Mar–Oct (CEST, UTC+2)**: `10 8 * 3-10 *` → 08:10 UTC = 10:10 Paris

├── .github/workflows/* **Nov–Feb (CET, UTC+1)**: `10 9 * 11,12,1,2 *` → 09:10 UTC = 10:10 Paris

│   ├── fetch.yml            # Daily at 10:05 Paris (DST-aware)

│   └── post.yml             # Daily at 10:10 Paris (X + LinkedIn)The 5-minute gap ensures Notion writes complete before posting. GitHub Actions only supports UTC cron, so this dual-schedule approach automatically handles daylight saving transitions.

└── README.md                # This file

```### Workflow Chain



---```

Daily at 10:05 Paris

## Costs (typical)       ↓

[AI Content Fetcher]

| Service              | Monthly | Notes                          |       ↓ (writes to Notion)

|----------------------|---------|--------------------------------|       ↓ (5-min buffer)

| GitHub Actions       | **Free** | ~60 min/month (3% of free tier) |[X Poster at 10:10] ← also triggers immediately on fetch success

| OpenAI `gpt-4o-mini` |  <$0.01 | ~1 short summary/day           |       ↓

| Notion API           |    Free | Included in plan               |[check_ready_to_post.py validates Notion]

| **Total**            | **<$0.01** | Virtually free to run       |       ↓ (if posts ready)

[main.py publishes to X]

---```



## Testing**Compute Efficiency:** Both workflows run once daily = ~2 runs/day = ~60 min/month (3% of free tier)



* **LLM disabled:** Remove `OPENAI_API_KEY` → heuristic summaries activate automatically### Files

* **Model override:** Set `OPENAI_MODEL` secret to test different models

* **No news scenario:** Fetcher writes a "Skipped" row to Notion* **`fetch_ai_news.py`** (445 lines) - RSS parser, scorer, OpenAI integration, Notion writer

* **Manual dispatch:** Test anytime via Actions tab with `dry_run` toggle* **`main.py`** - X/Twitter poster with thread support

* **Dry run mode:** `python fetch_ai_news.py --dry-run` for JSON output* **`check_ready_to_post.py`** - Pre-check validation script

* **`.github/workflows/fetch.yml`** - Fetcher workflow (daily at 10:05 Paris, DST-aware)

---* **`.github/workflows/post.yml`** - Poster workflow (daily at 10:10 Paris + event-chained)



## Contributing---



PRs and issues welcome. If this helped, please ⭐ the repo.## Costs (typical)



---| Service              | Monthly | Notes                          |

| -------------------- | ------: | ------------------------------ |

## License| GitHub Actions       | **Free** | ~60 min/month (3% of free tier) |

| OpenAI `gpt-4o-mini` |  <$0.01 | ~1 short summary/day           |

MIT| Notion API           |    Free | Included in plan               |

| **Total**            | **<$0.01** | Virtually free to run       |

---

**Compute optimization:** Running once daily instead of hourly saves ~1,035 minutes/month (95% reduction)!

**France Remote Worldwide** | [algorythmos.fr](https://algorythmos.fr) | [@algorythmos](https://x.com/algorythmos)

---

## Testing Matrix

* **LLM disabled:** Remove `OPENAI_API_KEY` → heuristic summaries activate automatically
* **Model override:** Set `OPENAI_MODEL` secret to test different models (e.g., `gpt-4`, `gpt-3.5-turbo`)
* **No news scenario:** Fetcher writes a "Skipped" row to Notion (production) or prints message (dry-run)
* **Manual dispatch:** Test anytime via Actions tab with `dry_run` toggle
* **Event-chain validation:** After manual fetch, verify poster auto-triggers within seconds

---

## Project Structure

```
notion-x-scheduler/
├── fetch_ai_news.py          # AI news fetcher (RSS → scoring → summarize → Notion)
├── main.py                   # X/Twitter poster (Notion → X API)
├── check_ready_to_post.py    # Pre-check validation for poster
├── requirements.txt          # Python dependencies
├── .github/workflows/
│   ├── fetch.yml            # Daily at 10:05 Paris (DST-aware)
│   └── post.yml             # Daily at 10:10 Paris + event-chained
└── README.md                # This file
```

---

## Contributing

PRs and issues welcome. If this helped, please ⭐ the repo:
**[https://github.com/skalaliya/notion-x-scheduler](https://github.com/skalaliya/notion-x-scheduler)**

---

## License

MIT

# A10 — AI System Evaluation & Analytics Dashboard

**Project:** RewriteLab
**Repo:** https://github.com/AlikhanIllini/10_RewriteLab
**Production URL:** https://rewritelab.onrender.com/
**Dashboard path:** `/analytics-dashboard/`
**Test credentials:** `mohitg2` / `uiuc12345`

---

## Part 1 — Analytics Design

### Step 1 — Questions

**System Performance**
1. What is the end-to-end latency distribution of our AI calls (p50/p95/p99)?
2. Which AI feature (LLM rewrite, local rewrite, semantic search) is the slowest?
3. How reliable is the system — what fraction of calls succeed vs. error vs. time out?

**User Behavior**
4. Which AI features are used most often, and has their usage changed over time?
5. How long are the texts users submit (input size distribution)?
6. Which users drive the most AI traffic?

**Cost**
7. What does each request cost on average, and what is our total spend?
8. Which feature is responsible for the largest share of cost?
9. How does daily cost trend — are we trending up?

### Step 2 — Widget Design

| # | Widget | Type | Category | Question(s) | Data source |
|---|---|---|---|---|---|
| KPI | Total calls, success %, avg/p50/p95/p99 latency, total cost, total tokens, avg cost/call | Summary cards | All | 1, 3, 7 | `AICallLog` aggregates |
| 1 | **Latency Distribution** | Histogram (bar) | Performance | 1 | `latency_ms` binned into 9 buckets |
| 2 | **Avg Latency by Feature** | Horizontal bar | Performance | 2 | `AVG(latency_ms) GROUP BY feature` |
| 3 | **Call Status Breakdown** | Donut | Performance | 3 | `COUNT GROUP BY status` |
| 4 | **Feature Usage** | Bar | Behavior | 4 | `COUNT GROUP BY feature` |
| 5 | **Calls Over Time by Feature** | Multi-series line | Behavior | 4 | `COUNT GROUP BY date, feature` |
| 6 | **Input Size Distribution** | Histogram | Behavior | 5 | `input_chars` binned |
| 7 | **Cost by Feature** | Bar | Cost | 8 | `SUM(cost_usd) GROUP BY feature` |
| 8 | **Daily Cost Trend** | Area + line | Cost | 9 | `SUM(cost_usd) GROUP BY date` |
| 9 | **Top 10 Users by Cost** | Table | Behavior + Cost | 6, 7 | `SUM(cost_usd) GROUP BY user` |

**Total: 1 KPI strip (7 metrics) + 9 visualizations.** Coverage per category:
performance = 3, behavior = 3 (+ top-user table), cost = 3.

### Step 3 — Data-Science / Statistical Thinking

The dashboard goes beyond raw counts by incorporating:

- **Central tendency** — mean latency, mean cost per call.
- **Percentiles** — p50, p95, and p99 latency (Python list + `_percentile` helper) so a few slow calls don't hide behind a good average.
- **Distributions (histograms)** — latency and input size bucketed into fixed ranges to reveal shape (right-skew, tails) rather than a single number.
- **Trends over time** — daily call volume and daily cost, plotted as time series; supports anomaly / spike detection by eye.
- **Comparison across groups** — per-feature breakdowns for latency, volume, and cost let us compare LLM API vs. local HF model vs. semantic search on the same axes.
- **Ranking** — top-10 users by cost (descending sort) for spend attribution.
- **Reliability rate** — success / (success + error + timeout) as a simple SLO indicator.

Simulated data is generated with realistic distributions
(`lognormvariate` for latency, `triangular` for time skew so recent days
have more traffic) so the dashboard shows meaningful shapes even without
live production traffic.

---

## Part 2 — Implementation

### Architecture

1. **New model:** `rewrites/models.py::AICallLog`
   — one row per AI invocation with `feature`, `model_name`, `user`, `session`,
   `latency_ms`, `input_chars`, `prompt_tokens`, `completion_tokens`,
   `cost_usd`, `status`, `created_at`. Indexed on `(feature, created_at)`
   and `(user, created_at)`.

2. **Non-invasive instrumentation:** `rewrites/signals.py`
   — a `post_save` signal on `RewriteResult` derives latency/token/cost
   estimates from existing fields and writes an `AICallLog` row.
   The existing AI service modules (`llm_rewrite.py`, `local_rewrite.py`,
   `semantic_search.py`) are **not modified**.

3. **Seed command:** `python manage.py seed_ai_logs --count 500 --days 21`
   — generates realistic simulated logs so the production dashboard has
   data even without live traffic.

4. **Test user command:** `python manage.py create_test_user`
   — creates / resets the grader account `mohitg2 / uiuc12345`.

5. **Dashboard view + 9 JSON endpoints** under `/api/a10/*`, returning
   Vega-Lite-ready arrays. Rendered by
   `templates/rewrites/analytics_dashboard.html` using Vega-Lite v5 via
   CDN (same stack already used by the `vega-lite/` page).

### Routes

```
/analytics-dashboard/                  page
/api/a10/latency-distribution/         JSON
/api/a10/latency-by-feature/           JSON
/api/a10/calls-over-time/              JSON
/api/a10/feature-usage/                JSON
/api/a10/status-breakdown/             JSON
/api/a10/input-size-distribution/      JSON
/api/a10/cost-by-feature/              JSON
/api/a10/cost-over-time/               JSON
/api/a10/top-cost-users/               JSON
```

### Sample outputs (seed: 500 rows / 21 days)

- Total calls: **500**, Success rate: **91.8%**
- Avg latency: **1654 ms**, p50 **1499**, p95 **4206**, p99 **5593**
- Total cost: **$0.1074** across 130,236 tokens
- Cost by feature: LLM API $0.1074 (291 calls), local $0 (76 calls),
  semantic $0 (133 calls) — confirms local/HF features are free-tier.

### Submission notes

- **Live dashboard:** https://rewritelab.onrender.com/analytics-dashboard/
- **Login:** `mohitg2` / `uiuc12345`
- **Code:** pushed to `main` on
  https://github.com/AlikhanIllini/10_RewriteLab
- **Screenshots:** attached separately in submission.

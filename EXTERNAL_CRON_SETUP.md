# External Cron Setup (Backup for GitHub Actions Schedule)

GitHub Actions scheduled workflows can sometimes be unreliable due to:
- Automatic disabling after periods of inactivity
- Delays during high load periods
- Silent failures

This guide sets up an external cron service as a reliable backup.

## Option 1: cron-job.org (Recommended, Free)

### Step 1: Create a GitHub Personal Access Token

1. Go to https://github.com/settings/tokens?type=beta
2. Click "Generate new token"
3. Name it: `email-summary-cron`
4. Set expiration (recommend 1 year)
5. Under "Repository access", select "Only select repositories" and choose `email-summary-agent`
6. Under "Permissions" > "Repository permissions":
   - Set **Contents** to "Read and write"
   - Set **Actions** to "Read and write" (optional, for monitoring)
7. Click "Generate token"
8. **Copy the token immediately** (starts with `github_pat_`)

### Step 2: Set Up cron-job.org

1. Go to https://cron-job.org and create a free account
2. Click "Create cronjob"
3. Configure as follows:

| Setting | Value |
|---------|-------|
| **Title** | Email Summary Agent |
| **URL** | `https://api.github.com/repos/ramben-ishay/email-summary-agent/dispatches` |
| **Schedule** | Choose your times (e.g., 08:00, 16:00, 00:00 Israel Time) |
| **Request method** | POST |
| **Request body** | `{"event_type":"run_email_summary"}` |

4. Under "Advanced" settings, add these headers:

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer YOUR_GITHUB_PAT_HERE` |
| `Accept` | `application/vnd.github.v3+json` |
| `Content-Type` | `application/json` |

5. Save the cronjob

### Step 3: Test It

Click "Test run" in cron-job.org to verify it works. Then check:
https://github.com/ramben-ishay/email-summary-agent/actions

You should see a new run triggered by `repository_dispatch`.

---

## Option 2: Using curl (Manual/Local Testing)

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_GITHUB_PAT" \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Content-Type: application/json" \
  https://api.github.com/repos/ramben-ishay/email-summary-agent/dispatches \
  -d '{"event_type":"run_email_summary"}'
```

A successful call returns HTTP 204 (no content).

---

## Option 3: Other Free Cron Services

- **EasyCron** (https://www.easycron.com) - 1 free cron job
- **Cron Hub** (https://cronhub.io) - Free tier available
- **Render** (https://render.com) - Free cron jobs with their services

---

## Monitoring

Check workflow runs at:
https://github.com/ramben-ishay/email-summary-agent/actions/workflows/email-summary.yml

Runs triggered by external cron will show `repository_dispatch` as the event type.

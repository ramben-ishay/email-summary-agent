# Email Summary Agent Specification

## Overview

An automated agent that runs on GitHub Actions, fetches newsletter emails from Gmail, summarizes articles using GPT 5.2, and sends a daily digest grouped by topic.

## Configuration

| Setting | Value |
|---------|-------|
| **Source Email** | `ramnewslettersblogsnews@gmail.com` |
| **Recipient Email** | `ram.ben.ishay60@gmail.com` |
| **Authentication** | Gmail IMAP with App Password |
| **Schedule** | Daily at 4 PM Israel Time (14:00 UTC) |
| **LLM Model** | GPT 5.2 |
| **Time Window** | Past 24 hours |

## Email Content Type

The source email receives newsletters containing:
- Medium posts
- Substack posts
- Personal blog articles
- Some emails contain single articles, others contain lists of articles

### Newsletter Formats

**Single Article Newsletters** (e.g., Lenny's Newsletter, Stratechery, A Smart Bear)
- Focus on the main article only
- Ignore reference links, recommended resources, past episodes, and book recommendations
- These supplementary links are not separate articles to summarize

**Multi Article Digests** (e.g., TechCrunch, a16z, Medium Weekly Digest)
- Extract and summarize each distinct article
- Typically organized in sections like "Top Stories", "Must Reads", etc.

**News Aggregations** (e.g., Google Alerts)
- Extract individual news items with their source links

### Content to Exclude

**Promotional Content** (always exclude):
- Event announcements and ticket sales
- Webinar promotions
- Newsletter cross promotions
- Sponsor messages and advertisements
- "A message from our partners" sections

**Non Newsletter Emails** (separate handling):
- Security alerts, account notifications, and system emails
- Include in a dedicated "System Notifications" section at the end
- Brief mention only, no detailed summary needed

### Hebrew Content

Hebrew newsletters should be:
- Summarized with the summary translated to English
- Original Hebrew title can be preserved alongside English summary
- Link to original article maintained

### Paywalled Content

For articles behind paywalls (common in Substack):
- Summarize whatever preview content is visible in the email
- Include the link as normal
- No special notation needed

## Summary Format

### Structure
- Articles grouped by dynamically detected topics (AI determines categories based on content)
- Each article includes:
  - Source name in brackets (e.g., [Lenny's Newsletter], [TechCrunch], [TheMarker])
  - Article title in bold
  - 1 to 2 line summary
  - Original link to the article

### Example Output

```
## AI and Machine Learning

- [TechCrunch] **Understanding Transformers in 2026** - A deep dive into how transformer architecture has evolved with new attention mechanisms and efficiency improvements. [Read more](https://example.com/article1)

- [a16z] **Building RAG Applications** - Practical guide to retrieval augmented generation covering vector databases and chunking strategies. [Read more](https://example.com/article2)

- [אופטיקאי מדופלם] **רדיולוגים ובינה מלאכותית** - Analysis of how AI is transforming radiology, examining whether radiologists will become obsolete or find new roles alongside AI tools. [Read more](https://example.com/hebrew-article)

## Productivity

- [The New York Times] **The 4 Hour Deep Work Block** - Research backed approach to structuring focused work sessions for maximum output. [Read more](https://example.com/article3)

## Startups and Business

- [Lenny's Newsletter] **Why your product stopped growing** - WP Engine founder Jason Cohen discusses diagnosing stalled growth, why "too expensive" is never the real churn reason, and the positioning shift that can 8x revenue. [Read more](https://example.com/article4)

- [TheMarker] **רכישות הענק הסתירו את המגמה האמיתית** - Major tech acquisitions have been masking the real trends in Israeli high tech industry performance. [Read more](https://example.com/article5)

---

## System Notifications

- [Google] Security Alert: n8n.cloud access granted to your account
- [Google] Recovery email verified for your Google Account
```

## Processing Strategy

### Two Stage LLM Approach

**Stage 1: Individual Email Processing**
- Each email is processed separately to avoid context drift
- LLM extracts articles with summaries and links
- Utility links are filtered out (unsubscribe, social icons, tracking redirects, etc.)
- Link classification based on email context and URL patterns (no redirect resolution)

**Stage 2: Combination and Grouping**
- All extracted articles sent to LLM
- LLM groups articles by topic
- LLM formats the final email

## Link Filtering

The agent automatically excludes:
- Unsubscribe links
- Manage preferences links
- View in browser links
- Social media share buttons (Twitter/X, LinkedIn, Facebook share icons)
- Tracking redirects
- Email reply/forward links
- "Like", "Comment", "Restack" buttons (Substack)
- Podcast platform links (Spotify, Apple Podcasts, YouTube) unless the podcast IS the main content
- Author social profiles (X, LinkedIn)
- Sponsor/advertiser links
- Event registration and ticket purchase links
- Newsletter signup links for other publications
- "Read in app" links
- Reference links in single article newsletters (books, tools, past episodes)

**Links to Include:**
- Main article links (the actual content being shared)
- "Read more" links that lead to full articles
- Individual story links in multi article digests

Classification is done by the LLM using email context and URL patterns.

## Edge Cases

### No Emails
If no emails (or no articles) are found in the past 24 hours:
- Send a brief confirmation email: "No new articles found in the past 24 hours"
- This confirms the agent ran successfully

### High Volume
- Each email processed individually (prevents context drift)
- Results combined in final grouping stage
- GPT 5.2's 400K token context handles large volumes

## Required Secrets

GitHub repository secrets needed:

| Secret Name | Description |
|-------------|-------------|
| `GMAIL_ADDRESS` | Source Gmail address |
| `GMAIL_APP_PASSWORD` | Gmail App Password (not regular password) |
| `OPENAI_API_KEY` | OpenAI API key |
| `RECIPIENT_EMAIL` | Email address to receive summaries |

## Technical Stack

- **Runtime**: GitHub Actions
- **Language**: Python 3.11+
- **Email Access**: IMAP via `imaplib`
- **Email Sending**: SMTP via `smtplib`
- **LLM**: OpenAI GPT 5.2 API
- **Scheduling**: GitHub Actions cron

## File Structure

```
Email/
├── .github/
│   └── workflows/
│       └── email-summary.yml
├── scripts/
│   └── email_summary.py
├── requirements.txt
├── SPECIFICATION.md
└── SETUP.md
```

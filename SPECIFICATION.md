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
- Articles grouped by thematic categories (see below)
- Duplicate stories from multiple sources are deduplicated
- Irrelevant content is filtered to a separate section
- Each article includes:
  - Source name in brackets (e.g., [Lenny's Newsletter], [TechCrunch], [TheMarker])
  - Article title in bold
  - 1 to 2 line summary
  - Original link to the article

### Thematic Categories

Articles are grouped into these specific categories:

| Category | What Belongs Here |
|----------|------------------|
| **AI Products and Tools** | New AI products, tools, APIs, coding assistants (Codex, Clawdbot), voice agents, AI notetakers |
| **AI Strategy and Industry** | Enterprise AI deals, AI regulation, AI's impact on industries, M&A driven by AI |
| **Startup and Venture News** | Funding rounds, accelerators, unicorns, company acquisitions, VC insights |
| **Product Craft** | PM frameworks, roadmaps, discovery habits, measuring impact, PM job hunting |
| **UX Patterns and Accessibility** | Micro interactions, loading states, onboarding teardowns, designing for ADHD/autism/older adults |
| **Developer Tools and Engineering** | SDKs, coding tools, CSS techniques, security incidents, programming language trends |
| **Marketing and Growth Tactics** | Viral loops, launch strategies, growth hacking, copywriting |
| **Leadership and Careers** | Burnout, meritocracy, company culture, career advice, job hunting |
| **Israeli Startups and Tech** | Israeli VC ecosystem, Israeli startups, tech company news ONLY (not general Israeli news) |
| **Crypto and Fintech** | Cryptocurrency, stablecoin regulation, fintech products |

### Deduplication Rules

- When the same story appears from multiple sources, keep only one entry with the best summary
- When multiple articles discuss the same product/topic, combine them into one entry
- Prefer sources with more substantive summaries

### Filtered Out Section

Content that is NOT relevant to tech/product professionals goes in a "Filtered Out" section:

- General politics/geopolitics unrelated to tech
- Real estate prices and property sales
- Legal cases unrelated to tech
- Social/cultural stories with no tech angle
- Labor policy unless directly affecting tech workers
- Government policy unrelated to tech
- Wealth profiles of non tech individuals
- Promotional content with no substance

### Example Output

```
## AI Products and Tools

- [TechCrunch] **OpenAI launches new macOS app for agentic coding** - OpenAI introduces Codex for macOS, enabling advanced AI driven coding workflows. [Read more](https://example.com/article1)

- [LangTalks] **Clawdbot: העוזר האישי שרץ על המחשב שלך** - Clawdbot (OpenClaw) is an open source AI assistant running locally with direct file access. [Read more](https://example.com/article2)

## AI Strategy and Industry

- [Platformer] **SpaceX acquires xAI for $250B** - Consolidates Musk's companies and plans space based AI data centers. [Read more](https://example.com/article3)

## Startup and Venture News

- [a16z] **2026: the biggest year of M&A in history?** - Ben Horowitz and David Solomon discuss why 2026 could break records for mergers and acquisitions. [Read more](https://example.com/article4)

## Product Craft

- [Lenny's Newsletter] **How to build AI product sense** - Interactive guide for developing intuition and skills for impactful AI products. [Read more](https://example.com/article5)

## Israeli Startups and Tech

- [Startup for Startup] **Ecosystem Conference** - Israeli investors discuss startup challenges in the AI era and strategies for growth. [Read more](https://example.com/article6)

## Filtered Out

- [TheMarker] **וילה ב 12.2 מיליון שקל** - Real estate, not tech
- [TheMarker] **עזבו חרדים, הממשלה הזאת עוד תתפרק בגלל הרפורמה בחלב** - Government policy, not tech
- [TheMarker] **סין בונה נושאות מטוסים** - Geopolitics, not tech

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

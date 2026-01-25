# Email Summary Agent Setup Guide

This guide walks you through setting up the Email Summary Agent on GitHub Actions.

## Prerequisites

1. A Gmail account for fetching newsletters
2. A Gmail account for sending summaries (can be the same account)
3. An OpenAI API key with access to GPT 5.2
4. A GitHub repository to host the workflow

## Step 1: Enable 2 Factor Authentication on Gmail

Before creating an App Password, you must have 2FA enabled:

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Under "Signing in to Google", click **2 Step Verification**
3. Follow the prompts to enable 2FA

## Step 2: Generate a Gmail App Password

App Passwords let you sign in to your Google Account from apps that don't support 2FA.

1. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
   - Or navigate: Google Account > Security > 2 Step Verification > App passwords
2. You may need to sign in again
3. Under "Select app", choose **Mail**
4. Under "Select device", choose **Other (Custom name)**
5. Enter a name like "Email Summary Agent"
6. Click **Generate**
7. **Copy the 16 character password** (shown with spaces, but you can use it with or without spaces)
8. Store this password securely; you won't be able to see it again

## Step 3: Enable IMAP in Gmail

1. Open Gmail in your browser
2. Click the gear icon > **See all settings**
3. Go to the **Forwarding and POP/IMAP** tab
4. Under "IMAP access", select **Enable IMAP**
5. Click **Save Changes**

## Step 4: Create a GitHub Repository

1. Go to [GitHub](https://github.com) and create a new repository
2. Name it something like `email-summary-agent`
3. Initialize with a README (optional)
4. Clone the repository locally or push these files to it

## Step 5: Add GitHub Secrets

You need to add 4 secrets to your GitHub repository:

1. Go to your repository on GitHub
2. Click **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret** for each of the following:

| Secret Name | Value |
|-------------|-------|
| `GMAIL_ADDRESS` | `ramnewslettersblogsnews@gmail.com` |
| `GMAIL_APP_PASSWORD` | The 16 character App Password from Step 2 |
| `OPENAI_API_KEY` | Your OpenAI API key |
| `RECIPIENT_EMAIL` | `ram.ben.ishay60@gmail.com` |

## Step 6: Push the Code

Ensure your repository has the following structure:

```
your-repo/
├── .github/
│   └── workflows/
│       └── email-summary.yml
├── scripts/
│   └── email_summary.py
├── requirements.txt
├── SPECIFICATION.md
└── SETUP.md
```

Push all files to your GitHub repository:

```bash
git add .
git commit -m "Add email summary agent"
git push origin main
```

## Step 7: Test the Workflow

1. Go to your repository on GitHub
2. Click **Actions** tab
3. Select **Daily Email Summary** workflow
4. Click **Run workflow** > **Run workflow**
5. Watch the workflow run and check for any errors
6. Check your email for the summary

## Troubleshooting

### "Invalid credentials" or "Authentication failed"

1. Make sure you're using an **App Password**, not your regular Gmail password
2. Verify the App Password was copied correctly (no extra spaces)
3. Ensure IMAP is enabled in Gmail settings
4. Check that 2FA is enabled on the Google account

### "No emails found"

1. The agent only fetches emails from the last 24 hours
2. Verify there are emails in the inbox within that timeframe
3. Check that the Gmail address is correct

### Workflow not running on schedule

1. GitHub Actions cron schedules can have delays of up to 15 minutes
2. Scheduled workflows only run on the default branch (usually `main`)
3. If the repository is inactive, GitHub may disable scheduled workflows

### OpenAI API errors

1. Verify your API key is valid and has sufficient credits
2. Check that your account has access to GPT 5.2
3. Look at the error message for specific issues

## Schedule

The workflow runs daily at:

| Timezone | Time |
|----------|------|
| UTC | 14:00 (2:00 PM) |
| Israel (IST/IDT) | 16:00 (4:00 PM) |

To change the schedule, edit the cron expression in `.github/workflows/email-summary.yml`:

```yaml
schedule:
  - cron: '0 14 * * *'  # Format: minute hour day month weekday
```

## Manual Testing

You can test the script locally:

```bash
# Set environment variables
export GMAIL_ADDRESS="your-email@gmail.com"
export GMAIL_APP_PASSWORD="your-app-password"
export OPENAI_API_KEY="your-openai-key"
export RECIPIENT_EMAIL="recipient@gmail.com"

# Install dependencies
pip install -r requirements.txt

# Run the script
python scripts/email_summary.py
```

## Cost Considerations

The agent uses GPT 5.2 which costs approximately:
- Input: $1.75 per 1M tokens
- Output: $14.00 per 1M tokens

Typical daily costs depend on newsletter volume:
- Light usage (5 to 10 emails): ~$0.01 to $0.05 per day
- Moderate usage (20 to 30 emails): ~$0.05 to $0.15 per day
- Heavy usage (50+ emails): ~$0.15 to $0.50 per day

## Security Notes

1. **Never commit secrets to your repository**
2. App Passwords can be revoked at any time from your Google Account
3. GitHub secrets are encrypted and not visible in logs
4. The agent only reads emails; it does not modify or delete them

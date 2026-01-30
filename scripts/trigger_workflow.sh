#!/bin/bash
# Trigger Email Summary Agent workflow via GitHub API
# This script is called by launchd on schedule

# Load the GitHub PAT from a secure file
PAT_FILE="$HOME/.config/email-summary-agent/github_pat"

if [ ! -f "$PAT_FILE" ]; then
    echo "Error: GitHub PAT not found at $PAT_FILE"
    echo "Please create the file with your GitHub Personal Access Token"
    exit 1
fi

GITHUB_PAT=$(cat "$PAT_FILE")

# Trigger the workflow
response=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST \
    -H "Authorization: Bearer $GITHUB_PAT" \
    -H "Accept: application/vnd.github.v3+json" \
    -H "Content-Type: application/json" \
    https://api.github.com/repos/ramben-ishay/email-summary-agent/dispatches \
    -d '{"event_type":"run_email_summary"}')

if [ "$response" = "204" ]; then
    echo "$(date): Workflow triggered successfully"
else
    echo "$(date): Failed to trigger workflow. HTTP status: $response"
    exit 1
fi

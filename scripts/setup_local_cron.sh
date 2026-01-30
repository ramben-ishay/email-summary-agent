#!/bin/bash
# Setup script for local cron trigger
# This sets up launchd to trigger the email summary workflow on schedule

set -e

CONFIG_DIR="$HOME/.config/email-summary-agent"
PAT_FILE="$CONFIG_DIR/github_pat"
PLIST_FILE="$HOME/Library/LaunchAgents/com.rambenishay.email-summary-agent.plist"

echo "=== Email Summary Agent Local Cron Setup ==="
echo ""

# Check if PAT already exists
if [ -f "$PAT_FILE" ]; then
    echo "GitHub PAT already configured at $PAT_FILE"
    read -p "Do you want to update it? (y/N): " update_pat
    if [ "$update_pat" != "y" ] && [ "$update_pat" != "Y" ]; then
        echo "Keeping existing PAT."
    else
        echo ""
        echo "Please enter your GitHub Personal Access Token:"
        echo "(Create one at: https://github.com/settings/tokens?type=beta)"
        read -s -p "PAT: " github_pat
        echo ""
        echo "$github_pat" > "$PAT_FILE"
        chmod 600 "$PAT_FILE"
        echo "PAT saved securely."
    fi
else
    echo "Please enter your GitHub Personal Access Token:"
    echo "(Create one at: https://github.com/settings/tokens?type=beta)"
    echo ""
    echo "Required permissions:"
    echo "  - Repository: email-summary-agent"
    echo "  - Contents: Read and write"
    echo ""
    read -s -p "PAT: " github_pat
    echo ""
    
    if [ -z "$github_pat" ]; then
        echo "Error: PAT cannot be empty"
        exit 1
    fi
    
    mkdir -p "$CONFIG_DIR"
    echo "$github_pat" > "$PAT_FILE"
    chmod 600 "$PAT_FILE"
    echo "PAT saved securely to $PAT_FILE"
fi

echo ""

# Test the PAT
echo "Testing GitHub API access..."
response=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $(cat $PAT_FILE)" \
    -H "Accept: application/vnd.github.v3+json" \
    https://api.github.com/repos/ramben-ishay/email-summary-agent)

if [ "$response" = "200" ]; then
    echo "GitHub API access: OK"
else
    echo "Warning: GitHub API returned status $response"
    echo "The PAT might not have the correct permissions."
fi

echo ""

# Load the launchd agent
echo "Loading launchd agent..."
launchctl unload "$PLIST_FILE" 2>/dev/null || true
launchctl load "$PLIST_FILE"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "The workflow will be triggered at:"
echo "  - 08:00 Israel Time"
echo "  - 16:00 Israel Time"
echo "  - 00:00 Israel Time"
echo ""
echo "Logs: $CONFIG_DIR/trigger.log"
echo ""
echo "To test manually, run:"
echo "  $HOME/Documents/Cursor/email-summary-agent/scripts/trigger_workflow.sh"
echo ""
echo "To disable, run:"
echo "  launchctl unload $PLIST_FILE"

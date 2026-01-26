#!/usr/bin/env python3
"""
Email Summary Agent

Fetches newsletter emails from Gmail, summarizes articles using GPT 5.2,
and sends a daily digest grouped by topic.

Implements the full specification from SPECIFICATION.md
"""

import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime, timedelta, timezone
import os
import json
import re
from typing import Optional
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from bs4 import BeautifulSoup
import html2text

# Load environment variables from .env file
# Look for .env in the project root (parent of scripts folder)
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

# Configuration from environment variables
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL")

# Gmail IMAP/SMTP settings
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-4.1"  # Update to "gpt-5.2" when available; spec targets GPT 5.2


def decode_email_subject(subject: str) -> str:
    """Decode email subject handling various encodings."""
    if subject is None:
        return "No Subject"
    
    decoded_parts = []
    for part, encoding in decode_header(subject):
        if isinstance(part, bytes):
            decoded_parts.append(part.decode(encoding or "utf-8", errors="replace"))
        else:
            decoded_parts.append(part)
    return "".join(decoded_parts)


def get_email_body(msg: email.message.Message) -> str:
    """Extract the text body from an email message."""
    body = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            
            if "attachment" in content_disposition:
                continue
                
            if content_type == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body = payload.decode(charset, errors="replace")
                        break
                except Exception:
                    continue
                    
            elif content_type == "text/html":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        html_content = payload.decode(charset, errors="replace")
                        # Convert HTML to text
                        h = html2text.HTML2Text()
                        h.ignore_links = False
                        h.ignore_images = True
                        h.ignore_tables = False
                        body = h.handle(html_content)
                except Exception:
                    continue
    else:
        content_type = msg.get_content_type()
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                if content_type == "text/html":
                    h = html2text.HTML2Text()
                    h.ignore_links = False
                    h.ignore_images = True
                    body = h.handle(payload.decode(charset, errors="replace"))
                else:
                    body = payload.decode(charset, errors="replace")
        except Exception:
            body = ""
    
    return body


def get_sender(msg: email.message.Message) -> str:
    """Extract sender name/email from message."""
    sender = msg.get("From", "Unknown Sender")
    # Try to decode if needed
    decoded_parts = []
    for part, encoding in decode_header(sender):
        if isinstance(part, bytes):
            decoded_parts.append(part.decode(encoding or "utf-8", errors="replace"))
        else:
            decoded_parts.append(part)
    return "".join(decoded_parts)


def fetch_emails_from_last_n_hours(hours: int = 8, limit: Optional[int] = None) -> list[dict]:
    """Connect to Gmail and fetch emails from the past N hours.
    
    Args:
        hours: Number of hours to look back (default 8)
        limit: Optional maximum number of emails to fetch (most recent first)
    """
    print(f"Connecting to Gmail IMAP...")
    
    emails = []
    
    try:
        # Connect to Gmail
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        mail.select("INBOX")
        
        # Calculate date for search (N hours ago)
        since_date = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%d-%b-%Y")
        
        # Search for emails since yesterday
        search_criteria = f'(SINCE "{since_date}")'
        status, message_ids = mail.search(None, search_criteria)
        
        if status != "OK":
            print("No messages found or search failed")
            return emails
        
        message_id_list = message_ids[0].split()
        total_found = len(message_id_list)
        
        # Take most recent emails if limit is specified (newest are at the end)
        if limit and len(message_id_list) > limit:
            message_id_list = message_id_list[-limit:]
            print(f"Found {total_found} emails, processing {limit} most recent")
        else:
            print(f"Found {total_found} emails from the last {hours} hours")
        
        for msg_id in message_id_list:
            try:
                status, msg_data = mail.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue
                    
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Get email date
                date_str = msg.get("Date", "")
                
                # Parse the email
                email_data = {
                    "subject": decode_email_subject(msg.get("Subject")),
                    "sender": get_sender(msg),
                    "date": date_str,
                    "body": get_email_body(msg)
                }
                
                # Only include emails with actual content
                if email_data["body"].strip():
                    emails.append(email_data)
                    print(f"  Fetched: {email_data['subject'][:50]}...")
                    
            except Exception as e:
                print(f"  Error processing email {msg_id}: {e}")
                continue
        
        mail.logout()
        
    except Exception as e:
        print(f"Error connecting to Gmail: {e}")
        raise
    
    return emails


def extract_articles_from_email(email_data: dict) -> dict:
    """
    Stage 1: Use GPT to extract articles from a single email.
    Returns a dict with articles listales and email_type (newsletter/system_notification).
    """
    print(f"  Processing: {email_data['subject'][:50]}...")
    
    prompt = f"""Analyze this email and extract content according to these rules:

**FIRST: Determine the email type:**
1. "newsletter" - Contains articles, blog posts, news, or educational content
2. "system_notification" - Security alerts, account notifications, service updates, verification emails

**FOR NEWSLETTERS:**

Identify the newsletter format:
- "single_article": One main article/post with optional reference links (e.g., Substack posts, personal blogs)
- "multi_article": Multiple distinct articles/stories (e.g., TechCrunch, a16z, news digests)
- "news_aggregation": Collection of news items from various sources (e.g., Google Alerts)

**Extraction Rules by Format:**

For SINGLE_ARTICLE newsletters:
- Extract ONLY the main article
- IGNORE all reference links (books, tools, past episodes, recommended resources)
- IGNORE podcast platform links (Spotify, Apple Podcasts, YouTube links to the same content)
- The email IS about one topic; summarize that one topic

For MULTI_ARTICLE newsletters:
- Extract each distinct article separately
- Include stories from sections like "Top Stories", "Must Reads", etc.

For NEWS_AGGREGATION:
- Extract each news item with its source link

**ALWAYS EXCLUDE these link types:**
- Unsubscribe, manage preferences, view in browser links
- Social media share buttons (Twitter/X, LinkedIn, Facebook)
- "Like", "Comment", "Restack" buttons
- Author social profiles
- Event tickets, webinar promotions, newsletter signups
- Sponsor/advertiser content
- "A message from our partners" sections
- "Read in app" links
- Footer navigation links

**FOR SYSTEM NOTIFICATIONS:**
- Extract a brief one-line description of what the notification is about
- No article extraction needed

**HEBREW CONTENT:**
- If the content is in Hebrew, still extract it
- Provide the original Hebrew title
- Translate the summary to English

Email Subject: {email_data['subject']}
Email From: {email_data['sender']}

Email Content:
{email_data['body'][:20000]}

Respond in JSON format:
{{
    "email_type": "newsletter" or "system_notification",
    "newsletter_format": "single_article" or "multi_article" or "news_aggregation" or null,
    "source_name": "Name of the newsletter/sender (e.g., 'Lenny's Newsletter', 'TechCrunch', 'Google')",
    "articles": [
        {{
            "title": "Article title (keep original language if Hebrew)",
            "summary": "1-2 line summary in ENGLISH (translate if Hebrew)",
            "link": "URL to the article",
            "is_hebrew": true/false
        }}
    ],
    "system_notification_summary": "Brief description if system_notification, null otherwise"
}}

If no valid articles are found in a newsletter, return an empty articles array.
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert at analyzing emails and extracting article references. 
You accurately distinguish between:
- Main article content vs supplementary reference links
- Newsletter content vs system notifications
- Promotional content vs actual articles

You always translate Hebrew summaries to English while preserving Hebrew titles.
Always respond with valid JSON."""
                },
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Add source to each article
        source_name = result.get("source_name", email_data["sender"].split("<")[0].strip())
        for article in result.get("articles", []):
            article["source"] = source_name
        
        email_type = result.get("email_type", "newsletter")
        articles = result.get("articles", [])
        system_summary = result.get("system_notification_summary")
        
        if email_type == "system_notification" and system_summary:
            print(f"    System notification: {source_name}")
            return {
                "type": "system_notification",
                "source": source_name,
                "summary": system_summary,
                "articles": []
            }
        else:
            print(f"    Found {len(articles)} articles from {source_name}")
            return {
                "type": "newsletter",
                "source": source_name,
                "articles": articles
            }
        
    except Exception as e:
        print(f"    Error extracting articles: {e}")
        return {"type": "newsletter", "articles": [], "source": email_data["sender"]}


def group_articles_by_topic(all_articles: list[dict], system_notifications: list[dict]) -> str:
    """
    Stage 2: Use GPT to group all articles by topic and format the final summary.
    """
    if not all_articles and not system_notifications:
        return None
    
    print(f"Grouping {len(all_articles)} articles by topic...")
    
    # Prepare articles for the prompt
    articles_text = json.dumps(all_articles, indent=2, ensure_ascii=False)
    notifications_text = json.dumps(system_notifications, indent=2, ensure_ascii=False)
    
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    
    prompt = f"""Create a daily newsletter digest from these articles and system notifications.

**ARTICLES:**
{articles_text}

**SYSTEM NOTIFICATIONS:**
{notifications_text}

**FORMATTING REQUIREMENTS:**

1. Start with a title: "# Daily Newsletter Digest" and the date: {today}

2. Add a brief intro line like "Here's your daily summary of [X] articles from [Y] sources."

3. Group articles by topic with ## headers. Topic examples:
   - AI and Machine Learning
   - Startups and Business
   - Product Management
   - Software Engineering
   - Tech Industry News
   - Israeli Tech (for Hebrew sources)
   
4. **CRITICAL FORMAT for each article:**
   - [Source] **Title** - Summary in English. [Read more](link)
   - Example: [Lenny's Newsletter] **Why your product stopped growing** - WP Engine founder discusses diagnosing stalled growth. [Read more](https://...)
   - For Hebrew titles, keep the Hebrew title: [TheMarker] **רכישות הענק** - English summary here. [Read more](link)

5. After all article sections, add a horizontal rule (---) and then:

## System Notifications

- [Source] Brief description of notification
- [Source] Brief description of notification

6. End with a footer: "*Automated by Email Summary Agent*"

**IMPORTANT:**
- Every article MUST have the source in brackets at the start
- Summaries must be in English (translate Hebrew if needed)
- Hebrew titles can remain in Hebrew
- Keep summaries to 1-2 lines maximum
- Make the email scannable and well-organized
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert at organizing information into clear, well-structured email digests. 
You create emails that are:
- Easy to scan quickly
- Well-organized by topic
- Consistently formatted with [Source] **Title** - Summary format
- Professional and pleasant to read"""
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Error grouping articles: {e}")
        return None


def create_no_articles_message() -> str:
    """Create message for when no articles are found."""
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    return f"""# Daily Newsletter Digest

**Date:** {today}

No new articles were found in your newsletters from the past 24 hours.

This email confirms that the Email Summary Agent ran successfully.

---
*Automated by Email Summary Agent*
"""


def send_summary_email(summary_content: str):
    """Send the summary email via Gmail SMTP."""
    print("Sending summary email...")
    
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    
    # Create message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Daily Newsletter Digest - {today}"
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = RECIPIENT_EMAIL
    
    # Create plain text version
    plain_text = summary_content
    
    # Create HTML version (convert markdown to basic HTML)
    html_content = markdown_to_html(summary_content)
    
    part1 = MIMEText(plain_text, "plain", "utf-8")
    part2 = MIMEText(html_content, "html", "utf-8")
    
    msg.attach(part1)
    msg.attach(part2)
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, RECIPIENT_EMAIL, msg.as_string())
        server.quit()
        print(f"Summary email sent to {RECIPIENT_EMAIL}")
    except Exception as e:
        print(f"Error sending email: {e}")
        raise


def markdown_to_html(markdown_text: str) -> str:
    """Convert markdown to beautiful HTML email with modern design."""
    
    # Category colors for visual distinction
    category_colors = {
        "AI and Machine Learning": "#8B5CF6",
        "Startups and Business": "#10B981",
        "Product Management": "#F59E0B",
        "Software Engineering": "#3B82F6",
        "Tech Industry News": "#EC4899",
        "Israeli Tech": "#06B6D4",
        "Cybersecurity": "#EF4444",
        "System Notifications": "#6B7280",
    }
    
    def get_category_color(category: str) -> str:
        for key, color in category_colors.items():
            if key.lower() in category.lower():
                return color
        return "#6366F1"  # Default purple
    
    # Parse the markdown content
    lines = markdown_text.split('\n')
    
    # Extract title, date, and intro
    title = "Daily Newsletter Digest"
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    intro = ""
    
    sections = []
    current_section = None
    current_items = []
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
            
        # Main title
        if line.startswith('# '):
            title = line[2:]
            continue
            
        # Date line
        if line.startswith('**Date:**') or re.match(r'^[A-Z][a-z]+ \d+, \d{4}$', line):
            date_str = line.replace('**Date:**', '').strip()
            continue
            
        # Intro paragraph
        if line.startswith("Here's your"):
            intro = line
            continue
            
        # Section header
        if line.startswith('## '):
            if current_section and current_items:
                sections.append((current_section, current_items))
            current_section = line[3:]
            current_items = []
            continue
            
        # Article item
        if line.startswith('- '):
            current_items.append(line[2:])
            continue
            
        # Horizontal rule (section break)
        if line == '---':
            if current_section and current_items:
                sections.append((current_section, current_items))
            current_section = None
            current_items = []
            continue
            
        # Footer
        if line.startswith('*Automated'):
            continue
    
    # Don't forget the last section
    if current_section and current_items:
        sections.append((current_section, current_items))
    
    # Build table of contents
    toc_html = ""
    for section_name, items in sections:
        if "System Notifications" not in section_name:
            color = get_category_color(section_name)
            toc_html += f'''<a href="#section-{section_name.replace(' ', '-').lower()}" style="display: inline-block; margin: 4px; padding: 6px 12px; background: {color}15; color: {color}; border-radius: 20px; text-decoration: none; font-size: 13px; font-weight: 500;">{section_name} ({len(items)})</a>'''
    
    # Build sections HTML
    sections_html = ""
    for section_name, items in sections:
        color = get_category_color(section_name)
        is_system = "System Notifications" in section_name
        is_hebrew = "Israeli" in section_name or "Hebrew" in section_name
        
        items_html = ""
        for item in items:
            # Parse item: [Source] **Title** - Summary. [Read more](link)
            # or for system notifications: [Source] Description
            
            if is_system:
                # System notification format
                match = re.match(r'\[([^\]]+)\]\s*(.+)', item)
                if match:
                    source = match.group(1)
                    description = match.group(2)
                    items_html += f'''
                    <tr>
                        <td style="padding: 8px 0; border-bottom: 1px solid #f3f4f6;">
                            <span style="display: inline-block; background: #f3f4f6; color: #6b7280; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; margin-right: 8px;">{source}</span>
                            <span style="color: #6b7280; font-size: 14px;">{description}</span>
                        </td>
                    </tr>'''
            else:
                # Article format
                match = re.match(r'\[([^\]]+)\]\s*\*\*(.+?)\*\*\s*[-–]\s*(.+?)\s*\[Read more\]\(([^)]+)\)', item)
                if match:
                    source = match.group(1)
                    article_title = match.group(2)
                    summary = match.group(3)
                    link = match.group(4)
                    
                    # Check if Hebrew content
                    has_hebrew = bool(re.search(r'[\u0590-\u05FF]', article_title))
                    text_dir = 'rtl' if has_hebrew else 'ltr'
                    text_align = 'right' if has_hebrew else 'left'
                    
                    items_html += f'''
                    <tr>
                        <td style="padding: 16px 0; border-bottom: 1px solid #f3f4f6;">
                            <table cellpadding="0" cellspacing="0" border="0" width="100%">
                                <tr>
                                    <td>
                                        <span style="display: inline-block; background: {color}20; color: {color}; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; letter-spacing: 0.3px;">{source}</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-top: 8px;" dir="{text_dir}">
                                        <a href="{link}" style="color: #1f2937; text-decoration: none; font-weight: 600; font-size: 15px; line-height: 1.4; text-align: {text_align};">{article_title}</a>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-top: 6px;">
                                        <span style="color: #6b7280; font-size: 14px; line-height: 1.5;">{summary}</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-top: 10px;">
                                        <a href="{link}" style="display: inline-block; background: {color}; color: white; padding: 6px 14px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: 500;">Read Article →</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>'''
                else:
                    # Fallback for unparseable items
                    items_html += f'''
                    <tr>
                        <td style="padding: 12px 0; border-bottom: 1px solid #f3f4f6; color: #4b5563; font-size: 14px;">
                            {item}
                        </td>
                    </tr>'''
        
        section_id = section_name.replace(' ', '-').lower()
        section_icon = "🔔" if is_system else ""
        
        sections_html += f'''
        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 32px;" id="section-{section_id}">
            <tr>
                <td style="padding-bottom: 16px;">
                    <table cellpadding="0" cellspacing="0" border="0">
                        <tr>
                            <td style="background: {color}; width: 4px; border-radius: 2px;"></td>
                            <td style="padding-left: 12px;">
                                <span style="font-size: 18px; font-weight: 700; color: #1f2937;">{section_icon} {section_name}</span>
                                <span style="margin-left: 8px; background: {color}20; color: {color}; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 600;">{len(items)}</span>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
            <tr>
                <td>
                    <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background: #ffffff; border-radius: 12px; border: 1px solid #e5e7eb;">
                        <tr>
                            <td style="padding: 8px 20px;">
                                <table cellpadding="0" cellspacing="0" border="0" width="100%">
                                    {items_html}
                                </table>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>'''
    
    # Count total articles (excluding system notifications)
    total_articles = sum(len(items) for name, items in sections if "System Notifications" not in name)
    
    # Build full HTML
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #f9fafb; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #f9fafb;">
            <tr>
                <td align="center" style="padding: 20px;">
                    <table cellpadding="0" cellspacing="0" border="0" width="600" style="max-width: 600px;">
                        
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); border-radius: 16px 16px 0 0; padding: 32px 24px; text-align: center;">
                                <h1 style="margin: 0; color: white; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">📬 {title}</h1>
                                <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.9); font-size: 15px;">{date_str}</p>
                            </td>
                        </tr>
                        
                        <!-- Stats Bar -->
                        <tr>
                            <td style="background: white; padding: 20px 24px; border-left: 1px solid #e5e7eb; border-right: 1px solid #e5e7eb;">
                                <table cellpadding="0" cellspacing="0" border="0" width="100%">
                                    <tr>
                                        <td align="center">
                                            <span style="display: inline-block; background: #f3f4f6; padding: 8px 16px; border-radius: 20px; font-size: 14px; color: #4b5563;">
                                                <strong style="color: #6366f1;">{total_articles}</strong> articles from <strong style="color: #6366f1;">{len(sections) - 1}</strong> categories
                                            </span>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                        <!-- Table of Contents -->
                        <tr>
                            <td style="background: white; padding: 0 24px 20px 24px; border-left: 1px solid #e5e7eb; border-right: 1px solid #e5e7eb;">
                                <table cellpadding="0" cellspacing="0" border="0" width="100%">
                                    <tr>
                                        <td style="text-align: center; padding: 16px; background: #f9fafb; border-radius: 12px;">
                                            <p style="margin: 0 0 12px 0; font-size: 12px; color: #9ca3af; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">Jump to Section</p>
                                            {toc_html}
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                        <!-- Main Content -->
                        <tr>
                            <td style="background: #f9fafb; padding: 24px; border-left: 1px solid #e5e7eb; border-right: 1px solid #e5e7eb;">
                                {sections_html}
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="background: #1f2937; border-radius: 0 0 16px 16px; padding: 24px; text-align: center;">
                                <p style="margin: 0; color: #9ca3af; font-size: 13px;">
                                    Automated by <strong style="color: white;">Email Summary Agent</strong>
                                </p>
                                <p style="margin: 8px 0 0 0; color: #6b7280; font-size: 12px;">
                                    Powered by GPT | Built with Python
                                </p>
                            </td>
                        </tr>
                        
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    '''
    
    return html


def main(email_limit: Optional[int] = None):
    """Main entry point for the email summary agent.
    
    Args:
        email_limit: Optional limit on number of emails to process (for testing)
    """
    print("=" * 60)
    print("Email Summary Agent Starting")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)
    
    # Validate configuration
    if not all([GMAIL_ADDRESS, GMAIL_APP_PASSWORD, OPENAI_API_KEY, RECIPIENT_EMAIL]):
        missing = []
        if not GMAIL_ADDRESS:
            missing.append("GMAIL_ADDRESS")
        if not GMAIL_APP_PASSWORD:
            missing.append("GMAIL_APP_PASSWORD")
        if not OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        if not RECIPIENT_EMAIL:
            missing.append("RECIPIENT_EMAIL")
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    # Step 1: Fetch emails from the last 24 hours
    print("\n[Step 1] Fetching emails from the last 24 hours...")
    emails = fetch_emails_from_last_n_hours(hours=24, limit=email_limit)
    print(f"Total emails fetched: {len(emails)}")
    
    # Step 2: Extract articles from each email (Stage 1)
    print("\n[Step 2] Extracting articles from emails...")
    all_articles = []
    system_notifications = []
    
    for email_data in emails:
        result = extract_articles_from_email(email_data)
        
        if result["type"] == "system_notification":
            system_notifications.append({
                "source": result["source"],
                "summary": result["summary"]
            })
        else:
            all_articles.extend(result.get("articles", []))
    
    print(f"\nTotal articles extracted: {len(all_articles)}")
    print(f"Total system notifications: {len(system_notifications)}")
    
    # Step 3: Group articles and create summary (Stage 2)
    print("\n[Step 3] Creating summary...")
    if all_articles or system_notifications:
        summary = group_articles_by_topic(all_articles, system_notifications)
    else:
        summary = create_no_articles_message()
    
    if not summary:
        summary = create_no_articles_message()
    
    # Step 4: Send the summary email
    print("\n[Step 4] Sending summary email...")
    send_summary_email(summary)
    
    print("\n" + "=" * 60)
    print("Email Summary Agent Completed Successfully")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Email Summary Agent")
    parser.add_argument("--limit", type=int, help="Limit number of emails to process (for testing)")
    args = parser.parse_args()
    main(email_limit=args.limit)

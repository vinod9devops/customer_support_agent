"""
Jira client for fetching CFT support tickets.
Connects to the Jira Cloud instance to retrieve pending SR tickets.
"""

import os
import httpx
from typing import Optional


JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "https://your-org.atlassian.net")

# Statuses to EXCLUDE (resolved/closed tickets)
EXCLUDED_STATUSES = (
    "Closed",
    "Cancel",
    "Cancelled",
    "Completed",
    "Done",
    "Resolved",
    "Pending Customer",
    "Waiting for Customer",
    "Pending User Verification",
    "Rejected",
)

PROJECT = "Cloud File Transfer-ServiceManagement"


def _get_auth() -> tuple[str, str]:
    """Get Jira auth credentials from environment."""
    email = os.environ.get("JIRA_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "")
    if not email or not token:
        raise ValueError(
            "JIRA_EMAIL and JIRA_API_TOKEN environment variables must be set.\n"
            "Get your API token from: https://id.atlassian.com/manage-profile/security/api-tokens"
        )
    return email, token


def fetch_team_members() -> list[dict]:
    """
    Fetch assignees who have open tickets in the CFT project.
    Returns a list of dicts with accountId and displayName.
    """
    email, token = _get_auth()

    excluded_str = ", ".join(f'"{s}"' for s in EXCLUDED_STATUSES)
    jql = (
        f'project = "{PROJECT}" '
        f"AND status NOT IN ({excluded_str}) "
        f"AND assignee IS NOT EMPTY "
        f"ORDER BY assignee ASC"
    )

    url = f"{JIRA_BASE_URL}/rest/api/3/search/jql"
    payload = {
        "jql": jql,
        "fields": ["assignee"],
        "maxResults": 100,
    }

    response = httpx.post(
        url,
        json=payload,
        auth=(email, token),
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    # Extract unique assignees
    seen = set()
    members = []
    for issue in data.get("issues", []):
        assignee = issue.get("fields", {}).get("assignee")
        if assignee and assignee.get("accountId") not in seen:
            seen.add(assignee["accountId"])
            members.append({
                "accountId": assignee["accountId"],
                "displayName": assignee.get("displayName", "Unknown"),
            })

    members.sort(key=lambda m: m["displayName"].lower())
    return members


def display_team_members(members: list[dict]) -> None:
    """Display team members in a numbered list."""
    print(f"  {'#':<4} {'Name'}")
    print(f"  {'─'*4} {'─'*30}")
    for i, member in enumerate(members, 1):
        print(f"  {i:<4} {member['displayName']}")


def fetch_pending_tickets(assignee_name: str) -> list[dict]:
    """
    Fetch pending/open tickets assigned to the given person.
    Returns a list of ticket dicts with key, summary, status, priority, reporter, description.
    """
    email, token = _get_auth()

    # Build JQL query - exclude closed/done/resolved/pending customer statuses
    excluded_str = ", ".join(f'"{s}"' for s in EXCLUDED_STATUSES)
    jql = (
        f'project = "{PROJECT}" '
        f"AND status NOT IN ({excluded_str}) "
        f'AND assignee = "{assignee_name}" '
        f"ORDER BY status DESC, created DESC"
    )

    # Use the new Jira Cloud search endpoint (POST /rest/api/3/search/jql)
    url = f"{JIRA_BASE_URL}/rest/api/3/search/jql"
    payload = {
        "jql": jql,
        "fields": ["summary", "status", "priority", "reporter", "description", "created"],
        "maxResults": 20,
    }

    response = httpx.post(
        url,
        json=payload,
        auth=(email, token),
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    tickets = []
    for issue in data.get("issues", []):
        fields = issue["fields"]
        # Extract description text from Atlassian Document Format
        description = _extract_description(fields.get("description"))
        tickets.append({
            "key": issue["key"],
            "summary": fields.get("summary", ""),
            "status": fields.get("status", {}).get("name", ""),
            "priority": fields.get("priority", {}).get("name", ""),
            "reporter": fields.get("reporter", {}).get("displayName", "Unknown"),
            "description": description,
            "created": fields.get("created", "")[:10],
        })

    return tickets


def _extract_description(desc) -> str:
    """Extract plain text from Jira's Atlassian Document Format (ADF)."""
    if not desc:
        return "(No description)"
    if isinstance(desc, str):
        return desc

    # ADF format - recursively extract text
    texts = []
    _walk_adf(desc, texts)
    return "\n".join(texts) or "(No description)"


def _walk_adf(node: dict, texts: list):
    """Recursively walk ADF nodes to extract text content."""
    if not isinstance(node, dict):
        return

    if node.get("type") == "text":
        texts.append(node.get("text", ""))
    elif node.get("type") == "hardBreak":
        texts.append("\n")

    for child in node.get("content", []):
        _walk_adf(child, texts)


def fetch_ticket_comments(ticket_key: str) -> list[dict]:
    """
    Fetch all comments for a given ticket.
    Returns a list of dicts with author, created, body.
    """
    email, token = _get_auth()

    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{ticket_key}/comment"
    response = httpx.get(
        url,
        auth=(email, token),
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    comments = []
    for comment in data.get("comments", []):
        author = comment.get("author", {}).get("displayName", "Unknown")
        created = comment.get("created", "")[:16].replace("T", " ")
        body = _extract_description(comment.get("body"))
        comments.append({
            "author": author,
            "created": created,
            "body": body,
        })

    return comments


def fetch_ticket_attachments(ticket_key: str) -> list[dict]:
    """
    Fetch attachments for a ticket.
    Returns list of dicts with filename, mimeType, content_url, size.
    """
    email, token = _get_auth()

    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{ticket_key}?fields=attachment"
    response = httpx.get(url, auth=(email, token), timeout=30)
    response.raise_for_status()
    data = response.json()

    attachments = []
    for att in data.get("fields", {}).get("attachment", []):
        attachments.append({
            "filename": att.get("filename", ""),
            "mimeType": att.get("mimeType", ""),
            "content_url": att.get("content", ""),
            "size": att.get("size", 0),
        })
    return attachments


def download_attachment(content_url: str) -> bytes:
    """Download attachment content from Jira."""
    email, token = _get_auth()
    response = httpx.get(content_url, auth=(email, token), timeout=60, follow_redirects=True)
    response.raise_for_status()
    return response.content


def get_ticket_with_history(ticket: dict) -> str:
    """
    Get full ticket context including description and comment history.
    Returns a formatted string with all context for the agent.
    """
    parts = [
        f"Ticket: {ticket['key']}",
        f"Summary: {ticket['summary']}",
        f"Reporter: {ticket['reporter']}",
        f"Status: {ticket['status']}",
        f"Priority: {ticket['priority']}",
        f"\nDescription:\n{ticket['description']}",
    ]

    try:
        comments = fetch_ticket_comments(ticket["key"])
        if comments:
            parts.append(f"\n--- Conversation History ({len(comments)} comments) ---")
            for c in comments:
                parts.append(f"\n[{c['created']}] {c['author']}:\n{c['body']}")
    except Exception:
        pass

    # List attachments
    try:
        attachments = fetch_ticket_attachments(ticket["key"])
        if attachments:
            parts.append(f"\n--- Attachments ({len(attachments)}) ---")
            for att in attachments:
                parts.append(f"- {att['filename']} ({att['mimeType']}, {att['size']} bytes)")
    except Exception:
        pass

    return "\n".join(parts)


def get_ticket_attachments_for_agent(ticket_key: str) -> list[dict]:
    """
    Download and prepare ticket attachments for the agent.
    Returns a list of content blocks ready for Claude's API:
    - Text files: {"type": "text", "content": "..."}
    - Images: {"type": "image", "media_type": "...", "data": "base64..."}
    """
    import base64

    TEXT_EXTENSIONS = {".txt", ".csv", ".log", ".json", ".xml", ".md", ".yml", ".yaml", ".conf", ".cfg", ".sh", ".py"}
    IMAGE_MIMES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
    MAX_TEXT_SIZE = 50000  # 50KB max per text file
    MAX_IMAGE_SIZE = 5000000  # 5MB max per image

    attachments = fetch_ticket_attachments(ticket_key)
    results = []

    for att in attachments:
        filename = att["filename"]
        mime = att["mimeType"]
        size = att["size"]

        # Skip large files
        if mime in IMAGE_MIMES and size > MAX_IMAGE_SIZE:
            results.append({"type": "text", "content": f"[Skipped large image: {filename} ({size} bytes)]"})
            continue

        # Text files
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext in TEXT_EXTENSIONS or mime.startswith("text/"):
            if size > MAX_TEXT_SIZE:
                results.append({"type": "text", "content": f"[Skipped large text file: {filename} ({size} bytes)]"})
                continue
            try:
                content = download_attachment(att["content_url"])
                text = content.decode("utf-8", errors="replace")
                results.append({"type": "text", "content": f"--- Attachment: {filename} ---\n{text}"})
            except Exception as e:
                results.append({"type": "text", "content": f"[Failed to read {filename}: {e}]"})

        # Images
        elif mime in IMAGE_MIMES:
            try:
                content = download_attachment(att["content_url"])
                b64 = base64.b64encode(content).decode("utf-8")
                results.append({
                    "type": "image",
                    "media_type": mime,
                    "data": b64,
                    "filename": filename,
                })
            except Exception as e:
                results.append({"type": "text", "content": f"[Failed to download image {filename}: {e}]"})
        else:
            results.append({"type": "text", "content": f"[Unsupported attachment: {filename} ({mime})]"})

    return results


def search_similar_tickets(ticket: dict, max_results: int = 10) -> list[dict]:
    """
    Search for historical tickets with similar keywords.
    Returns a list of dicts with key, summary, status, resolution date.
    """
    email, token = _get_auth()

    # Extract keywords from summary for search
    summary = ticket["summary"]
    # Remove common filler words and special characters
    stop_words = {"to", "the", "a", "an", "for", "of", "in", "on", "is", "and", "or", "with"}
    # Remove special chars that break JQL
    clean_summary = "".join(c if c.isalnum() or c == " " else " " for c in summary)
    keywords = [w for w in clean_summary.split() if w.lower() not in stop_words and len(w) > 2]
    search_text = " ".join(keywords[:4])  # Use top 4 keywords

    if not search_text:
        return []

    jql = (
        f'project = "{PROJECT}" '
        f'AND text ~ "{search_text}" '
        f'AND key != "{ticket["key"]}" '
        f"ORDER BY created DESC"
    )

    url = f"{JIRA_BASE_URL}/rest/api/3/search/jql"
    payload = {
        "jql": jql,
        "fields": ["summary", "status", "resolution", "resolutiondate", "created"],
        "maxResults": max_results,
    }

    response = httpx.post(
        url,
        json=payload,
        auth=(email, token),
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    similar = []
    for issue in data.get("issues", []):
        fields = issue["fields"]
        resolution = fields.get("resolution")
        similar.append({
            "key": issue["key"],
            "summary": fields.get("summary", ""),
            "status": fields.get("status", {}).get("name", ""),
            "resolution": resolution.get("name", "") if resolution else "",
            "created": fields.get("created", "")[:10],
            "resolutiondate": (fields.get("resolutiondate") or "")[:10],
        })

    return similar


def display_tickets(tickets: list[dict]) -> None:
    """Display tickets in a formatted table."""
    if not tickets:
        print("  No pending tickets found.")
        return

    print(f"  {'#':<4} {'Ticket':<15} {'Status':<22} {'Priority':<10} {'Reporter':<20} {'Summary'}")
    print(f"  {'─'*4} {'─'*15} {'─'*22} {'─'*10} {'─'*20} {'─'*40}")

    for i, ticket in enumerate(tickets, 1):
        summary = ticket["summary"][:50] + "..." if len(ticket["summary"]) > 50 else ticket["summary"]
        print(
            f"  {i:<4} {ticket['key']:<15} {ticket['status']:<22} "
            f"{ticket['priority']:<10} {ticket['reporter']:<20} {summary}"
        )

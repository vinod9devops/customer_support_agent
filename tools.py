"""
Tools for the customer support agents.
Uses a locally cached knowledge base and Jira access.
"""

from knowledge_base import search_knowledge_base


# Tool definitions for Claude's tool_use format
TOOLS = [
    {
        "name": "search_cft_docs",
        "description": (
            "Search the CFT (Cloud File Transfer) documentation knowledge base. "
            "The knowledge base contains all CFT User Guide pages including: "
            "overview, specifications, guidelines, prerequisites, getting started, "
            "concepts, file transfers, onboarding, admin portal, manage projects, "
            "manage applications, manage workflows, manage keys, webhooks, "
            "HTTPS integrations, SFTP setup, data security, encryption (PGP/SLIFT), "
            "CDR scanning, scan bypass, security policies, troubleshooting, FAQ, "
            "and more. Use specific keywords related to the customer's question."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Search query with keywords relevant to the customer's question. "
                        "Examples: 'SLA service level agreement performance', "
                        "'file size limit maximum', 'SFTP setup configuration', "
                        "'PGP encryption key management'"
                    ),
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_jira_tickets",
        "description": (
            "Search Jira for CFT support tickets. Use this to find tickets by keyword, "
            "check ticket status, look up a specific ticket by key (e.g., CFTSM-1234), "
            "or find tickets by status or assignee. "
            "Returns ticket key, summary, status, priority, and reporter."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Search text or ticket key. "
                        "Examples: 'CFTSM-3374', 'whitelist IP', 'SFTP connection'"
                    ),
                },
                "status": {
                    "type": "string",
                    "description": (
                        "Filter by ticket status. Options: 'open' (all non-closed), "
                        "'Work in Progress', 'In Progress', 'Open', 'Assigned', "
                        "'Pending Approval', 'Waiting for support', 'New'. "
                        "Leave empty to search all statuses."
                    ),
                },
                "assignee": {
                    "type": "string",
                    "description": "Filter by assignee name. Example: 'Ivan Lee', 'Yang Xia'",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_ticket_attachments",
        "description": (
            "Download and read attachments from a Jira ticket. "
            "Returns text content of text files (.txt, .csv, .log, .json, .xml, .md, .sh) "
            "and describes images. Use this when you need to read files attached to a ticket. "
            "Provide the ticket key (e.g., CFTSM-3372)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_key": {
                    "type": "string",
                    "description": "The Jira ticket key. Example: 'CFTSM-3372'",
                }
            },
            "required": ["ticket_key"],
        },
    }
]


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool by name and return the result."""
    if tool_name == "search_cft_docs":
        return search_knowledge_base(tool_input["query"])
    if tool_name == "search_jira_tickets":
        return _search_jira(
            query=tool_input.get("query", ""),
            status=tool_input.get("status", ""),
            assignee=tool_input.get("assignee", ""),
        )
    if tool_name == "get_ticket_attachments":
        return _get_attachments(tool_input["ticket_key"])
    return f"Unknown tool: {tool_name}"


def _get_attachments(ticket_key: str) -> str:
    """Fetch and read text attachments from a Jira ticket."""
    try:
        from jira_client import get_ticket_attachments_for_agent
        attachments = get_ticket_attachments_for_agent(ticket_key)

        if not attachments:
            return f"No attachments found on {ticket_key}."

        results = []
        for att in attachments:
            if att["type"] == "text":
                results.append(att["content"])
            elif att["type"] == "image":
                results.append(f"[Image attachment: {att.get('filename', 'image')} - "
                             f"Cannot display in text mode, but image was found]")

        return "\n\n".join(results)
    except Exception as e:
        return f"Error fetching attachments: {str(e)}"


def _search_jira(query: str, status: str = "", assignee: str = "") -> str:
    """Search Jira tickets by keyword, with optional status and assignee filters."""
    try:
        import os
        import httpx

        email = os.environ.get("JIRA_EMAIL", "")
        token = os.environ.get("JIRA_API_TOKEN", "")
        if not email or not token:
            return "Jira credentials not configured."

        base_url = os.environ.get("JIRA_BASE_URL", "https://your-org.atlassian.net")
        project = "Cloud File Transfer-ServiceManagement"

        # If query looks like a ticket key, fetch that specific ticket
        if query.upper().startswith("CFTSM-"):
            url = f"{base_url}/rest/api/3/issue/{query.upper()}"
            response = httpx.get(url, auth=(email, token), timeout=30)
            response.raise_for_status()
            issue = response.json()
            fields = issue["fields"]

            from jira_client import _extract_description, fetch_ticket_comments
            desc = _extract_description(fields.get("description"))
            comments = fetch_ticket_comments(query.upper())

            result = (
                f"Ticket: {issue['key']}\n"
                f"Summary: {fields.get('summary', '')}\n"
                f"Status: {fields.get('status', {}).get('name', '')}\n"
                f"Priority: {fields.get('priority', {}).get('name', '')}\n"
                f"Reporter: {fields.get('reporter', {}).get('displayName', 'Unknown')}\n"
                f"Assignee: {fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned'}\n"
                f"Description: {desc}\n"
            )
            if comments:
                result += f"\n--- Comments ({len(comments)}) ---\n"
                for c in comments:
                    result += f"\n[{c['created']}] {c['author']}:\n{c['body']}\n"
            return result

        # Build JQL for search
        jql_parts = [f'project = "{project}"']

        # Status filter
        if status:
            if status.lower() == "open":
                excluded = ("Closed", "Done", "Resolved", "Cancel", "Cancelled",
                           "Completed", "Pending Customer", "Waiting for Customer",
                           "Pending User Verification", "Rejected")
                excluded_str = ", ".join(f'"{s}"' for s in excluded)
                jql_parts.append(f"status NOT IN ({excluded_str})")
            else:
                jql_parts.append(f'status = "{status}"')

        # Assignee filter
        if assignee:
            jql_parts.append(f'assignee = "{assignee}"')

        # Text search (only if not just filtering)
        if query and query.lower() not in ("all", "pending", "open", "tickets"):
            jql_parts.append(f'text ~ "{query}"')

        jql_parts.append("ORDER BY created DESC")
        jql = " AND ".join(jql_parts[:-1]) + " " + jql_parts[-1]

        url = f"{base_url}/rest/api/3/search/jql"
        payload = {
            "jql": jql,
            "fields": ["summary", "status", "priority", "reporter", "assignee", "created"],
            "maxResults": 15,
        }

        response = httpx.post(url, json=payload, auth=(email, token), timeout=30)
        response.raise_for_status()
        data = response.json()

        if not data.get("issues"):
            return f"No tickets found matching: query='{query}', status='{status}', assignee='{assignee}'"

        results = []
        for issue in data["issues"]:
            f = issue["fields"]
            assignee_name = f.get("assignee", {}).get("displayName", "Unassigned") if f.get("assignee") else "Unassigned"
            results.append(
                f"- {issue['key']} | Status: {f.get('status', {}).get('name', '')} | "
                f"Priority: {f.get('priority', {}).get('name', '')} | "
                f"Assignee: {assignee_name} | "
                f"Reporter: {f.get('reporter', {}).get('displayName', 'Unknown')} | "
                f"{f.get('summary', '')}"
            )

        return f"Found {len(results)} tickets:\n" + "\n".join(results)

    except Exception as e:
        return f"Jira search error: {str(e)}"

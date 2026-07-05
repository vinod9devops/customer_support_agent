"""
Multi-Agent Customer Support System for Cloud File Transfer (CFT).

Two modes:
1. Jira mode: Fetches pending SR tickets, lets you pick one, and suggests a response
2. Manual mode: Ask any CFT question directly

Usage:
    python main.py
"""

import os
import sys
from dotenv import load_dotenv

from agents import create_support_agent, create_qa_agent
from crew import Crew
from tools import TOOLS
from knowledge_base import refresh_knowledge_base

load_dotenv()


def _run_agents(person: str, customer: str, inquiry: str) -> str:
    """Run the two-agent pipeline and return the final response (used by sr1)."""
    support_agent = create_support_agent(customer)
    qa_agent = create_qa_agent(customer)

    inquiry_resolution = {
        "description": (
            f"{person} from {customer} raised a support ticket:\n"
            f"{inquiry}\n\n"
            "Search the CFT documentation knowledge base to find the relevant information. "
            "Provide a concise, accurate response based on official CFT documentation. "
            "Keep the answer short and directly relevant to the question."
        ),
        "expected_output": (
            "A concise, accurate response addressing the customer's question "
            "with references to CFT documentation."
        ),
        "tools": TOOLS,
        "agent": support_agent,
    }

    quality_assurance_review = {
        "description": (
            f"Review the response drafted for {person}'s CFT support ticket. "
            "Verify accuracy against CFT documentation using the search tool. "
            "If any relevant information is missing, add it.\n\n"
            "CRITICAL RULES:\n"
            "1. Output ONLY the customer-facing response. Nothing else.\n"
            "2. Do NOT include any preamble, internal notes, or commentary like "
            "'I found the documentation' or 'Let me provide the final response'.\n"
            "3. Do NOT include '---' separators before the greeting.\n"
            "4. Start directly with 'Hi [Name],' or the response content.\n"
            "5. Keep it concise and professional yet friendly."
        ),
        "expected_output": (
            "A final, concise response ready to be sent to the customer."
        ),
        "tools": TOOLS,
        "agent": qa_agent,
    }

    crew = Crew(
        agents=[support_agent, qa_agent],
        tasks=[inquiry_resolution, quality_assurance_review],
        memory=True,
        verbose=False,
    )

    return crew.kickoff(inputs={
        "customer": customer,
        "person": person,
        "inquiry": inquiry,
    })


def _run_single_agent(person: str, customer: str, inquiry: str) -> str:
    """Run a single agent for fast chat responses (used by sr2)."""
    support_agent = create_support_agent(customer)

    task = {
        "description": (
            f"{person} from {customer} asks:\n"
            f"{inquiry}\n\n"
            "Search the CFT documentation knowledge base to find the relevant information. "
            "Provide a concise, accurate, and complete response. "
            "Keep it short and directly relevant. Cite documentation sources."
        ),
        "expected_output": (
            "A concise, helpful response to the question."
        ),
        "tools": TOOLS,
        "agent": support_agent,
    }

    crew = Crew(
        agents=[support_agent],
        tasks=[task],
        memory=True,
        verbose=False,
    )

    return crew.kickoff(inputs={
        "customer": customer,
        "person": person,
        "inquiry": inquiry,
    })


def jira_mode():
    """Fetch tickets from Jira and process a selected one."""
    try:
        from jira_client import fetch_pending_tickets, display_tickets, fetch_team_members, display_team_members, get_ticket_with_history
    except ImportError:
        print("  ⚠️  Jira client not available. Install httpx.")
        return

    # Fetch and display team members
    print("\n  🔍 Fetching team members with open tickets...\n")
    try:
        members = fetch_team_members()
    except ValueError as e:
        print(f"  ❌ {e}")
        return
    except Exception as e:
        print(f"  ❌ Failed to fetch team members: {e}")
        return

    if not members:
        print("  No team members with open tickets found.")
        return

    display_team_members(members)

    print()
    member_choice = input("👤 Select Assignee name (#): ").strip()
    if not member_choice.isdigit() or int(member_choice) < 1 or int(member_choice) > len(members):
        print("  ❌ Invalid selection. Exiting.")
        return

    selected_member = members[int(member_choice) - 1]
    name = selected_member["displayName"]

    print(f"\n  🔍 Fetching pending tickets for {name}...\n")

    try:
        tickets = fetch_pending_tickets(name)
    except ValueError as e:
        print(f"  ❌ {e}")
        return
    except Exception as e:
        print(f"  ❌ Failed to fetch tickets: {e}")
        return

    if not tickets:
        print("  No pending tickets found.")
        return

    display_tickets(tickets)

    print()
    selection = input("🎯 Enter ticket # or SR number to work on (or 'q' to quit): ").strip()
    if selection.lower() == "q":
        return

    # Find the selected ticket
    selected = None
    if selection.isdigit():
        idx = int(selection) - 1
        if 0 <= idx < len(tickets):
            selected = tickets[idx]
    else:
        # Match by ticket key
        for t in tickets:
            if t["key"].lower() == selection.lower():
                selected = t
                break

    if not selected:
        print("  ❌ Invalid selection.")
        return

    print(f"\n  📋 Selected: {selected['key']} - {selected['summary']}")
    print(f"  📝 Description: {selected['description'][:200]}...")
    print(f"\n  ⏳ Analyzing and preparing response (including comment history)...\n")

    # Get full ticket context including comments
    inquiry = get_ticket_with_history(selected)
    reporter = selected["reporter"]

    result = _run_agents(reporter, reporter, inquiry)

    print("\n" + "=" * 60)
    print("📧 SUGGESTED RESPONSE")
    print("=" * 60)
    print(f"\n📌 Ticket: {selected['key']} - {selected['summary']}")
    print(f"👤 Requester: {selected['reporter']}")
    print("-" * 60)
    print(result)


def manual_mode():
    """Chat mode - ask CFT questions until user exits."""
    print()
    person = input("👤 Your name: ").strip() or "User"
    customer = input("🏢 Organisation (optional): ").strip() or "a government agency"
    print()
    print("  💬 Chat mode active. Type 'exit' or 'quit' to end.\n")

    while True:
        inquiry = input("❓ Your question: ").strip()
        if not inquiry:
            continue
        if inquiry.lower() in ("exit", "quit", "q"):
            print("\n  👋 Goodbye!")
            break

        print(f"\n  ⏳ Processing...\n")
        result = _run_single_agent(person, customer, inquiry)

        print("\n" + "=" * 60)
        print("📧 RESPONSE")
        print("=" * 60)
        print(result)
        print("\n")


def main():
    print("\n" + "=" * 60)
    print("  Cloud File Transfer (CFT) Support Agent")
    print("=" * 60)
    print()

    # Initialize knowledge base
    kb_status = refresh_knowledge_base()
    if kb_status["status"] == "cache_valid":
        print(f"  📚 Knowledge base ready ({kb_status['pages_cached']} pages, "
              f"last updated {kb_status['age_hours']}h ago)")

    # Check for command-line argument
    import sys
    mode = None
    if len(sys.argv) > 1:
        mode = sys.argv[1]

    if not mode:
        print()
        print("  Select mode:")
        print("  [1] Jira tickets - Fetch & resolve pending SR tickets")
        print("  [2] Manual query - Ask a CFT question directly")
        print()
        mode = input("  Choose (1/2): ").strip()

    if mode == "1":
        jira_mode()
    elif mode == "2":
        manual_mode()
    else:
        print("  Invalid choice. Exiting.")


if __name__ == "__main__":
    main()

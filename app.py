"""
CFT Support Agent - Streamlit Web UI

Features:
- Mode 1: Jira ticket resolution
- Mode 2: Chat with CFT knowledge base
- Copy to clipboard
- Chat history
- Dark mode toggle
- Knowledge base status
"""

import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

# Must be first Streamlit command
st.set_page_config(
    page_title="CFT Support Agent",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="expanded",
)

from agents import create_support_agent, create_qa_agent
from crew import Crew
from tools import TOOLS
from knowledge_base import refresh_knowledge_base

# --- Custom CSS ---
def apply_custom_css():
    st.markdown("""
    <style>
        .stApp { max-width: 1200px; margin: 0 auto; }
        .response-box {
            background-color: #f0f2f6;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 0;
            border-left: 4px solid #4CAF50;
        }
        .dark .response-box {
            background-color: #1e1e1e;
            border-left-color: #66bb6a;
        }
        .ticket-card {
            background-color: #ffffff;
            border-radius: 8px;
            padding: 15px;
            margin: 8px 0;
            border: 1px solid #e0e0e0;
            cursor: pointer;
        }
        .ticket-card:hover {
            border-color: #4CAF50;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .kb-status {
            font-size: 0.85em;
            color: #666;
            padding: 8px 12px;
            background: #f8f9fa;
            border-radius: 6px;
        }
        .copy-btn { margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

apply_custom_css()


def _render_copy_button(text: str, key: str):
    """Render a copyable text block using Streamlit's native copy functionality."""
    with st.popover("📋 Copy Response"):
        st.code(text, language=None)


# --- Session State Init ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "kb_initialized" not in st.session_state:
    st.session_state.kb_initialized = False
if "tickets" not in st.session_state:
    st.session_state.tickets = []
if "team_members" not in st.session_state:
    st.session_state.team_members = []


# --- Knowledge Base Init ---
@st.cache_resource
def init_knowledge_base():
    try:
        return refresh_knowledge_base()
    except Exception as e:
        return {"status": "error", "pages_cached": 0, "error": str(e)}


# --- Agent Functions ---
def run_single_agent(person: str, customer: str, inquiry: str) -> str:
    """Fast single-agent response for chat mode."""
    support_agent = create_support_agent(customer)
    task = {
        "description": (
            f"{person} from {customer} asks:\n"
            f"{inquiry}\n\n"
            "Search the CFT documentation knowledge base to find the relevant information. "
            "Provide a concise, accurate, and complete response. "
            "Keep it short and directly relevant. Cite documentation sources."
        ),
        "expected_output": "A concise, helpful response to the question.",
        "tools": TOOLS,
        "agent": support_agent,
    }
    crew = Crew(agents=[support_agent], tasks=[task], memory=True, verbose=False)
    return crew.kickoff(inputs={"customer": customer, "person": person, "inquiry": inquiry})


def run_two_agents(person: str, customer: str, inquiry: str, attachments: list = None) -> str:
    """Full two-agent pipeline for Jira tickets."""
    support_agent = create_support_agent(customer)
    qa_agent = create_qa_agent(customer)

    inquiry_resolution = {
        "description": (
            f"{person} from {customer} raised a support ticket:\n"
            f"{inquiry}\n\n"
            "Search the CFT documentation knowledge base to find the relevant information. "
            "Provide a concise, accurate response based on official CFT documentation. "
            "Keep the answer short and directly relevant to the question."
            + ("\n\nNote: Attachments from the ticket are included below. "
               "Review them for additional context." if attachments else "")
        ),
        "expected_output": "A concise, accurate response with references to CFT documentation.",
        "attachments": attachments or [],
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
        "expected_output": "A final, concise response ready to be sent to the customer. No preamble.",
        "tools": TOOLS,
        "agent": qa_agent,
    }

    crew = Crew(
        agents=[support_agent, qa_agent],
        tasks=[inquiry_resolution, quality_assurance_review],
        memory=True, verbose=False,
    )
    return crew.kickoff(inputs={"customer": customer, "person": person, "inquiry": inquiry})


# --- Sidebar ---
with st.sidebar:
    st.title("📁 CFT Support Agent")
    st.divider()

    # Mode selection
    mode = st.radio(
        "Select Mode",
        ["💬 Chat", "🎫 Jira Tickets"],
        index=0,
        help="Chat: Quick Q&A about CFT | Jira: Resolve support tickets"
    )

    st.divider()

    # Knowledge base status
    kb_status = init_knowledge_base()
    if kb_status["status"] == "cache_valid":
        st.markdown(f"""
        <div class="kb-status">
            📚 <strong>Knowledge Base</strong><br>
            {kb_status['pages_cached']} pages cached<br>
            Last updated: {kb_status['age_hours']}h ago
        </div>
        """, unsafe_allow_html=True)
    else:
        st.success(f"📚 KB refreshed: {kb_status['pages_cached']} pages")

    st.divider()

    # Dark mode toggle
    dark_mode = st.toggle("🌙 Dark Mode", value=False)
    if dark_mode:
        st.markdown("""
        <style>
            .stApp { background-color: #0e1117; color: #fafafa; }
            .response-box { background-color: #1e1e1e; border-left-color: #66bb6a; }
            .ticket-card { background-color: #1e1e1e; border-color: #333; }
        </style>
        """, unsafe_allow_html=True)

    st.divider()
    st.caption("Built with Claude + Streamlit")


# --- Main Content ---

if mode == "💬 Chat":
    st.header("💬 CFT Documentation Chat")
    st.caption("Ask any question about Cloud File Transfer (CFT)")

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask a question about CFT..."):
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Searching CFT docs..."):
                response = run_single_agent("User", "a government agency", prompt)
            st.markdown(response)
            _render_copy_button(response, f"chat_{len(st.session_state.chat_history)}")

        st.session_state.chat_history.append({"role": "assistant", "content": response})

    # Clear history button
    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()


elif mode == "🎫 Jira Tickets":
    st.header("🎫 Jira Ticket Resolution")
    st.caption("Fetch pending tickets and get AI-suggested responses")

    # Check Jira credentials
    if not os.environ.get("JIRA_EMAIL") or not os.environ.get("JIRA_API_TOKEN"):
        st.error("⚠️ JIRA_EMAIL and JIRA_API_TOKEN environment variables required.")
        st.info("Set them before running: `export JIRA_EMAIL=... && export JIRA_API_TOKEN=...`")
        st.stop()

    from jira_client import fetch_team_members, fetch_pending_tickets, display_tickets, get_ticket_with_history, fetch_ticket_comments, search_similar_tickets

    # Step 1: Fetch team members
    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("🔍 Fetch Team Members", type="primary"):
            with st.spinner("Loading team members..."):
                try:
                    st.session_state.team_members = fetch_team_members()
                except Exception as e:
                    st.error(f"Failed to fetch team members: {e}")

    # Step 2: Select assignee
    if st.session_state.team_members:
        member_names = [m["displayName"] for m in st.session_state.team_members]
        selected_member = st.selectbox("👤 Select Assignee", member_names)

        # Step 3: Fetch tickets
        if st.button("📋 Fetch Tickets"):
            with st.spinner(f"Fetching tickets for {selected_member}..."):
                try:
                    st.session_state.tickets = fetch_pending_tickets(selected_member)
                except Exception as e:
                    st.error(f"Failed to fetch tickets: {e}")

    # Step 4: Display tickets
    if st.session_state.tickets:
        st.subheader(f"📋 Pending Tickets ({len(st.session_state.tickets)})")

        for i, ticket in enumerate(st.session_state.tickets):
            with st.expander(f"**{ticket['key']}** - {ticket['summary']} [{ticket['status']}]"):
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Priority", ticket["priority"])
                col_b.metric("Status", ticket["status"])
                col_c.metric("Reporter", ticket["reporter"])

                st.text_area(
                    "Description",
                    ticket["description"][:500],
                    height=100,
                    disabled=True,
                    key=f"desc_{i}"
                )

                # Action buttons in one row with custom styling
                st.markdown("""
                <style>
                    div[data-testid="stHorizontalBlock"] > div:nth-child(1) button {
                        background-color: #4CAF50 !important; color: white !important;
                        width: 100% !important; height: 45px !important;
                    }
                    div[data-testid="stHorizontalBlock"] > div:nth-child(2) button {
                        background-color: #2196F3 !important; color: white !important;
                        width: 100% !important; height: 45px !important;
                    }
                    div[data-testid="stHorizontalBlock"] > div:nth-child(3) button {
                        background-color: #FF9800 !important; color: white !important;
                        width: 100% !important; height: 45px !important;
                    }
                </style>
                """, unsafe_allow_html=True)

                btn_col1, btn_col2, btn_col3 = st.columns(3)
                with btn_col1:
                    gen_clicked = st.button(f"🤖 Generate Response", key=f"gen_{i}")
                with btn_col2:
                    sum_clicked = st.button(f"📝 Summarize", key=f"sum_{i}")
                with btn_col3:
                    prev_clicked = st.button(f"🔍 Previous SRs", key=f"prev_{i}")

                # Display area below buttons
                if gen_clicked:
                    inquiry = get_ticket_with_history(ticket)
                    reporter = ticket["reporter"]

                    # Fetch attachments (text + images)
                    from jira_client import get_ticket_attachments_for_agent
                    with st.spinner("🤖 Analyzing ticket, attachments, and generating response..."):
                        try:
                            attachments = get_ticket_attachments_for_agent(ticket["key"])
                        except Exception:
                            attachments = []
                        response = run_two_agents(reporter, reporter, inquiry, attachments=attachments)

                    st.divider()
                    st.subheader("📧 Suggested Response")
                    st.markdown(response)
                    _render_copy_button(response, f"ticket_{i}")

                if sum_clicked:
                    with st.spinner("📝 Summarizing conversation..."):
                        try:
                            comments = fetch_ticket_comments(ticket["key"])
                            if not comments:
                                st.info("No comments found on this ticket.")
                            else:
                                convo = f"Ticket: {ticket['key']} - {ticket['summary']}\n"
                                convo += f"Reporter: {ticket['reporter']}\n"
                                convo += f"Description: {ticket['description']}\n\n"
                                convo += f"--- {len(comments)} Comments ---\n"
                                for c in comments:
                                    convo += f"\n[{c['created']}] {c['author']}:\n{c['body']}\n"

                                summary_prompt = (
                                    f"Summarize this support ticket conversation concisely. "
                                    f"Include: what was requested, key actions taken, current status, "
                                    f"and any pending items.\n\n{convo}"
                                )
                                summary = run_single_agent("Support", "CFT Team", summary_prompt)
                                st.divider()
                                st.subheader("📝 Ticket Summary")
                                st.markdown(summary)
                                _render_copy_button(summary, f"sum_r_{i}")
                        except Exception as e:
                            st.error(f"Failed to summarize: {e}")

                if prev_clicked:
                    with st.spinner("🔍 Searching for similar historical tickets..."):
                        try:
                            similar = search_similar_tickets(ticket)
                            if not similar:
                                st.info("No similar historical tickets found.")
                            else:
                                st.divider()
                                st.subheader(f"🔍 Similar Tickets ({len(similar)} found)")
                                for s in similar:
                                    status_icon = "✅" if s["status"] in ("Closed", "Done", "Resolved", "Completed") else "🔄"
                                    resolution = f" → {s['resolution']}" if s["resolution"] else ""
                                    st.markdown(
                                        f"{status_icon} **{s['key']}** - {s['summary']}  \n"
                                        f"&nbsp;&nbsp;&nbsp; Status: `{s['status']}{resolution}` | "
                                        f"Created: {s['created']}"
                                    )
                        except Exception as e:
                            st.error(f"Failed to search: {e}")
    elif st.session_state.team_members:
        st.info("Select an assignee and click 'Fetch Tickets' to see pending tickets.")

"""
Local knowledge base with daily refresh for CFT documentation.

- Fetches all CFT doc pages and stores them locally as markdown files.
- Only re-fetches if the last update was more than 24 hours ago.
- Provides semantic + keyword search to retrieve relevant chunks.
- Uses TF-IDF for lightweight semantic matching (no external API needed).
"""

import os
import json
import math
import hashlib
import httpx
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path


# All known CFT documentation pages
CFT_DOC_PAGES = [
    ("overview", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/overview.md"),
    ("specifications", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/general/specifications.md"),
    ("guidelines", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/general/guidelines.md"),
    ("prerequisites", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/gettingstarted/prerequisites.md"),
    ("get-started", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/gettingstarted/get-started.md"),
    ("concepts", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/gettingstarted/concepts.md"),
    ("file-transfers", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/gettingstarted/file-transfers.md"),
    ("release-notes", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/gettingstarted/release-notes.md"),
    ("preonboarding", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/onboarding/preonboarding.md"),
    ("subscribing", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/onboarding/subscribing.md"),
    ("postonboarding", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/onboarding/postonboarding.md"),
    ("admin-portal", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/adminportal/cloud-file-transfer-admin-portal.md"),
    ("log-in", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/adminportal/log-in-to-admin-portal.md"),
    ("user-roles", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/adminportal/user-roles.md"),
    ("manage-projects", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/adminportal/manage-projects.md"),
    ("manage-applications", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/adminportal/manage-applications.md"),
    ("manage-workflows", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/adminportal/manage-workflows.md"),
    ("manage-keys", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/adminportal/manage-keys.md"),
    ("manage-notifications", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/adminportal/manage-notifications.md"),
    ("view-logs-page", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/adminportal/view-logs-page.md"),
    ("view-logs-files", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/adminportal/view-logs-files.md"),
    ("logs-file-status", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/adminportal/logs-file-status.md"),
    ("view-logs", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/adminportal/view-logs.md"),
    ("usage-dashboard", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/adminportal/usage-dashboard.md"),
    ("https-integrations", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/integrations/integrations.md"),
    ("https-prerequisites", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/integrations/prerequisites.md"),
    ("https-quickstart", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/integrations/quick-start.md"),
    ("testing-with-curl", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/integrations/testing-with-curl.md"),
    ("sftp-setup", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/sftp/sftp-setup.md"),
    ("sftp-scheduler", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/sftp/sftp-scheduler.md"),
    ("sftp-client", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/sftp/sftp-client.md"),
    ("datasecurity-overview", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/datasecurity/overview.md"),
    ("encryption-overview", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/datasecurity/encryption-overview.md"),
    ("pgp", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/datasecurity/pgp.md"),
    ("slift", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/datasecurity/slift.md"),
    ("cdr", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/datasecurity/cdr.md"),
    ("scan-bypass", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/datasecurity/scan-bypass.md"),
    ("sensitive-high", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/datasecurity/sensitive-high.md"),
    ("security-policies", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/datasecurity/security-policies.md"),
    ("security-policies-https", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/datasecurity/security-policies-https.md"),
    ("security-policies-sftp", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/datasecurity/security-policies-sftp.md"),
    ("webhooks", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/webhooks/webhooks.md"),
    ("webhooks-setup", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/webhooks/webhooks-setup.md"),
    ("payload-samples", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/webhooks/payload-samples.md"),
    ("faq", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/faq.md"),
    ("troubleshooting-admin-portal", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/support/troubleshooting/admin-portal.md"),
    ("troubleshooting-sftp", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/support/troubleshooting/sftp.md"),
    ("troubleshooting-data-security", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/support/troubleshooting/data-security.md"),
    ("contact-us", "https://docs.developer.tech.gov.sg/docs/cft-user-guide/contact-us.md"),
]

CACHE_DIR = Path(__file__).parent / ".kb_cache"
METADATA_FILE = CACHE_DIR / "_metadata.json"


def _load_metadata() -> dict:
    """Load cache metadata (last update timestamp, page hashes)."""
    if METADATA_FILE.exists():
        return json.loads(METADATA_FILE.read_text())
    return {"last_updated": None, "pages": {}}


def _save_metadata(metadata: dict):
    """Save cache metadata."""
    METADATA_FILE.write_text(json.dumps(metadata, indent=2))


def _needs_refresh(metadata: dict) -> bool:
    """Check if we need to refresh (>24h since last update or no cache)."""
    if not metadata["last_updated"]:
        return True
    last = datetime.fromisoformat(metadata["last_updated"])
    return datetime.now() - last > timedelta(hours=24)


def refresh_knowledge_base(force: bool = False) -> dict:
    """
    Fetch all CFT doc pages and cache them locally.
    Only re-fetches if >24h since last update or if forced.
    Returns stats about the refresh.
    """
    CACHE_DIR.mkdir(exist_ok=True)
    metadata = _load_metadata()

    if not force and not _needs_refresh(metadata):
        # Still re-index local docs (they might have changed)
        local_count = _index_local_docs()
        age_hours = (datetime.now() - datetime.fromisoformat(metadata["last_updated"])).total_seconds() / 3600
        return {
            "status": "cache_valid",
            "pages_cached": len(metadata["pages"]) + local_count,
            "age_hours": round(age_hours, 1),
        }

    print("  📥 Refreshing CFT knowledge base from documentation...")

    updated = 0
    errors = 0

    for page_name, url in CFT_DOC_PAGES:
        try:
            response = httpx.get(url, timeout=15, follow_redirects=True)
            response.raise_for_status()
            content = response.text

            # Check if content changed
            content_hash = hashlib.md5(content.encode()).hexdigest()
            if metadata["pages"].get(page_name, {}).get("hash") == content_hash:
                continue  # No change, skip writing

            # Save to cache
            cache_file = CACHE_DIR / f"{page_name}.md"
            cache_file.write_text(content)

            metadata["pages"][page_name] = {
                "hash": content_hash,
                "url": url,
                "size": len(content),
            }
            updated += 1

        except Exception as e:
            errors += 1
            print(f"    ⚠️  Failed to fetch {page_name}: {e}")

    metadata["last_updated"] = datetime.now().isoformat()
    _save_metadata(metadata)

    # Also index local docs
    local_count = _index_local_docs()

    total = len(metadata["pages"]) + local_count
    print(f"  ✅ Knowledge base ready: {total} pages ({local_count} local), {updated} updated, {errors} errors")

    return {"status": "refreshed", "pages_cached": total, "updated": updated, "errors": errors}


LOCAL_DOCS_DIR = Path(__file__).parent / "local_docs"


def _index_local_docs() -> int:
    """Index markdown files from the local_docs/ folder into the cache."""
    if not LOCAL_DOCS_DIR.exists():
        return 0

    count = 0
    for md_file in LOCAL_DOCS_DIR.rglob("*.md"):
        # Copy to cache with a "local-" prefix to avoid name collisions
        relative = md_file.relative_to(LOCAL_DOCS_DIR)
        cache_name = f"local-{relative.stem}"
        cache_file = CACHE_DIR / f"{cache_name}.md"
        cache_file.write_text(md_file.read_text())
        count += 1

    if count > 0:
        print(f"  📂 Indexed {count} local doc(s) from local_docs/")
    return count


def search_knowledge_base(query: str, max_results: int = 8, max_chars: int = 12000) -> str:
    """
    Search the local knowledge base using TF-IDF semantic similarity + keyword matching.
    Returns concatenated relevant sections.
    """
    if not CACHE_DIR.exists():
        return "Knowledge base not initialized. Run refresh_knowledge_base() first."

    # Collect all sections
    all_sections = []
    for cache_file in CACHE_DIR.glob("*.md"):
        content = cache_file.read_text()
        page_name = cache_file.stem
        sections = _split_into_sections(content, page_name)
        all_sections.extend(sections)

    if not all_sections:
        return "Knowledge base is empty."

    # Build TF-IDF index and score
    query_terms = set(query.lower().split())
    _expand_query(query_terms)

    # Tokenize all docs for IDF calculation
    doc_tokens = [_tokenize(s["text"] + " " + s["heading"]) for s in all_sections]
    num_docs = len(doc_tokens)

    # Calculate IDF for all terms
    doc_freq = Counter()
    for tokens in doc_tokens:
        unique = set(tokens)
        for t in unique:
            doc_freq[t] += 1

    scored_chunks = []
    query_tokens = _tokenize(query)
    expanded_query_tokens = list(query_tokens) + list(query_terms)

    for idx, section in enumerate(all_sections):
        tokens = doc_tokens[idx]
        if not tokens:
            continue

        # TF-IDF score
        tf = Counter(tokens)
        tfidf_score = 0.0
        for qt in expanded_query_tokens:
            if qt in tf:
                term_freq = tf[qt] / len(tokens)
                idf = math.log((num_docs + 1) / (doc_freq.get(qt, 0) + 1)) + 1
                tfidf_score += term_freq * idf

        # Bonus: heading match (important signal)
        heading_lower = section["heading"].lower()
        for qt in query_tokens:
            if qt in heading_lower:
                tfidf_score += 2.0

        # Bonus: exact phrase fragments (2+ word sequences from query)
        text_lower = section["text"].lower()
        query_words = query.lower().split()
        for j in range(len(query_words) - 1):
            bigram = f"{query_words[j]} {query_words[j+1]}"
            if bigram in text_lower:
                tfidf_score += 3.0

        if tfidf_score > 0:
            scored_chunks.append((tfidf_score, section))

    # Sort by relevance score (descending)
    scored_chunks.sort(key=lambda x: x[0], reverse=True)

    # Take top results within char limit
    results = []
    total_chars = 0
    for score, section in scored_chunks[:max_results]:
        if total_chars + len(section["text"]) > max_chars:
            remaining = max_chars - total_chars
            if remaining > 200:
                results.append(f"### [{section['page']}] {section['heading']}\n{section['text'][:remaining]}...")
            break
        results.append(f"### [{section['page']}] {section['heading']}\n{section['text']}")
        total_chars += len(section["text"])

    if not results:
        return f"No relevant information found for: {query}"

    return "\n\n---\n\n".join(results)


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words, removing punctuation and stop words."""
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "through", "during",
        "before", "after", "above", "below", "between", "out", "off", "over",
        "under", "again", "further", "then", "once", "here", "there", "when",
        "where", "why", "how", "all", "each", "every", "both", "few", "more",
        "most", "other", "some", "such", "no", "not", "only", "own", "same",
        "so", "than", "too", "very", "just", "because", "but", "and", "or",
        "if", "while", "this", "that", "these", "those", "it", "its", "you",
        "your", "we", "our", "they", "their", "he", "she", "him", "her",
    }
    words = re.findall(r'[a-z0-9]+', text.lower())
    return [w for w in words if w not in stop_words and len(w) > 1]


def _expand_query(terms: set):
    """Expand query terms with related words."""
    expansions = {
        "sla": {"service", "level", "agreement", "uptime", "availability", "performance", "baseline"},
        "sftp": {"ssh", "server", "client", "port", "connection"},
        "https": {"api", "rest", "curl", "upload", "download", "endpoint"},
        "error": {"troubleshooting", "issue", "problem", "failed", "failure"},
        "setup": {"configure", "configuration", "getting", "started", "onboarding"},
        "encrypt": {"encryption", "decryption", "pgp", "slift", "key", "keys"},
        "webhook": {"webhooks", "notification", "notifications", "payload"},
        "size": {"limit", "limits", "maximum", "file", "gb", "mb"},
        "security": {"policy", "policies", "scan", "scanning", "malware", "cdr"},
        "workflow": {"workflows", "transfer", "sender", "receiver"},
        "log": {"logs", "status", "dashboard", "monitoring"},
        "onboard": {"onboarding", "subscription", "provisioning", "subscribe"},
    }
    for term in list(terms):
        for key, related in expansions.items():
            if key in term or term in key:
                terms.update(related)


def _split_into_sections(content: str, page_name: str) -> list[dict]:
    """Split markdown content into sections based on headings."""
    sections = []
    current_heading = "Introduction"
    current_text = []

    for line in content.split("\n"):
        if line.startswith("##"):
            # Save previous section
            if current_text:
                text = "\n".join(current_text).strip()
                if text:
                    sections.append({
                        "page": page_name,
                        "heading": current_heading,
                        "text": text,
                    })
            current_heading = line.lstrip("#").strip()
            current_text = []
        else:
            current_text.append(line)

    # Save last section
    if current_text:
        text = "\n".join(current_text).strip()
        if text:
            sections.append({
                "page": page_name,
                "heading": current_heading,
                "text": text,
            })

    return sections

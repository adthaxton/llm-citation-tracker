"""
geo-content-auditor
===================
Scrapes a URL and scores it against a GEO (Generative Engine Optimization)
readiness checklist. Evaluates entity signals, structured data, E-E-A-T
indicators, citation-friendly formatting, and heading structure.

Outputs a scored report to the terminal and saves it as a text file.

Requirements:
    pip install requests beautifulsoup4 python-dotenv

Usage:
    python geo_content_auditor.py https://example.com/your-page

Output:
    geo_audit_[domain]_[timestamp].txt
"""

import sys
import re
import json
import datetime
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# ─── CONFIG ──────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Schema types most relevant to GEO/AI discoverability
GEO_RELEVANT_SCHEMA = [
    "FAQPage",
    "HowTo",
    "Article",
    "NewsArticle",
    "BlogPosting",
    "Organization",
    "LocalBusiness",
    "Person",
    "Product",
    "Service",
    "WebPage",
    "BreadcrumbList",
    "Speakable",
]

# E-E-A-T signal phrases to look for in page content
EEAT_SIGNALS = [
    "years of experience",
    "certified",
    "licensed",
    "founded",
    "our team",
    "our experts",
    "author",
    "written by",
    "reviewed by",
    "published",
    "last updated",
    "sources",
    "references",
    "according to",
    "research shows",
    "studies show",
    "data shows",
]

# Citation-friendly formatting indicators
CITATION_SIGNALS = [
    "according to",
    "research shows",
    "studies indicate",
    "data suggests",
    "experts say",
    "the answer is",
    "in summary",
    "to summarize",
    "the key takeaway",
    "step 1",
    "step 2",
    "first,",
    "second,",
    "third,",
    "finally,",
]


# ─── FETCH PAGE ──────────────────────────────────────────────────────────────

def fetch_page(url: str) -> BeautifulSoup:
    """Fetch a URL and return a BeautifulSoup object."""
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


# ─── AUDIT CHECKS ────────────────────────────────────────────────────────────

def check_title(soup: BeautifulSoup) -> dict:
    title = soup.find("title")
    text = title.get_text(strip=True) if title else ""
    return {
        "present": bool(text),
        "length": len(text),
        "value": text,
        "score": 2 if text and 30 <= len(text) <= 65 else (1 if text else 0),
        "max": 2,
        "note": (
            "Good length" if text and 30 <= len(text) <= 65
            else "Too short or too long" if text
            else "Missing title tag"
        ),
    }


def check_meta_description(soup: BeautifulSoup) -> dict:
    meta = soup.find("meta", attrs={"name": "description"})
    text = meta.get("content", "").strip() if meta else ""
    return {
        "present": bool(text),
        "length": len(text),
        "value": text[:120] + "..." if len(text) > 120 else text,
        "score": 2 if text and 100 <= len(text) <= 160 else (1 if text else 0),
        "max": 2,
        "note": (
            "Good length" if text and 100 <= len(text) <= 160
            else "Too short or too long" if text
            else "Missing meta description"
        ),
    }


def check_headings(soup: BeautifulSoup) -> dict:
    h1s = soup.find_all("h1")
    h2s = soup.find_all("h2")
    h3s = soup.find_all("h3")

    has_single_h1 = len(h1s) == 1
    has_h2s = len(h2s) >= 2
    has_hierarchy = len(h2s) > 0

    score = 0
    if has_single_h1:
        score += 2
    if has_h2s:
        score += 2
    if has_hierarchy:
        score += 1

    return {
        "h1_count": len(h1s),
        "h2_count": len(h2s),
        "h3_count": len(h3s),
        "h1_text": h1s[0].get_text(strip=True) if h1s else "",
        "score": score,
        "max": 5,
        "note": (
            f"H1: {len(h1s)}, H2: {len(h2s)}, H3: {len(h3s)} — "
            + ("single H1 good" if has_single_h1 else "needs exactly one H1")
            + (", good H2 structure" if has_h2s else ", needs more H2s")
        ),
    }


def check_schema(soup: BeautifulSoup) -> dict:
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    found_types = []
    raw_schemas = []

    for script in scripts:
        try:
            data = json.loads(script.string or "")
            raw_schemas.append(data)
            if isinstance(data, dict):
                schema_type = data.get("@type", "")
                if isinstance(schema_type, list):
                    found_types.extend(schema_type)
                elif schema_type:
                    found_types.append(schema_type)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        t = item.get("@type", "")
                        if isinstance(t, list):
                            found_types.extend(t)
                        elif t:
                            found_types.append(t)
        except (json.JSONDecodeError, TypeError):
            continue

    geo_relevant_found = [t for t in found_types if t in GEO_RELEVANT_SCHEMA]
    has_faq = "FAQPage" in found_types
    has_org = any(t in found_types for t in ["Organization", "LocalBusiness"])
    has_article = any(t in found_types for t in ["Article", "NewsArticle", "BlogPosting"])

    score = 0
    if found_types:
        score += 2
    if geo_relevant_found:
        score += 2
    if has_faq:
        score += 3
    if has_org:
        score += 2
    if has_article:
        score += 1

    return {
        "schema_count": len(scripts),
        "types_found": found_types,
        "geo_relevant": geo_relevant_found,
        "has_faq": has_faq,
        "has_org": has_org,
        "has_article": has_article,
        "score": min(score, 10),
        "max": 10,
        "note": (
            f"Found: {', '.join(found_types) if found_types else 'none'}"
            + (" | FAQPage present - strong GEO signal" if has_faq else " | No FAQPage schema - consider adding")
        ),
    }


def check_eeat(soup: BeautifulSoup) -> dict:
    text = soup.get_text(separator=" ", strip=True).lower()
    found = [s for s in EEAT_SIGNALS if s in text]
    score = min(len(found) * 2, 10)

    return {
        "signals_found": found,
        "count": len(found),
        "score": score,
        "max": 10,
        "note": (
            f"{len(found)} E-E-A-T signals found: {', '.join(found[:5])}"
            + ("..." if len(found) > 5 else "")
            if found else "No E-E-A-T signals detected - add author info, dates, sources"
        ),
    }


def check_citation_friendliness(soup: BeautifulSoup) -> dict:
    text = soup.get_text(separator=" ", strip=True).lower()
    found = [s for s in CITATION_SIGNALS if s in text]

    # Check for Q&A or definition patterns
    has_questions = bool(re.search(r'\bwhat is\b|\bhow (do|does|to)\b|\bwhy (is|does|do)\b', text))
    has_lists = len(soup.find_all(["ul", "ol"])) >= 2
    has_tables = len(soup.find_all("table")) >= 1

    score = 0
    score += min(len(found), 4)
    if has_questions:
        score += 2
    if has_lists:
        score += 2
    if has_tables:
        score += 2

    return {
        "citation_phrases": found,
        "has_questions": has_questions,
        "has_lists": has_lists,
        "has_tables": has_tables,
        "score": min(score, 10),
        "max": 10,
        "note": (
            f"{len(found)} citation-friendly phrases, "
            f"{'has' if has_questions else 'no'} Q&A patterns, "
            f"{'has' if has_lists else 'no'} lists, "
            f"{'has' if has_tables else 'no'} tables"
        ),
    }


def check_entity_signals(soup: BeautifulSoup) -> dict:
    text = soup.get_text(separator=" ", strip=True)

    # Look for entity-like patterns: proper nouns, brand mentions, location signals
    proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b', text)
    unique_proper = list(set(proper_nouns))

    # Check for internal links (entity relationships)
    internal_links = []
    base = urlparse(soup.find("base", href=True)["href"] if soup.find("base", href=True) else "")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/") or href.startswith("#"):
            internal_links.append(href)

    has_about = any(
        phrase in text.lower()
        for phrase in ["about us", "our story", "who we are", "our mission"]
    )

    score = 0
    if len(unique_proper) >= 10:
        score += 3
    if len(internal_links) >= 5:
        score += 3
    if has_about:
        score += 2
    if len(unique_proper) >= 5:
        score += 2

    return {
        "proper_noun_count": len(unique_proper),
        "internal_link_count": len(internal_links),
        "has_about_signals": has_about,
        "score": min(score, 10),
        "max": 10,
        "note": (
            f"{len(unique_proper)} unique proper nouns, "
            f"{len(internal_links)} internal links"
            + (" | About/org signals present" if has_about else " | No about/org signals found")
        ),
    }


def check_content_length(soup: BeautifulSoup) -> dict:
    # Remove script and style tags before counting
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    word_count = len(text.split())

    score = 0
    if word_count >= 300:
        score += 2
    if word_count >= 800:
        score += 2
    if word_count >= 1500:
        score += 1

    return {
        "word_count": word_count,
        "score": score,
        "max": 5,
        "note": (
            f"{word_count} words — "
            + ("strong depth" if word_count >= 1500
               else "good depth" if word_count >= 800
               else "adequate" if word_count >= 300
               else "too thin for GEO - aim for 800+ words")
        ),
    }


# ─── REPORT ──────────────────────────────────────────────────────────────────

def grade(score: int, max_score: int) -> str:
    pct = score / max_score if max_score else 0
    if pct >= 0.85:
        return "STRONG"
    elif pct >= 0.65:
        return "GOOD"
    elif pct >= 0.40:
        return "NEEDS WORK"
    else:
        return "WEAK"


def build_report(url: str, results: dict, total: int, max_total: int, timestamp: str) -> str:
    pct = round(total / max_total * 100)
    overall = grade(total, max_total)

    lines = [
        "=" * 70,
        "GEO CONTENT AUDIT REPORT",
        f"URL: {url}",
        f"Run: {timestamp}",
        f"Overall score: {total}/{max_total} ({pct}%) — {overall}",
        "=" * 70,
        "",
    ]

    sections = [
        ("Title Tag", "title"),
        ("Meta Description", "meta_description"),
        ("Heading Structure", "headings"),
        ("Structured Data / Schema", "schema"),
        ("E-E-A-T Signals", "eeat"),
        ("Citation-Friendly Formatting", "citation_friendliness"),
        ("Entity Signals", "entity_signals"),
        ("Content Depth", "content_length"),
    ]

    for label, key in sections:
        r = results[key]
        g = grade(r["score"], r["max"])
        lines.append(f"[ {g:<10} ] {label} — {r['score']}/{r['max']}")
        lines.append(f"             {r['note']}")
        lines.append("")

    lines += [
        "=" * 70,
        "RECOMMENDATIONS",
        "=" * 70,
        "",
    ]

    recs = []

    if not results["schema"]["has_faq"]:
        recs.append("Add FAQPage schema — this is one of the strongest GEO signals. Identify 3-5 questions your page answers and mark them up.")

    if results["eeat"]["count"] < 3:
        recs.append("Strengthen E-E-A-T signals: add author byline, publication/update date, and cite sources or research to support claims.")

    if not results["citation_friendliness"]["has_questions"]:
        recs.append("Add question-based headings (What is X? How does Y work?) — LLMs are trained on Q&A patterns and tend to cite pages structured this way.")

    if not results["citation_friendliness"]["has_lists"]:
        recs.append("Add structured lists or numbered steps — list-formatted content is easier for LLMs to extract and cite.")

    if results["content_length"]["word_count"] < 800:
        recs.append(f"Increase content depth — currently {results['content_length']['word_count']} words. Aim for 800-1500+ for competitive GEO topics.")

    if not results["schema"]["has_org"]:
        recs.append("Add Organization or LocalBusiness schema to establish entity identity — helps LLMs understand who you are.")

    if results["headings"]["h1_count"] != 1:
        recs.append(f"Fix H1 structure — found {results['headings']['h1_count']} H1 tags. Pages should have exactly one H1.")

    if not recs:
        recs.append("Page is well-optimized for GEO. Continue monitoring citation rates with citation_tracker.py.")

    for i, rec in enumerate(recs, 1):
        lines.append(f"{i}. {rec}")
        lines.append("")

    lines += ["=" * 70, ""]
    return "\n".join(lines)


# ─── MAIN ────────────────────────────────────────────────────────────────────

def run(url: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    domain = urlparse(url).netloc.replace("www.", "")
    safe_domain = re.sub(r'[^\w]', '_', domain)
    safe_ts = timestamp.replace(":", "-").replace(" ", "_")
    output_file = f"geo_audit_{safe_domain}_{safe_ts}.txt"

    print(f"\nGEO Content Auditor")
    print(f"URL: {url}")
    print(f"Fetching page...")

    try:
        soup = fetch_page(url)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page: {e}")
        sys.exit(1)

    print("Running checks...\n")

    results = {
        "title": check_title(soup),
        "meta_description": check_meta_description(soup),
        "headings": check_headings(soup),
        "schema": check_schema(soup),
        "eeat": check_eeat(soup),
        "citation_friendliness": check_citation_friendliness(soup),
        "entity_signals": check_entity_signals(soup),
        "content_length": check_content_length(soup),
    }

    total = sum(r["score"] for r in results.values())
    max_total = sum(r["max"] for r in results.values())

    report = build_report(url, results, total, max_total, timestamp)

    print(report)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Report saved to: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python geo_content_auditor.py https://example.com/your-page")
        sys.exit(1)
    run(sys.argv[1])

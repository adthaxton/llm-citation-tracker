"""
geo-batch-auditor
=================
Run GEO readiness audits across a list of URLs in bulk.

Accepts a CSV or plain text file of URLs, runs the GEO content audit on each,
and outputs a consolidated CSV report with scores and recommendations for every page.

Designed to work with URL lists exported from Screaming Frog, Google Search Console,
or any spreadsheet. No crawling — you provide the URLs, this tool audits them.

Requirements:
    pip install requests beautifulsoup4 python-dotenv

Usage:
    python geo_batch_auditor.py urls.txt
    python geo_batch_auditor.py urls.csv
    python geo_batch_auditor.py urls.csv --column url
    python geo_batch_auditor.py urls.txt --delay 2 --output my_report.csv

Arguments:
    input_file          Path to a .txt or .csv file containing URLs
    --column            Column name containing URLs (CSV only, default: first column)
    --delay             Seconds to wait between requests (default: 1)
    --output            Output CSV filename (default: geo_batch_report_[timestamp].csv)
    --limit             Max number of URLs to audit (optional)

Output:
    geo_batch_report_[timestamp].csv — full scored report for every URL
    geo_batch_summary_[timestamp].txt — summary of top issues across all pages
"""

import sys
import csv
import os
import time
import datetime
import argparse
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import re
import json

# ─── CONFIG ──────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

REQUEST_TIMEOUT = 15

GEO_RELEVANT_SCHEMA = [
    "FAQPage", "HowTo", "Article", "NewsArticle", "BlogPosting",
    "Organization", "LocalBusiness", "Person", "Product", "Service",
    "WebPage", "BreadcrumbList", "Speakable",
]

EEAT_SIGNALS = [
    "years of experience", "certified", "licensed", "founded", "our team",
    "our experts", "author", "written by", "reviewed by", "published",
    "last updated", "sources", "references", "according to",
    "research shows", "studies show", "data shows",
]

CITATION_SIGNALS = [
    "according to", "research shows", "studies indicate", "data suggests",
    "experts say", "the answer is", "in summary", "to summarize",
    "the key takeaway", "step 1", "step 2", "first,", "second,", "third,",
    "finally,",
]


# ─── URL LOADING ─────────────────────────────────────────────────────────────

def load_urls(filepath, column=None):
    """Load URLs from a .txt or .csv file."""
    urls = []
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".csv":
        with open(filepath, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []

            if column and column in fieldnames:
                col = column
            elif fieldnames:
                col = fieldnames[0]
                print(f"Using column: '{col}'")
            else:
                print("Error: CSV has no headers.")
                sys.exit(1)

            for row in reader:
                url = row.get(col, "").strip()
                if url and url.startswith("http"):
                    urls.append(url)
    else:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                url = line.strip()
                if url and url.startswith("http"):
                    urls.append(url)

    return urls


# ─── PAGE FETCH ──────────────────────────────────────────────────────────────

def fetch_page(url):
    """Fetch a URL and return BeautifulSoup. Returns None on error."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser"), response.status_code, None
    except requests.exceptions.HTTPError as e:
        return None, e.response.status_code if e.response else 0, str(e)
    except requests.exceptions.RequestException as e:
        return None, 0, str(e)


# ─── AUDIT CHECKS ────────────────────────────────────────────────────────────

def check_title(soup):
    title = soup.find("title")
    text = title.get_text(strip=True) if title else ""
    score = 2 if text and 30 <= len(text) <= 65 else (1 if text else 0)
    return {"score": score, "max": 2, "value": text[:80], "note": (
        "Good" if score == 2 else "Too short/long" if text else "Missing"
    )}


def check_meta_description(soup):
    meta = soup.find("meta", attrs={"name": "description"})
    text = meta.get("content", "").strip() if meta else ""
    score = 2 if text and 100 <= len(text) <= 160 else (1 if text else 0)
    return {"score": score, "max": 2, "value": text[:100], "note": (
        "Good" if score == 2 else "Too short/long" if text else "Missing"
    )}


def check_headings(soup):
    h1s = soup.find_all("h1")
    h2s = soup.find_all("h2")
    score = 0
    if len(h1s) == 1: score += 2
    if len(h2s) >= 2: score += 2
    if len(h2s) > 0: score += 1
    return {
        "score": min(score, 5), "max": 5,
        "h1_count": len(h1s), "h2_count": len(h2s), "h3_count": len(soup.find_all("h3")),
        "h1_text": h1s[0].get_text(strip=True)[:60] if h1s else "",
        "note": f"H1:{len(h1s)} H2:{len(h2s)} H3:{len(soup.find_all('h3'))}"
    }


def check_schema(soup):
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    found_types = []
    for script in scripts:
        try:
            data = json.loads(script.string or "")
            if isinstance(data, dict):
                t = data.get("@type", "")
                if isinstance(t, list): found_types.extend(t)
                elif t: found_types.append(t)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        t = item.get("@type", "")
                        if isinstance(t, list): found_types.extend(t)
                        elif t: found_types.append(t)
        except: continue

    geo_relevant = [t for t in found_types if t in GEO_RELEVANT_SCHEMA]
    has_faq = "FAQPage" in found_types
    has_org = any(t in found_types for t in ["Organization", "LocalBusiness"])
    has_article = any(t in found_types for t in ["Article", "NewsArticle", "BlogPosting"])

    score = 0
    if found_types: score += 2
    if geo_relevant: score += 2
    if has_faq: score += 3
    if has_org: score += 2
    if has_article: score += 1

    return {
        "score": min(score, 10), "max": 10,
        "types": ", ".join(found_types) if found_types else "none",
        "has_faq": has_faq, "has_org": has_org, "has_article": has_article,
        "note": f"{'FAQPage ' if has_faq else ''}{'Org ' if has_org else ''}{'Article' if has_article else ''}" or "No GEO schema"
    }


def check_eeat(soup):
    text = soup.get_text(separator=" ", strip=True).lower()
    found = [s for s in EEAT_SIGNALS if s in text]
    return {
        "score": min(len(found) * 2, 10), "max": 10,
        "count": len(found),
        "signals": ", ".join(found[:5]),
        "note": f"{len(found)} signals found" if found else "No E-E-A-T signals"
    }


def check_citation_friendliness(soup):
    text = soup.get_text(separator=" ", strip=True).lower()
    found = [s for s in CITATION_SIGNALS if s in text]
    has_questions = bool(re.search(r'\bwhat is\b|\bhow (do|does|to)\b|\bwhy (is|does|do)\b', text))
    has_lists = len(soup.find_all(["ul", "ol"])) >= 2
    has_tables = len(soup.find_all("table")) >= 1
    score = min(len(found), 4)
    if has_questions: score += 2
    if has_lists: score += 2
    if has_tables: score += 2
    return {
        "score": min(score, 10), "max": 10,
        "has_questions": has_questions, "has_lists": has_lists, "has_tables": has_tables,
        "phrase_count": len(found),
        "note": f"Q&A:{'Y' if has_questions else 'N'} Lists:{'Y' if has_lists else 'N'} Tables:{'Y' if has_tables else 'N'}"
    }


def check_content_length(soup):
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    word_count = len(soup.get_text(separator=" ", strip=True).split())
    score = 0
    if word_count >= 300: score += 2
    if word_count >= 800: score += 2
    if word_count >= 1500: score += 1
    return {
        "score": score, "max": 5, "word_count": word_count,
        "note": f"{word_count} words - {'strong' if word_count >= 1500 else 'good' if word_count >= 800 else 'adequate' if word_count >= 300 else 'thin'}"
    }


# ─── RECOMMENDATIONS ─────────────────────────────────────────────────────────

def get_top_recommendations(results):
    recs = []
    if not results["schema"]["has_faq"]:
        recs.append("Add FAQPage schema")
    if results["eeat"]["count"] < 3:
        recs.append("Strengthen E-E-A-T signals (author, date, sources)")
    if not results["citation"]["has_questions"]:
        recs.append("Add Q&A formatted content")
    if not results["citation"]["has_lists"]:
        recs.append("Add structured lists or numbered steps")
    if results["content"]["word_count"] < 800:
        recs.append(f"Increase content depth (currently {results['content']['word_count']} words)")
    if not results["schema"]["has_org"]:
        recs.append("Add Organization/LocalBusiness schema")
    if results["headings"]["h1_count"] != 1:
        recs.append(f"Fix H1 count (found {results['headings']['h1_count']}, need 1)")
    if results["title"]["score"] == 0:
        recs.append("Add title tag")
    return " | ".join(recs[:3]) if recs else "Well optimized"


def grade(score, max_score):
    pct = score / max_score if max_score else 0
    if pct >= 0.85: return "STRONG"
    elif pct >= 0.65: return "GOOD"
    elif pct >= 0.40: return "NEEDS WORK"
    else: return "WEAK"


# ─── MAIN ────────────────────────────────────────────────────────────────────

def run():
    parser = argparse.ArgumentParser(description="GEO Batch Auditor — audit multiple URLs for GEO readiness")
    parser.add_argument("input_file", help="Path to .txt or .csv file containing URLs")
    parser.add_argument("--column", default=None, help="CSV column name containing URLs")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between requests (default: 1)")
    parser.add_argument("--output", default=None, help="Output CSV filename")
    parser.add_argument("--limit", type=int, default=None, help="Max URLs to audit")
    args = parser.parse_args()

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_csv = args.output or f"geo_batch_report_{timestamp}.csv"
    output_summary = f"geo_batch_summary_{timestamp}.txt"

    print(f"\nGEO Batch Auditor")
    print(f"Input: {args.input_file}")
    print(f"Delay: {args.delay}s between requests")
    print(f"Output: {output_csv}\n")
    print("-" * 70)

    urls = load_urls(args.input_file, args.column)

    if not urls:
        print("No valid URLs found in input file.")
        sys.exit(1)

    if args.limit:
        urls = urls[:args.limit]

    print(f"Found {len(urls)} URLs to audit\n")

    # CSV output fields
    fieldnames = [
        "url", "status", "error",
        "total_score", "total_max", "pct_score", "grade",
        "title_score", "title_note", "title_value",
        "meta_score", "meta_note",
        "heading_score", "h1_count", "h2_count", "h1_text",
        "schema_score", "schema_types", "has_faq", "has_org", "has_article",
        "eeat_score", "eeat_count", "eeat_signals",
        "citation_score", "has_questions", "has_lists", "has_tables",
        "content_score", "word_count",
        "top_recommendations",
    ]

    all_results = []
    issue_counts = {}

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] {url[:70]}...")

            soup, status_code, error = fetch_page(url)

            if soup is None:
                row = {k: "" for k in fieldnames}
                row["url"] = url
                row["status"] = status_code
                row["error"] = error
                row["grade"] = "ERROR"
                writer.writerow(row)
                print(f"  ERROR: {error}")
                all_results.append(row)
                if args.delay: time.sleep(args.delay)
                continue

            # Run all checks
            results = {
                "title": check_title(soup),
                "meta": check_meta_description(soup),
                "headings": check_headings(soup),
                "schema": check_schema(soup),
                "eeat": check_eeat(soup),
                "citation": check_citation_friendliness(soup),
                "content": check_content_length(soup),
            }

            total = sum(r["score"] for r in results.values())
            max_total = sum(r["max"] for r in results.values())
            pct = round(total / max_total * 100) if max_total else 0
            g = grade(total, max_total)
            recs = get_top_recommendations(results)

            # Track issue counts for summary
            for rec in recs.split(" | "):
                if rec and rec != "Well optimized":
                    issue_counts[rec] = issue_counts.get(rec, 0) + 1

            row = {
                "url": url,
                "status": status_code,
                "error": "",
                "total_score": total,
                "total_max": max_total,
                "pct_score": pct,
                "grade": g,
                "title_score": results["title"]["score"],
                "title_note": results["title"]["note"],
                "title_value": results["title"]["value"],
                "meta_score": results["meta"]["score"],
                "meta_note": results["meta"]["note"],
                "heading_score": results["headings"]["score"],
                "h1_count": results["headings"]["h1_count"],
                "h2_count": results["headings"]["h2_count"],
                "h1_text": results["headings"]["h1_text"],
                "schema_score": results["schema"]["score"],
                "schema_types": results["schema"]["types"],
                "has_faq": results["schema"]["has_faq"],
                "has_org": results["schema"]["has_org"],
                "has_article": results["schema"]["has_article"],
                "eeat_score": results["eeat"]["score"],
                "eeat_count": results["eeat"]["count"],
                "eeat_signals": results["eeat"]["signals"],
                "citation_score": results["citation"]["score"],
                "has_questions": results["citation"]["has_questions"],
                "has_lists": results["citation"]["has_lists"],
                "has_tables": results["citation"]["has_tables"],
                "content_score": results["content"]["score"],
                "word_count": results["content"]["word_count"],
                "top_recommendations": recs,
            }

            writer.writerow(row)
            all_results.append(row)

            print(f"  {g} — {pct}% ({total}/{max_total}) — {recs[:60]}")

            if args.delay:
                time.sleep(args.delay)

    # Write summary
    successful = [r for r in all_results if r.get("grade") != "ERROR"]
    errors = [r for r in all_results if r.get("grade") == "ERROR"]

    if successful:
        avg_score = round(sum(int(r["pct_score"]) for r in successful) / len(successful))
        strong = sum(1 for r in successful if r["grade"] == "STRONG")
        good = sum(1 for r in successful if r["grade"] == "GOOD")
        needs_work = sum(1 for r in successful if r["grade"] == "NEEDS WORK")
        weak = sum(1 for r in successful if r["grade"] == "WEAK")

        summary_lines = [
            "=" * 70,
            "GEO BATCH AUDIT SUMMARY",
            f"Run: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Input: {args.input_file}",
            f"URLs audited: {len(successful)} | Errors: {len(errors)}",
            f"Average GEO score: {avg_score}%",
            "=" * 70,
            "",
            "GRADE DISTRIBUTION:",
            f"  STRONG:     {strong} pages ({round(strong/len(successful)*100)}%)",
            f"  GOOD:       {good} pages ({round(good/len(successful)*100)}%)",
            f"  NEEDS WORK: {needs_work} pages ({round(needs_work/len(successful)*100)}%)",
            f"  WEAK:       {weak} pages ({round(weak/len(successful)*100)}%)",
            "",
            "TOP ISSUES ACROSS ALL PAGES:",
        ]

        sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
        for issue, count in sorted_issues[:10]:
            pct_affected = round(count / len(successful) * 100)
            summary_lines.append(f"  {count} pages ({pct_affected}%): {issue}")

        if errors:
            summary_lines += ["", "ERRORS:", *[f"  {r['url']} — {r['error']}" for r in errors]]

        summary_lines += ["", "=" * 70, f"Full report: {output_csv}", ""]
        summary_text = "\n".join(summary_lines)
        print("\n" + summary_text)

        with open(output_summary, "w", encoding="utf-8") as f:
            f.write(summary_text)

        print(f"Summary saved to: {output_summary}")

    print(f"Full report saved to: {output_csv}\n")


if __name__ == "__main__":
    run()

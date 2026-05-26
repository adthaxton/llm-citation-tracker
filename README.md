# llm-citation-tracker

A lightweight Python toolkit for tracking brand citations in LLM responses and auditing content for GEO readiness. Built by an SEO practitioner who started logging LLM citations manually before dedicated tools existed.

---

## Tools

### citation_tracker.py
Track whether your brand appears across a set of prompts you define. You write the prompts, it runs them against the Perplexity API, logs citation presence and context snippets to CSV, and appends on each run so you can track trends over time.

Good for: ongoing monitoring with a fixed prompt set.

### prompt_variation_tester.py
Auto-generates prompt variations around any brand and topic, then tests each one. Reveals which question phrasings are most likely to surface your brand in LLM responses. Works for any industry.

Good for: one-time research, discovering which prompt angles work, informing your GEO content strategy.

### geo_content_auditor.py
Scrapes a single URL and scores it against a GEO readiness checklist — entity signals, structured data, E-E-A-T indicators, citation-friendly formatting, heading structure, and content depth. Outputs a scored report with prioritized recommendations.

Good for: auditing individual pages before publishing or after optimization.

### geo_batch_auditor.py
Run GEO readiness audits across a list of URLs in bulk. Accepts a CSV or plain text file of URLs — exported from Screaming Frog, Google Search Console, or any spreadsheet — and outputs a consolidated CSV report with scores and recommendations for every page, plus a site-wide summary of the most common issues.

No crawling. You provide the URLs, this tool audits them. Works with any site without triggering bot detection.

Good for: site-wide GEO audits, identifying the most common gaps across a large page portfolio, client reporting.

---

## Example output (geo_batch_summary.txt)

```
======================================================================
GEO BATCH AUDIT SUMMARY
Run: 2026-05-25 09:14:02
URLs audited: 47 | Errors: 2
Average GEO score: 38%
======================================================================

GRADE DISTRIBUTION:
  STRONG:     3 pages (6%)
  GOOD:       8 pages (17%)
  NEEDS WORK: 22 pages (47%)
  WEAK:       14 pages (30%)

TOP ISSUES ACROSS ALL PAGES:
  44 pages (94%): Add FAQPage schema
  38 pages (81%): Strengthen E-E-A-T signals (author, date, sources)
  31 pages (66%): Add Q&A formatted content
  28 pages (60%): Increase content depth
  19 pages (40%): Add Organization/LocalBusiness schema
======================================================================
```

---

## Setup (all tools)

**1. Install dependencies**

```bash
pip install requests beautifulsoup4 python-dotenv
```

**2. Get a Perplexity API key** (citation_tracker and prompt_variation_tester only)

Sign up at [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api). There is a free tier available.

**3. Create a `.env` file** (citation_tracker and prompt_variation_tester only)

```
PERPLEXITY_API_KEY=your_key_here
```

---

## citation_tracker.py usage

Edit the config at the top of the file:

```python
BRAND = "Your Brand Name"

PROMPTS = [
    "What are the best SEO agencies for X?",
    "Who specializes in Y SEO?",
    ...
]
```

Run it:

```bash
python citation_tracker.py
```

Output: `citations_log.csv`

---

## prompt_variation_tester.py usage

Edit the config at the top of the file:

```python
BRAND = "Your Brand Name"
TOPIC = "your industry or niche"  # e.g. "personal injury law firms", "B2B SaaS SEO"
NUM_VARIATIONS = 10
```

Run it:

```bash
python prompt_variation_tester.py
```

Output: `variation_results.csv` and `variation_summary.txt`

---

## geo_content_auditor.py usage

Pass any URL as an argument:

```bash
python geo_content_auditor.py https://example.com/your-page
```

Output: `geo_audit_[domain]_[timestamp].txt`

---

## geo_batch_auditor.py usage

Create a text or CSV file of URLs to audit, then run:

```bash
# Plain text file - one URL per line
python geo_batch_auditor.py urls.txt

# CSV from Screaming Frog - specify the URL column
python geo_batch_auditor.py screaming_frog_export.csv --column Address

# CSV from Google Search Console
python geo_batch_auditor.py gsc_export.csv --column Page

# Add a longer delay between requests (default is 1 second)
python geo_batch_auditor.py urls.txt --delay 2

# Limit to first 50 URLs
python geo_batch_auditor.py urls.txt --limit 50

# Custom output filename
python geo_batch_auditor.py urls.txt --output client_audit.csv
```

Output: `geo_batch_report_[timestamp].csv` and `geo_batch_summary_[timestamp].txt`

**CSV columns in the report:**
url, status, grade, total_score, pct_score, title_score, meta_score, heading_score, schema_score, has_faq, has_org, has_article, eeat_score, eeat_count, citation_score, has_questions, has_lists, word_count, top_recommendations

---

## Tracking over time

Run citation_tracker.py or prompt_variation_tester.py on a regular cadence (weekly, biweekly) without deleting the output CSV. Each run appends new rows with a fresh timestamp so you can chart citation rate trends in a spreadsheet or BI tool.

---

## Notes

- citation_tracker and prompt_variation_tester query Perplexity specifically. ChatGPT and Gemini do not currently offer public APIs that replicate their consumer chat interfaces.
- geo_content_auditor and geo_batch_auditor fetch pages directly — no API key required.
- The batch auditor includes a configurable delay between requests (default 1 second) to avoid overloading servers.
- Citation presence is a simple string match (case-insensitive). It catches exact brand name matches but not paraphrases.

---

## Roadmap

- [ ] Multi-model support for citation tracking (Claude, Gemini API)
- [ ] Automated weekly scheduling via cron
- [ ] HTML report output for geo_batch_auditor
- [ ] GEO score trending over time (compare batch runs)
- [ ] Integration with Google Search Console API for automatic URL import

---

## Related

[geo-skills](https://github.com/adthaxton/geo-skills) — Open-source GEO skill frameworks for SEO practitioners covering citation auditing, AI Overview optimization, schema for GEO, multi-location GEO, E-E-A-T signal auditing, and llms.txt implementation.

---

## Author

Angie Thaxton — Senior SEO Strategist specializing in GEO and AI search visibility
[linkedin.com/in/adthaxton](https://linkedin.com/in/adthaxton) | [myainotes.com](https://myainotes.com)

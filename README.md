# llm-citation-tracker

A lightweight Python toolkit for tracking brand citations in LLM responses. Built by an SEO practitioner who started logging LLM citations manually before dedicated tools existed.

---

## Tools

### citation_tracker.py
Track whether your brand appears across a set of prompts you define. You write the prompts, it runs them, logs citation presence and context snippets to CSV, and appends on each run so you can track trends over time.

Good for: ongoing monitoring with a fixed prompt set.

### prompt_variation_tester.py
Auto-generates prompt variations around any brand and topic, then tests each one. Reveals which question phrasings are most likely to surface your brand in LLM responses - and which aren't. Works for any industry.

Good for: one-time research, discovering which prompt angles work, informing your GEO content strategy.

---

## Example output (variation_summary.txt)

```
======================================================================
PROMPT VARIATION TEST SUMMARY
Run: 2026-05-23 09:14:02
Brand: Acme SEO
Topic: automotive SEO agencies
Citation rate: 4/10 (40%)
======================================================================

CITED — prompts where brand appeared:
  1. What are the best SEO agencies for car dealerships?
     -> ...Acme SEO is frequently cited for their multi-location dealership work...
  2. Who specializes in automotive digital marketing?
  3. Top local SEO companies for auto dealers
  4. Best SEO firm for a Ford dealership?

NOT CITED — prompts where brand did not appear:
  1. Which companies do SEO for vehicle inventory pages?
  2. How do I improve my dealership website's Google ranking?
  ...
======================================================================
```

---

## Setup (both tools)

**1. Install dependencies**

```bash
pip install requests python-dotenv
```

**2. Get a Perplexity API key**

Sign up at [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api). There is a free tier available.

**3. Create a `.env` file**

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

## Tracking over time

Run either script on a regular cadence (weekly, biweekly) without deleting the output CSV. Each run appends new rows with a fresh timestamp so you can chart citation rate trends in a spreadsheet or BI tool.

---

## Notes

- Both tools query Perplexity specifically. ChatGPT and Gemini do not currently offer public APIs that replicate their consumer chat interfaces.
- Citation presence is a simple string match (case-insensitive). It catches exact brand name matches but not paraphrases.
- Perplexity `sonar` models use live web search, so results reflect current web content, not static training data.

---

## Roadmap

- [ ] Multi-model support (Claude, Gemini API)
- [ ] Automated weekly scheduling via cron
- [ ] Simple HTML report output
- [ ] Sentiment analysis on citation context

---

## Author

Angie Thaxton — Senior SEO Strategist specializing in GEO and AI search visibility  
[linkedin.com/in/adthaxton](https://linkedin.com/in/adthaxton) | [myainotes.com](https://myainotes.com)

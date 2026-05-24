# llm-citation-tracker

A lightweight Python tool for tracking brand citations in LLM responses. Queries the Perplexity API across a set of target prompts and logs whether your brand appears in each response, along with the surrounding context snippet.

Built by an SEO practitioner who started tracking LLM citations manually before dedicated tools existed. This script automates the prompt-by-prompt logging workflow.

---

## What it does

- Sends a list of prompts to the Perplexity API (which uses live web search)
- Checks each response for your brand name
- Logs results to a CSV with timestamp, prompt, cited (YES/NO), context snippet, and full response
- Appends on each run so you can track citation presence over time

---

## Example output (citations_log.csv)

| timestamp | brand | model | prompt | cited | snippet |
|---|---|---|---|---|---|
| 2026-05-23 09:14:02 | Acme SEO | llama-3.1-sonar... | What are the best automotive SEO agencies? | YES | ...Acme SEO is frequently mentioned for their multi-location... |
| 2026-05-23 09:14:08 | Acme SEO | llama-3.1-sonar... | Who are the top SEO companies for car dealerships? | NO | |

---

## Setup

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

**4. Edit `citation_tracker.py`**

Set your brand name and prompts at the top of the file:

```python
BRAND = "Your Brand Name"

PROMPTS = [
    "What are the best SEO agencies for X?",
    "Who specializes in Y SEO?",
    ...
]
```

**5. Run it**

```bash
python citation_tracker.py
```

---

## Tracking over time

Run the script on a regular cadence (weekly, biweekly) without deleting `citations_log.csv`. Each run appends new rows with a fresh timestamp, so you can chart citation rate trends in a spreadsheet or BI tool over time.

---

## Notes

- This tool checks Perplexity specifically. ChatGPT and Gemini do not currently offer public APIs that replicate their consumer chat interfaces.
- Citation presence is a simple string match (case-insensitive). It will catch exact brand name matches but not paraphrases.
- The Perplexity `sonar` models use live web search, so results reflect current web content, not static training data.

---

## Roadmap ideas

- [ ] Multi-model support (add Claude, Gemini API)
- [ ] Prompt variation testing (same intent, different phrasing)
- [ ] Automated weekly scheduling via cron
- [ ] Simple HTML report output

---

## Author

Angie Thaxton — Senior SEO Strategist specializing in GEO and AI search visibility  
[linkedin.com/in/adthaxton](https://linkedin.com/in/adthaxton) | [myainotes.com](https://myainotes.com)
